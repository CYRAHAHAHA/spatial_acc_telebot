# First run: pip install python-telegram-bot==21.4
# Run code: python bot_logger.

import os
import re
import json
import pathlib
import datetime
from datetime import datetime as dt
from typing import Dict, List, Any, Tuple
import difflib

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

# ----------------------------
# Setup: logs directory & file
# ----------------------------
LOG_DIR = pathlib.Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def log_path() -> pathlib.Path:
    """Single JSONL file to append to."""
    return LOG_DIR / "log_message.jsonl"


# -------------------------------------
# Optional helper: /template quick reply
# -------------------------------------
TEMPLATE = (
    "[UPDATE]\n"
    "Location: Building A, Level 3\n"
    "Zone / Grid / Area: Grid 5-7, East Wing\n"
    "Task: Internal Partition Walls\n"
    "Status: Completed\n"
    "Date: 17 Oct 2025\n"
    "Remarks: Ready for inspection"
)

async def cmd_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply a template that users can copy/edit/send."""
    await update.message.reply_text("Copy, edit, and send this format:\n\n" + TEMPLATE)


# -------------------------
# Canon + typo-fix helpers
# -------------------------
BUILDINGS_CANON = ["Building A", "Building B", "Building C", "Block A", "Block B"]
LEVELS_CANON    = ["B3", "B2", "B1", "1", "2", "3", "4", "5", "6", "7"]
TASKS_CANON     = [
    "Internal Partition Walls", "Masonry Walls", "Drywall",
    "Slab", "MEP Rough-in", "Painting"
]
STATUSES_CANON  = ["Completed", "In Progress", "Delayed", "Issue"]

COMMON_WORD_FIXES = {
    "inspecton": "inspection",
    "inspetion": "inspection",
    "inspeciton": "inspection",
    "partion": "partition",
    "parititon": "partition",
    "complted": "completed",
    "compeleted": "completed",
}

def _closest_canon(user_text: str, canon: List[str], cutoff_low: float = 0.60) -> str:
    """
    Return the best canonical value if close enough; otherwise return original.
    Keeps behavior silent (no prompts).
    """
    if not user_text or not canon:
        return user_text
    # exact (case-insensitive) -> standardize casing to canon
    for c in canon:
        if user_text.strip().lower() == c.lower():
            return c
    # fuzzy
    match = difflib.get_close_matches(user_text, canon, n=1, cutoff=cutoff_low)
    return match[0] if match else user_text

def _fix_common_words(text: str) -> str:
    """Replace common misspellings in free text (remarks/task)."""
    if not text:
        return text
    words = text.split()
    for i, w in enumerate(words):
        core = w.strip(",.;:!?").lower()
        if core in COMMON_WORD_FIXES:
            suffix = w[len(w.rstrip(",.;:!?")):]
            words[i] = COMMON_WORD_FIXES[core] + suffix
    return " ".join(words)


# ------------------------------------------
# One-shot [UPDATE] message parsing & logging
# ------------------------------------------
UPDATE_BLOCK_RE = re.compile(
    r"""
    ^\s*\[UPDATE\]\s*
    (?P<body>.+?)\s*$          # everything after [UPDATE] until the end
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE
)

# Field extractor — flexible order & spacing; all anchored to line starts.
FIELD_RE = re.compile(
    r"""
    ^\s*Location\s*:\s*(?P<location>.+?)\s*$ |
    ^\s*(?:Zone\s*/\s*Grid\s*/\s*Area|Zone|Grid|Area)\s*:\s*(?P<area>.+?)\s*$ |
    ^\s*Task\s*:\s*(?P<task>.+?)\s*$ |
    ^\s*Status\s*:\s*(?P<status>.+?)\s*$ |
    ^\s*Date\s*:\s*(?P<date>.+?)\s*$ |
    ^\s*Remarks\s*:\s*(?P<remarks>.+?)\s*$
    """,
    re.MULTILINE | re.IGNORECASE | re.VERBOSE
)

# Parse "Building A, Level 3" (case-insensitive, accepts letters/numbers/dashes)
LOC_SPLIT_RE = re.compile(
    r"Building\s*(?P<b>[A-Za-z0-9\-]+)\s*,\s*Level\s*(?P<l>[A-Za-z0-9\-]+)",
    re.IGNORECASE
)

def _normalize_date(s: str, fallback_iso_date: str) -> str:
    """Return an ISO date yyyy-mm-dd. If s is None/invalid, use fallback."""
    if not s:
        return fallback_iso_date
    s = s.strip()
    for fmt in ("%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %B %Y"):
        try:
            return dt.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    if s.lower() in ("today", "now"):
        return dt.utcnow().date().isoformat()
    # Unknown format: keep as-is (still stored)
    return s

def _parse_update_text(text: str, message_dt_iso: str) -> Tuple[Dict[str, Any], List[str]]:
    """
    Parse a single-shot [UPDATE] message.
    Returns: (parsed_json, errors)
    - parsed_json: dict with normalized fields
    - errors: list of validation error strings (empty if OK)
    """
    m = UPDATE_BLOCK_RE.match(text)
    if not m:
        return ({}, ["Message must start with [UPDATE]."])

    body = m.group("body")

    found = {
        "location": None,
        "area": None,
        "task": None,
        "status": None,
        "date": None,
        "remarks": None,
    }

    # Find all fields (any order)
    for fm in FIELD_RE.finditer(body):
        gd = fm.groupdict()
        for k in found:
            if gd.get(k):
                found[k] = gd[k].strip()

    errors: List[str] = []
    # Required fields check
    if not found["location"]:
        errors.append("Missing 'Location: Building X, Level Y'.")
    if not found["area"]:
        errors.append("Missing 'Zone / Grid / Area: ...'.")
    if not found["task"]:
        errors.append("Missing 'Task: ...'.")
    if not found["status"]:
        errors.append("Missing 'Status: ...'.")

    # Parse Location -> building, level
    building = level = None
    if found["location"]:
        lm = LOC_SPLIT_RE.search(found["location"])
        if lm:
            braw = lm.group("b")
            building = braw if braw.lower().startswith("building") else f"Building {braw}"
            level = lm.group("l")
        else:
            # Keep raw location if not matched, and leave level None
            building = found["location"]

    # Parse Area -> grid, wing (split on first comma)
    grid = wing = None
    if found["area"]:
        parts = [p.strip() for p in found["area"].split(",", 1)]
        grid = parts[0] if parts else None
        wing = parts[1] if len(parts) > 1 else None

    # Ignore user-entered date and force to the message's actual timestamp date
    date_iso = message_dt_iso.split("T", 1)[0]

    # --- silent auto-corrections (no chat messages) ---
    if building:
        building = _closest_canon(building, BUILDINGS_CANON)
    if level:
        level = _closest_canon(str(level), LEVELS_CANON)
    if found["task"]:
        fixed_task = _fix_common_words(found["task"])
        found["task"] = _closest_canon(fixed_task, TASKS_CANON)
    if found["status"]:
        found["status"] = _closest_canon(found["status"], STATUSES_CANON)
    if found["remarks"]:
        found["remarks"] = _fix_common_words(found["remarks"])

    parsed = {
        "type": "UPDATE",
        "location": {"building": building, "level": level},
        "area": {"zone": None, "grid": grid, "wing": wing},
        "task": found["task"],
        "status": found["status"],
        "date": date_iso,
        "remarks": found["remarks"] or None,
    }
    return (parsed, errors)


async def one_shot_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Validate + parse single-shot [UPDATE] messages in groups,
    then append only {timestamp + corrected fields} to log_message.jsonl
    """
    # Only act in group chats (ignore DMs unless you want otherwise)
    if update.effective_chat.type not in ("group", "supergroup"):
        return

    msg = update.effective_message
    text = (msg.text or msg.caption or "").strip()
    if not text.startswith("[UPDATE]"):
        return  # ignore normal chatter

    parsed, errors = _parse_update_text(text, message_dt_iso=msg.date.isoformat())

    if errors:
        await msg.reply_text(
            "Message Error:\n- " + "\n- ".join(errors)
        )
        return

    # Append only the timestamp + corrected fields
    with open(log_path(), "a", encoding="utf-8") as f:
        entry = {"timestamp": msg.date.isoformat(), **parsed}
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Minimal acknowledgement without exposing corrections
    await msg.reply_text("Update logged.")


# -------------
# Main bootstrap
# -------------
def main() -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("Please set TELEGRAM_TOKEN environment variable first")

    app = Application.builder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("template", cmd_template))

    # Handlers: One-shot [UPDATE] parser for group chats
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, one_shot_update_handler))

    print("Bot is running... listening for messages.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

# First run: pip install python-telegram-bot==21.4 requests
# Run code: python bot_logger.py

import os
import re
import json
import pathlib
import difflib
from datetime import datetime as dt
from typing import Dict, List, Any, Tuple

import requests
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

# -------------------------------------------------
# ENV CONFIG for talking to Flask backend
# -------------------------------------------------
FLASK_BASE = os.environ.get("FLASK_BASE", "http://localhost:8080")
FLASK_TOKEN = os.environ.get("SITE_UPDATES_TOKEN", "super-secret-token")

# ----------------------------
# Setup: logs directory & file
# ----------------------------
LOG_DIR = pathlib.Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def log_path() -> pathlib.Path:
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
    "Remarks: Ready for inspection\n"
    "GUID: 12345678-1234-1234-1234-123456789012"
)

async def cmd_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    if not user_text or not canon:
        return user_text
    for c in canon:
        if user_text.strip().lower() == c.lower():
            return c
    match = difflib.get_close_matches(user_text, canon, n=1, cutoff=cutoff_low)
    return match[0] if match else user_text

def _fix_common_words(text: str) -> str:
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
# Regexes & parsing
# ------------------------------------------
UPDATE_BLOCK_RE = re.compile(
    r"""
    ^\s*\[UPDATE\]\s*
    (?P<body>.+?)\s*$
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE
)

FIELD_RE = re.compile(
    r"""
    ^\s*Location\s*:\s*(?P<location>.+?)\s*$ |
    ^\s*(?:Zone\s*/\s*Grid\s*/\s*Area|Zone|Grid|Area)\s*:\s*(?P<area>.+?)\s*$ |
    ^\s*Task\s*:\s*(?P<task>.+?)\s*$ |
    ^\s*Status\s*:\s*(?P<status>.+?)\s*$ |
    ^\s*Date\s*:\s*(?P<date>.+?)\s*$ |
    ^\s*Remarks\s*:\s*(?P<remarks>.+?)\s*$ |
    ^\s*GUID\s*:\s*(?P<guid>.+?)\s*$
    """,
    re.MULTILINE | re.IGNORECASE | re.VERBOSE
)

LOC_SPLIT_RE = re.compile(
    r"Building\s*(?P<b>[A-Za-z0-9\-]+)\s*,\s*Level\s*(?P<l>[A-Za-z0-9\-]+)",
    re.IGNORECASE
)

GUID_LINE_RE = re.compile(
    r"^GUID\s*:\s*(?P<guid>[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})\s*$",
    re.MULTILINE | re.IGNORECASE
)

def extract_guid_block_format(text: str):
    if not text:
        return None
    m = GUID_LINE_RE.search(text)
    if m:
        return m.group("guid")
    return None

def _parse_update_text(text: str, message_dt_iso: str) -> Tuple[Dict[str, Any], List[str]]:
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

    for fm in FIELD_RE.finditer(body):
        gd = fm.groupdict()
        for k in found:
            if gd.get(k):
                found[k] = gd[k].strip()

    errors: List[str] = []
    if not found["location"]:
        errors.append("Missing 'Location: Building X, Level Y'.")
    if not found["area"]:
        errors.append("Missing 'Zone / Grid / Area: ...'.")
    if not found["task"]:
        errors.append("Missing 'Task: ...'.")
    if not found["status"]:
        errors.append("Missing 'Status: ...'.")

    building = level = None
    if found["location"]:
        lm = LOC_SPLIT_RE.search(found["location"])
        if lm:
            braw = lm.group("b")
            building = braw if braw.lower().startswith("building") else f"Building {braw}"
            level = lm.group("l")
        else:
            building = found["location"]

    grid = wing = None
    if found["area"]:
        parts = [p.strip() for p in found["area"].split(",", 1)]
        grid = parts[0] if parts else None
        wing = parts[1] if len(parts) > 1 else None

    # force to message timestamp date (not user-typed Date)
    date_iso = message_dt_iso.split("T", 1)[0]

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

# -------------------------------------------------
# Send parsed update to Flask backend
# -------------------------------------------------
def send_to_flask_api(guid: str, message, parsed: Dict[str, Any]) -> Tuple[bool, str]:
    raw_text = (message.text or message.caption or "").strip()

    payload = {
        "timestamp": message.date.isoformat(),
        "chat_id": message.chat_id,
        "message_id": message.message_id,
        "sender": (
            f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
            if message.from_user else None
        ),
        "sender_id": (message.from_user.id if message.from_user else None),
        "raw_text": raw_text,
        "parsed": parsed
    }

    url = f"{FLASK_BASE}/site-updates/{guid}"
    headers = {
        "Authorization": f"Bearer {FLASK_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        if r.status_code < 300:
            return True, r.text
        else:
            return False, f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return False, str(e)

# -------------------------------------------------
# Telegram handler
# -------------------------------------------------
async def one_shot_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type not in ("group", "supergroup"):
        return

    msg = update.effective_message
    text = (msg.text or msg.caption or "").strip()
    if not text.startswith("[UPDATE]"):
        return

    parsed, errors = _parse_update_text(text, message_dt_iso=msg.date.isoformat())
    if errors:
        await msg.reply_text("Message Error:\n- " + "\n- ".join(errors))
        return

    # 1. Write to local log file
    with open(log_path(), "a", encoding="utf-8") as f:
        entry = {"timestamp": msg.date.isoformat(), **parsed}
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # 2. Extract GUID
    guid = extract_guid_block_format(text)

    # 3. If GUID present, send to Flask
    if guid:
        ok, info = send_to_flask_api(guid, msg, parsed)
        if ok:
            await msg.reply_text(f"✅ Update logged and synced for GUID {guid}.")
        else:
            await msg.reply_text(
                f"⚠ Update logged locally but sync failed for GUID {guid}.\n{info}"
            )
    else:
        await msg.reply_text("Update logged.")

# ------------- 
# Main bootstrap
# -------------
def main() -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("Please set TELEGRAM_TOKEN environment variable first")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("template", cmd_template))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, one_shot_update_handler))

    print("Bot is running... listening for messages.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

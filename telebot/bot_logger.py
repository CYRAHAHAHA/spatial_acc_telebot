# First run: pip install python-telegram-bot==21.4 requests
# Run code: python bot_logger.py

import os
import re
import json
import pathlib
import difflib
from datetime import datetime as dt
from typing import Dict, List, Any, Tuple
from threading import Lock
from datetime import UTC

from dotenv import load_dotenv, find_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

# Load environment variables (supports running from /telebot)
load_dotenv(find_dotenv(usecwd=True), override=True)

# -------------------------------------------------------------------
# Local JSON logging for compiled/parsed updates (replaces flask_api)
# -------------------------------------------------------------------

BASE_DIR = pathlib.Path(__file__).resolve().parent
SITE_UPDATES_PATH = BASE_DIR / "site_updates.json"

# Map each Telegram chat (group) to a project_id
PROJECT_MAP_PATH = BASE_DIR / "group_project_map.json"


def load_project_map() -> Dict[str, str]:
    if PROJECT_MAP_PATH.exists():
        try:
            with open(PROJECT_MAP_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception as e:
            print("Bot: error reading project map:", repr(e))
    return {}


def save_project_map(mapping: Dict[str, str]) -> None:
    with open(PROJECT_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

DB: Dict[str, Dict[str, Any]] = {}
DB_LOCK = Lock()


def append_pretty_update(entry: dict) -> None:
    """
    Append one entry into site_updates.json, stored as a JSON array.
    """

    if SITE_UPDATES_PATH.exists():
        try:
            with open(SITE_UPDATES_PATH, "r", encoding="utf-8") as rf:
                data = json.load(rf)
            if not isinstance(data, list):
                data = []
        except Exception as e:
            print("Bot: error reading existing JSON:", repr(e))
            data = []
    else:
        data = []

    data.append(entry)

    with open(SITE_UPDATES_PATH, "w", encoding="utf-8") as wf:
        json.dump(data, wf, ensure_ascii=False, indent=2)
        wf.write("\n")
    print("Bot: write complete, total entries:", len(data))  # debug

def log_site_update(guid: str, payload: dict, project_id: str | None) -> dict:
    print("Bot: logging payload for GUID", guid)  # still keep this

    # 1) Pull timestamp -> date (YYYY-MM-DD)
    full_ts = payload.get("timestamp", "")
    date_only = full_ts.split("T")[0] if "T" in full_ts else full_ts

    # 2) Get parsed fields
    parsed = payload.get("parsed") or {}
    loc = parsed.get("location") or {}
    area = parsed.get("area") or {}

    # 3) Build 'location' string: "Building C, Level 8"
    location_str = None
    if isinstance(loc, dict):
        b = loc.get("building")
        lvl = loc.get("level")
        if b and lvl:
            location_str = f"{b}, Level {lvl}"
        elif b:
            location_str = b
        elif lvl:
            location_str = f"Level {lvl}"
    elif isinstance(loc, str):
        location_str = loc

    # 4) Build 'area' string: "Grid 5-7, East Wing"
    area_str = None
    if isinstance(area, dict):
        parts = []
        g = area.get("grid")
        w = area.get("wing")
        if g:
            parts.append(g)
        if w:
            parts.append(w)
        area_str = ", ".join(parts) if parts else None
    elif isinstance(area, str):
        area_str = area

    # 5) Flatten and clean the parsed fields
    flattened_parsed = {
        "location": location_str,
        "area": area_str,
        "task": parsed.get("task"),
        "status": parsed.get("status"),
        "remarks": parsed.get("remarks"),
    }

    # 6) In-memory versioning + save to site_updates.json
    with DB_LOCK:
        rec = DB.get(guid) or {"guid": guid, "version": 0, "history": []}
        rec["version"] += 1
        # you can keep this or later switch to timezone-aware:
        rec["updated_at"] = dt.now(UTC).isoformat()
        rec["last"] = payload
        rec["history"].append(payload)
        DB[guid] = rec

        clean_payload = {
            "guid": guid,
            "version": rec["version"],
            "date": date_only,
            "project_id": project_id,   
            "parsed": flattened_parsed,
        }

        append_pretty_update(clean_payload)

    return clean_payload



# Optional helper: /template quick reply -------------------------------------

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

async def cmd_setproject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    # Only allow in groups
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("This command is only for group chats.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setproject <project_id>")
        return

    project_id = context.args[0].strip()
    mapping = load_project_map()
    mapping[str(chat.id)] = project_id
    save_project_map(mapping)

    await update.message.reply_text(
        f"Project ID for this group is now set to: {project_id}"
    )


# Canon + typo-fix helpers -------------------------

BUILDINGS_CANON = ["Building A", "Building B", "Building C", "Block A", "Block B"]
LEVELS_CANON = ["B3", "B2", "B1", "1", "2", "3", "4", "5", "6", "7"]
TASKS_CANON = [
    "Internal Partition Walls",
    "Masonry Walls",
    "Drywall",
    "Slab",
    "MEP Rough-in",
    "Painting",
]
STATUSES_CANON = ["Completed", "In Progress", "Delayed", "Issue"]

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
            suffix = w[len(w.rstrip(",.;:!?")) :]
            words[i] = COMMON_WORD_FIXES[core] + suffix
    return " ".join(words)


# Regexes & parsing ------------------------------------------

UPDATE_BLOCK_RE = re.compile(
    r"""
    ^\s*\[UPDATE\]\s*
    (?P<body>.+?)\s*$
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

LINE_RE = re.compile(
    r"^\s*(?P<key>[^:]+?)\s*:\s*(?P<val>.*)\s*$",
    re.IGNORECASE,
)

LOC_SPLIT_RE = re.compile(
    r"Building\s*(?P<b>[A-Za-z0-9\-]+)\s*,\s*Level\s*(?P<l>[A-Za-z0-9\-]+)",
    re.IGNORECASE,
)

GUID_LINE_RE = re.compile(
    r"^GUID\s*:\s*(?P<guid>.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def extract_guid_block_format(text: str):
    if not text:
        return None
    m = GUID_LINE_RE.search(text)
    if m:
        return m.group("guid")
    return None


def _parse_update_text(text: str, message_dt_iso: str) -> Tuple[Dict[str, Any], List[str]]:
    """
    Parse a single-shot [UPDATE] message.
    Always returns (parsed_dict, errors_list).
    If there are validation errors, parsed_dict will be {} and errors_list non-empty.
    """
    m = UPDATE_BLOCK_RE.match(text or "")
    if not m:
        return ({}, ["Message must start with [UPDATE]."])

    body = m.group("body")

    # We'll collect all fields, forcing whitespace-only values to None
    found = {
        "location": None,
        "area": None,
        "task": None,
        "status": None,
        "date": None,
        "remarks": None,
    }

    # Parse line by line so each field is mapped correctly
    for raw_line in body.splitlines():
        m = LINE_RE.match(raw_line)
        if not m:
            continue

        key = m.group("key").strip().lower()
        val = _normalize_and_strip(m.group("val"))

        if key.startswith("location"):
            found["location"] = val
        elif key.startswith("zone") or key.startswith("grid") or key.startswith("area"):
            found["area"] = val
        elif key == "task":
            found["task"] = val
        elif key == "status":
            found["status"] = val
        elif key == "date":
            found["date"] = val
        elif key == "remarks":
            found["remarks"] = val
        # GUID is handled separately by extract_guid_block_format()


    # Requireds
    label = {
        "location": "Location: Building X, Level Y",
        "area": "Zone / Grid / Area: ...",
        "task": "Task: ...",
        "status": "Status: ...",
    }
    errors: List[str] = []
    for key in ("location", "area", "task", "status"):
        if not found.get(key):
            errors.append(f"Missing '{label[key]}'")

    # Location -> building, level
    building = level = None
    if found["location"]:
        lm = LOC_SPLIT_RE.search(found["location"])
        if lm:
            braw = lm.group("b")
            building = (
                braw if braw.lower().startswith("building") else f"Building {braw}"
            )
            level = lm.group("l")
        else:
            building = found["location"]

    # Area -> grid, wing
    grid = wing = None
    if found["area"]:
        parts = [p.strip() for p in found["area"].split(",", 1)]
        grid = parts[0] if parts else None
        wing = parts[1] if len(parts) > 1 else None

    # Use message date (YYYY-MM-DD)
    date_iso = (message_dt_iso or "").split("T", 1)[0] or dt.utcnow().date().isoformat()

    # Canonicalization / polishing
    if building:
        building = _closest_canon(building, BUILDINGS_CANON)
    if level:
        level = _closest_canon(str(level), LEVELS_CANON)

    grid, wing = _normalize_area_parts(grid, wing)
    found["task"] = _canonicalize_task(found["task"])
    found["status"] = _canonicalize_status(found["status"])
    found["remarks"] = _polish_remarks(found["remarks"])

    # Enforce canon values
    if found.get("task") and found["task"] not in TASKS_CANON:
        errors.append("Unrecognized 'Task'. Allowed: " + ", ".join(TASKS_CANON))
    if found.get("status") and found["status"] not in STATUSES_CANON:
        errors.append("Unrecognized 'Status'. Allowed: " + ", ".join(STATUSES_CANON))

    # If any errors, return tuple with {} + errors
    if errors:
        return ({}, errors)

    parsed = {
        "type": "UPDATE",
        "location": {"building": building, "level": level},
        "area": {"zone": None, "grid": grid, "wing": wing},
        "task": found["task"],
        "status": found["status"],
        "date": date_iso,
        "remarks": found["remarks"] or None,
    }
    return (parsed, [])


# Expand typo map - typo helper
COMMON_WORD_FIXES.update(
    {
        "reay": "ready",
        "inspec": "inspection",
        "inspct": "inspection",
        "insp": "inspection",
        "com": "completed",
        "compl": "completed",
        "complet": "completed",
    }
)

DIRECTIONS = {"east", "west", "north", "south"}


def _prefix_or_fuzzy(value: str, choices: List[str]) -> str | None:
    """Prefer case-insensitive prefix match; fallback to fuzzy."""
    if not value:
        return None
    v = value.strip().lower()
    hits = [c for c in choices if c.lower().startswith(v)]
    if len(hits) == 1:
        return hits[0]
    cand = difflib.get_close_matches(value, choices, n=1, cutoff=0.6)
    return cand[0] if cand else None


def _canonicalize_status(s: str | None) -> str | None:
    if not s:
        return None
    return _prefix_or_fuzzy(s, STATUSES_CANON)


def _canonicalize_task(t: str | None) -> str | None:
    if not t:
        return None
    t = _fix_common_words(t)
    mapped = _closest_canon(t, TASKS_CANON)
    return mapped or _prefix_or_fuzzy(t, TASKS_CANON)


def _normalize_area_parts(
    grid: str | None, wing: str | None
) -> tuple[str | None, str | None]:
    if grid:
        g = grid.strip()
        if not g.lower().startswith("grid "):
            grid = f"Grid {g}"
    if wing:
        w = wing.strip()
        if w.lower() in DIRECTIONS:
            wing = w.capitalize() + " Wing"
    return grid, wing


def _polish_remarks(text: str | None) -> str | None:
    if not text:
        return None
    tokens = []
    for w in text.split():
        core = w.strip(",.;:!?")
        fixed = COMMON_WORD_FIXES.get(core.lower(), core)
        suffix = w[len(core) :]
        tokens.append(fixed + suffix)
    s = " ".join(tokens)
    s = s.replace("ready for inspection", "Ready for inspection")
    return s


def _normalize_and_strip(s: str) -> str | None:
    if s is None:
        return None
    s = (
        s.replace("\u00A0", " ")  # NBSP
        .replace("\u2007", " ")  # Figure space
        .replace("\u202F", " ")  # Narrow NBSP
    )
    s = s.strip()
    return s if s != "" else None


# -------------------------------------------------------------------
# Telegram handler --------------------------------------------------
# -------------------------------------------------------------------

async def one_shot_update_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    # Only act in group chats
    if update.effective_chat.type not in ("group", "supergroup"):
        return

    msg = update.effective_message
    text = (msg.text or msg.caption or "").strip()

    # Only react to messages that start with [UPDATE]
    if not text.startswith("[UPDATE]"):
        return

    chat_id_str = str(msg.chat_id)
    mapping = load_project_map()
    project_id = mapping.get(chat_id_str)

    # If this group has no project_id yet, ask once and stop
    if not project_id:
        await msg.reply_text(
            "👋 I don't know the project for this group yet.\n\n"
            "Please set it once using:\n"
            "/setproject <project_id>\n\n"
            "Example:\n"
            "/setproject Punggol-EC-01\n\n"
            "Then resend your [UPDATE] message."
        )
        return

    # Parse the message
    parsed, errors = _parse_update_text(text, message_dt_iso=msg.date.isoformat())

    # If any required fields are missing/blank, STOP here
    if errors:
        await msg.reply_text(
            "Error: Update not logged.\nPlease fix:\n- " + "\n- ".join(errors)
        )
        return

    # Extract GUID from the message
    guid = extract_guid_block_format(text)

    # If GUID present, also log to site_updates.json with versioning
    if guid:
        raw_text = text
        payload_for_site_updates = {
            "timestamp": msg.date.isoformat(),
            "chat_id": msg.chat_id,
            "message_id": msg.message_id,
            "sender": (
                f"{msg.from_user.first_name or ''} {msg.from_user.last_name or ''}".strip()
                if msg.from_user
                else None
            ),
            "sender_id": (msg.from_user.id if msg.from_user else None),
            "raw_text": raw_text,
            "parsed": parsed,
        }

        clean = log_site_update(guid, payload_for_site_updates, project_id)
        await msg.reply_text(
            f"Update logged for GUID {guid} Project: {project_id}."
        )
    else:
        await msg.reply_text(
            f"Update logged (no GUID provided). Project: {project_id}."
        )


# Main bootstrap -------------
def main() -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("Please set TELEGRAM_TOKEN environment variable first")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("template", cmd_template))
    app.add_handler(CommandHandler("setproject", cmd_setproject))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.GROUPS, one_shot_update_handler)
    )

    print("Bot is running... listening for messages.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

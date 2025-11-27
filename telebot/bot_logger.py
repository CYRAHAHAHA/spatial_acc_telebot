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
from pathlib import Path
import sys

from dotenv import load_dotenv, find_dotenv
from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    ChatMemberHandler,
    filters,
)

import requests

# Locate project root → telebot/../
ROOT_DIR = Path(__file__).resolve().parents[1]

# Append project root so NLP package can be resolved
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from NLP.io_wrapper import run_sample_match  # <- working import


API_URL = "http://localhost:8080/update_status"  # Flask main.py runs on this
API_UPDATE_ISSUE_URL = "http://localhost:8080/update_issue_status" # For issues		
API_FETCH_ISSUE_SUBTYPES_URL = "http://localhost:8080/fetch_issue_subtypes" # For fetching issue info		
API_CREATE_ISSUE_URL = "http://localhost:8080/create_issue" # For creating issues

# Load environment variables (supports running from /telebot)
load_dotenv(find_dotenv(usecwd=True), override=True)


# -------------------------------------------------------------------
# Local JSON logging for compiled/parsed updates (replaces flask_api)
# -------------------------------------------------------------------

BASE_DIR = pathlib.Path(__file__).resolve().parent
SITE_UPDATES_PATH = BASE_DIR / "site_updates.json"
ISSUE_UPDATES_PATH = BASE_DIR / "issue_updates.json"		
ISSUE_CREATED_PATH = BASE_DIR / "issues_created.json"

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
    flattened = {
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
            "parsed": flattened,
        }

        append_pretty_update(clean_payload)

    return clean_payload

def log_issue_update(guid: str, payload: dict, project_id: str | None) -> dict:
    """Log issue status updates (in-memory only, no JSON file)."""
    print("Bot: logging issue update for GUID", guid)

    full_ts = payload.get("timestamp", "")
    date_only = full_ts.split("T")[0] if "T" in full_ts else full_ts
    with DB_LOCK:
        clean_payload = {
            "issue_guid": guid,
            "timestamp": full_ts,
            "date": date_only,
            "project_id": project_id,
            "status": payload.get("status"),
            "sender": payload.get("sender"),
            "sender_id": payload.get("sender_id"),
            "raw_text": payload.get("raw_text"),
        }
        # JSON logging disabled - data kept in memory only
        # append_pretty_update(clean_payload, ISSUE_UPDATES_PATH)

    return clean_payload

def log_issue_created(issue_data: dict, project_id: str | None) -> dict:
    """Log newly created issues (in-memory only, no JSON file)."""
    print("Bot: logging issue creation")

    with DB_LOCK:
        clean_payload = {
            "timestamp": dt.now(UTC).isoformat(),
            "project_id": project_id,
            "issue_data": issue_data
        }
        # JSON logging disabled - data kept in memory only
        # append_pretty_update(clean_payload, ISSUE_CREATED_PATH)

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
    "GUID: 1$p8tACJ938vr1_lKOJJ9g"
)

ISSUE_TEMPLATE = (
    "[ISSUE STATUS]\n"
    "GUID: cae94f63-282c-435b-b798-ec527afcde1d\n"
    "Status: open"
)

CREATE_ISSUE_TEMPLATE = (
    "[CREATE ISSUE]\n"
    "Title: Water leakage at Level 3\n"
    "Status: open\n"
    "Subtype ID: 06e9ad10-7a05-43e8-9e27-38fb455dd50f\n"
    "Description: Water leaking from ceiling\n"
    "Location: Building A, Level 3"
)

async def cmd_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Copy, edit, and send one of these formats:\n\n"
        "For ASSET updates:\n" + TEMPLATE + "\n\n"
        "For ISSUE status updates:\n" + ISSUE_TEMPLATE + "\n\n"
        "For CREATING a new issue:\n" + CREATE_ISSUE_TEMPLATE + "\n\n"
        "To view all issue types and IDs, use:\n/issuesinfo"
    )

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


# Command to fetch issue information with new format
async def cmd_issues_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Fetch all issue types, subtypes, and recent issues from ACC.
    Usage: /issuesinfo
    """
    msg = update.effective_message
    
    # Send initial message
    status_msg = await msg.reply_text("Fetching issue information from ACC...")
    
    try:
        # Call Flask endpoint
        resp = requests.get(API_FETCH_ISSUE_SUBTYPES_URL, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            grouped = data.get("grouped_by_type", {})
            all_subtypes = data.get("all_subtypes", {})
            
            # Get recent issues from the data if available
            recent_issues = data.get("recent_issues", [])
            
            # Count total subtypes
            total_subtypes = len(all_subtypes)
            total_issues = len(recent_issues)
            
            if total_subtypes == 0:
                await status_msg.edit_text(
                    "No issue information found.\n"
                    "Make sure you have project access or issue types configured in ACC."
                )
                return
            
            # Build message in the specified format
            messages = []
            current_message = (
                "ISSUE INFORMATION\n"
                "========================================\n"
                f"Total Issue Types/Subtypes: {len(grouped)}\n"
                f"Total Issues: {total_issues}\n\n"
                "Issue Types & Subtypes:\n"
            )
            
            # Add all issue types and subtypes
            for type_name, subtypes in sorted(grouped.items()):
                type_section = f"{type_name}:\n"
                
                for sub in sorted(subtypes, key=lambda x: x["subtype"]):
                    subtype_line = f"  • {sub['subtype']}\n"
                    subtype_id_line = f"    {sub['id']}\n"
                    
                    # Check if adding this would exceed Telegram's limit
                    test_message = current_message + type_section + subtype_line + subtype_id_line
                    
                    if len(test_message) > 3800:
                        # Save current message and start a new one
                        messages.append(current_message)
                        current_message = "ISSUE INFORMATION (continued)...\n========================================\n\n"
                        type_section = f"{type_name}:\n"
                    
                    type_section += subtype_line + subtype_id_line
                
                current_message += type_section
            
            # Add separator before recent issues
            current_message += "\n========================================\n"
            
            # Add recent issues section
            if total_issues > 0:
                current_message += f"Recent Issues (showing {total_issues}):\n\n"
                
                for issue in recent_issues:
                    title = issue.get("title", "Untitled")
                    status = issue.get("status", "unknown")
                    issue_type = issue.get("issueTypeName") or "None"
                    issue_subtype = issue.get("issueSubtypeName") or "None"
                    issue_id = issue.get("id", "")
                    
                    issue_section = (
                        f"{title}\n"
                        f"  Status: {status}\n"
                        f"  Type: {issue_type} → {issue_subtype}\n"
                        f"  ID: {issue_id}\n\n"
                    )
                    
                    # Check if adding this would exceed Telegram's limit
                    if len(current_message + issue_section) > 3800:
                        # Save current message and start a new one
                        messages.append(current_message)
                        current_message = "ISSUE INFORMATION (continued)...\n========================================\n📋 Recent Issues (continued):\n\n"
                    
                    current_message += issue_section
            else:
                current_message += "Recent Issues: None found\n"
            
            # Add the last message
            messages.append(current_message)
            
            # Send all messages
            for i, message_text in enumerate(messages):
                if i == 0:
                    # Edit the first "fetching..." message
                    await status_msg.edit_text(message_text)
                else:
                    # Send additional messages
                    await msg.reply_text(message_text)
            
        else:
            error_msg = f"Failed to fetch issue information (HTTP {resp.status_code})"
            try:
                error_data = resp.json()
                error_msg += f"\nError: {error_data.get('error', 'Unknown error')}"
            except:
                pass
            
            await status_msg.edit_text(error_msg)
    
    except requests.exceptions.Timeout:
        await status_msg.edit_text("Request timed out. Please try again.")
    except Exception as e:
        print(f"Error fetching issue information: {repr(e)}")
        await status_msg.edit_text(f"Error: {str(e)}")


async def on_new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    member = update.my_chat_member

    # Fire only when *this* bot becomes a member of the group
    if member and member.new_chat_member.status == ChatMemberStatus.MEMBER:
        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "Hello! I'm your site update bot.\n\n"
                "Please provide the Project ID for this group (one time):\n"
                "Example:\n"
                "Project ID: KotaKinabalu-A\n\n"
                "Once set, send your [UPDATE] or [ISSUE STATUS] messages.\n"
                "Use /template to see message formats."
            )
        )


async def handle_project_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.effective_message
    text = (msg.text or "").strip()

    m = re.match(r"(?i)^project\s*id\s*:\s*(.+)", text)
    if not m:
        return

    project_id = m.group(1).strip()
    mapping = load_project_map()
    mapping[str(chat.id)] = project_id
    save_project_map(mapping)

    await msg.reply_text(f"Project ID for this group is now set to: {project_id}")


# Regexes & parsing ------------------------------------------

UPDATE_BLOCK_RE = re.compile(
    r"""
    ^\s*\[UPDATE\]\s*
    (?P<body>.+?)\s*$
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

ISSUE_STATUS_RE = re.compile(
    r"""
    ^\s*\[ISSUE\s+STATUS\]\s*
    (?P<body>.+?)\s*$
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)		
			
CREATE_ISSUE_RE = re.compile(		
    r"""		
    ^\s*\[CREATE\s+ISSUE\]\s*		
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

def _parse_issue_status(text: str) -> Tuple[str | None, str | None, List[str]]:
    """
    Parse [ISSUE STATUS] message format.
    Returns: (guid, status, errors)
    
    Example input:
    [ISSUE STATUS]
    GUID: cae94f63-282c-435b-b798-ec527afcde1d
    Status: open
    """
    m = ISSUE_STATUS_RE.match(text or "")
    if not m:
        return (None, None, ["Message must start with [ISSUE STATUS]."])
    
    body = m.group("body")
    
    guid = None
    status = None
    
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
            
        m = LINE_RE.match(line)
        if not m:
            continue
        
        key = m.group("key").strip().lower()
        val = m.group("val").strip()
        
        if key == "guid":
            guid = val
        elif key == "status":
            status = val
    
    errors = []
    if not guid:
        errors.append("Missing 'GUID: ...'")
    if not status:
        errors.append("Missing 'Status: ...'")
    
    return (guid, status, errors)

def _parse_create_issue(text: str) -> Tuple[Dict[str, Any] | None, List[str]]:
    """
    Parse [CREATE ISSUE] message format.
    Returns: (issue_data, errors)
    """
    m = CREATE_ISSUE_RE.match(text or "")
    if not m:
        return (None, ["Message must start with [CREATE ISSUE]."])
    
    body = m.group("body")
    
    issue_data = {
        "title": None,
        "status": None,
        "subtype_id": None,
        "description": None,
        "location": None
    }
    
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
            
        m = LINE_RE.match(line)
        if not m:
            continue
        
        key = m.group("key").strip().lower()
        val = m.group("val").strip()
        
        if key == "title":
            issue_data["title"] = val
        elif key == "status":
            issue_data["status"] = val
        elif key.startswith("subtype") and "id" in key:
            issue_data["subtype_id"] = val
        elif key == "description":
            issue_data["description"] = val
        elif key == "location":
            issue_data["location"] = val
    
    errors = []
    if not issue_data["title"]:
        errors.append("Missing 'Title: ...'")
    if not issue_data["status"]:
        errors.append("Missing 'Status: ...'")
    if not issue_data["subtype_id"]:
        errors.append("Missing 'Subtype ID: ...' (Use /issuesinfo to find IDs)")
    
    if errors:
        return (None, errors)
    
    return (issue_data, [])


def _parse_update_text(text: str, message_dt_iso: str) -> Tuple[Dict[str, Any], List[str]]:
    """
    Parse a single-shot [UPDATE] message.

    Now:
    - Only checks that required fields are present and non-empty.
    - Does NOT canonicalise or restrict values (any text is allowed).
    """
    m = UPDATE_BLOCK_RE.match(text or "")
    if not m:
        return ({}, ["Message must start with [UPDATE]."])

    body = m.group("body")

    # Collect all fields, forcing whitespace-only values to None
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

    # Required fields: just make sure they're not empty
    label = {
        "location": "Location: Building X, Level Y",
        "area": "Zone / Grid / Area: ...",
        "task": "Task: ...",
        "status": "Status: ...",
    }
    errors: List[str] = []
    for key in ("location", "area", "task", "status"):
        value = found.get(key)
        if value is None or str(value).strip() == "":
            errors.append(f"Missing '{label[key]}'")

    # If any required fields missing → return errors
    if errors:
        return ({}, errors)

    # --- Light parsing of location/area, but no canonicalisation ----
    building = level = None
    if found["location"]:
        lm = LOC_SPLIT_RE.search(found["location"])
        if lm:
            building = lm.group("b")   # e.g. "A", "Building A", "Tower 1" etc.
            level = lm.group("l")      # e.g. "3", "L2", "Roof"
        else:
            # If it doesn't match the pattern, just keep full string as "building"
            building = found["location"]

    grid = wing = None
    if found["area"]:
        parts = [p.strip() for p in found["area"].split(",", 1)]
        grid = parts[0] if parts else None
        wing = parts[1] if len(parts) > 1 else None

    # Use message date (YYYY-MM-DD) if present, else today
    date_iso = (message_dt_iso or "").split("T", 1)[0] or dt.utcnow().date().isoformat()

    parsed = {
        "type": "UPDATE",
        "location": {"building": building, "level": level},
        "area": {"zone": None, "grid": grid, "wing": wing},
        "task": found["task"],          # raw text
        "status": found["status"],      # raw text
        "date": date_iso,
        "remarks": found["remarks"] or None,
    }
    return (parsed, [])


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

def resolve_guid_from_nlp(project_id: str, parsed: Dict[str, Any]) -> tuple[str | None, str | None]:
    """
    Call the matcher (via run_sample_match) and get BOTH:
      - guid  (which BIM element to update)
      - status (canonical status to apply)

    Expected matcher output: {"guid": "...", "status": "..."}
    """
    try:
        loc = parsed.get("location") or {}
        area = parsed.get("area") or {}

        building = loc.get("building") or ""
        level = loc.get("level") or ""
        grid = area.get("grid") or ""
        wing = area.get("wing") or ""
        task = parsed.get("task") or ""
        status_from_text = parsed.get("status") or ""  # original from message
        date = parsed.get("date") or ""
        remarks = parsed.get("remarks") or ""

        # Rebuild the [UPDATE] text that your matcher expects
        lines = [
            "[UPDATE]",
            f"Location: {building}, Level {level}".strip().rstrip(", "),
            f"Zone / Grid / Area: {grid}, {wing}".strip().rstrip(", "),
            f"Task: {task}",
            f"Status: {status_from_text}",
            f"Date: {date}",
        ]
        if remarks:
            lines.append(f"Remarks: {remarks}")

        update_text = "\n".join(lines)

        # Call your NLP matcher here
        result = run_sample_match(update_path=update_text)

        # Your NLP output: {"guid": "xyz", "status": "abc"}
        guid = result.get("guid")
        status_value = result.get("status")

        if isinstance(guid, str):
            guid = guid.strip()
        if isinstance(status_value, str):
            status_value = status_value.strip()

        if not guid or not status_value:
            print("Bot: NLP did not return both guid and status:", result)
            return None, None

        print(f"Bot: NLP resolved GUID={guid}, STATUS={status_value} for project {project_id}")
        return guid, status_value

    except Exception as e:
        print("Bot: error while running NLP matcher via run_sample_match:", repr(e))
        return None, None


# -------------------------------------------------------------------
# Create issue handler
# -------------------------------------------------------------------
async def create_issue_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle [CREATE ISSUE] messages."""
    # Only act in group chats
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    
    msg = update.effective_message
    text = (msg.text or msg.caption or "").strip()
    
    # Only react to messages that start with [CREATE ISSUE]
    if not text.upper().startswith("[CREATE ISSUE]"):
        return
    
    chat_id_str = str(msg.chat_id)
    mapping = load_project_map()
    project_id = mapping.get(chat_id_str)
    
    # If this group has no project_id yet, ask once and stop
    if not project_id:
        await msg.reply_text(
            "No Project ID linked to this group yet.\n\n"
            "Please set it once using:\n"
            "Project ID: <project_id>\n\n"
            "Example:\n"
            "Project ID: Pasir Ris-EC-01\n\n"
            "Then resend your [CREATE ISSUE] message."
        )
        return
    
    # Parse the create issue message
    issue_data, errors = _parse_create_issue(text)
    
    if errors:
        await msg.reply_text(
            "Error: Issue not created.\n\n"
            "Please fix:\n" + "\n".join(f"• {e}" for e in errors) + 
            "\n\nUse /template to see the correct format.\nUse /issuesinfo to find Subtype IDs."
        )
        return
    
    # Call Flask /create_issue
    payload = {
        "title": issue_data["title"],
        "status": issue_data["status"],
        "issue_subtype_id": issue_data["subtype_id"],
        "description": issue_data.get("description"),
        "location_description": issue_data.get("location")
    }
    
    try:
        resp = requests.post(API_CREATE_ISSUE_URL, json=payload, timeout=15)
    except Exception as e:
        print("Bot: error calling /create_issue:", repr(e))
        await msg.reply_text(
            f"Failed to contact the ACC server.\n"
            f"Error: {str(e)}"
        )
        return
    
    if 200 <= resp.status_code < 300:
        try:
            result = resp.json()
            issue_id = result.get("id", "Unknown")
            
            # Log the created issue
            log_issue_created(result, project_id)
            
            await msg.reply_text(
                f"Issue created in ACC!\n\n"
                f"Title: {issue_data['title']}\n"
                f"Status: {issue_data['status']}\n"
                f"ID: {issue_id}\n"
                f"Project: {project_id}"
            )
        except:
            await msg.reply_text(
                f"Issue created in ACC!\n\n"
                f"Title: {issue_data['title']}\n"
                f"Status: {issue_data['status']}\n"
                f"Project: {project_id}"
            )
    else:
        print("Bot: ACC issue creation failed:", resp.status_code, resp.text[:500])
        error_msg = "Unknown error"
        try:
            error_data = resp.json()
            error_msg = error_data.get("error", str(error_data))
        except:
            error_msg = resp.text[:200]
        
        await msg.reply_text(
            f"Issue creation FAILED (HTTP {resp.status_code}).\n\n"
            f"Error: {error_msg}\n\n"
            f"Use /issuesinfo to check valid Subtype IDs."
        )

# -------------------------------------------------------------------
# Issue status update handler
# -------------------------------------------------------------------
async def issue_status_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle [ISSUE STATUS] messages."""
    # Only act in group chats
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    
    msg = update.effective_message
    text = (msg.text or msg.caption or "").strip()
    
    # Only react to messages that start with [ISSUE STATUS]
    if not text.upper().startswith("[ISSUE STATUS]"):
        return
    
    chat_id_str = str(msg.chat_id)
    mapping = load_project_map()
    project_id = mapping.get(chat_id_str)
    
    # If this group has no project_id yet, ask once and stop
    if not project_id:
        await msg.reply_text(
            "No Project ID linked to this group yet.\n\n"
            "Please set it once using:\n"
            "Project ID: <project_id>\n\n"
            "Example:\n"
            "Project ID: Pasir Ris-EC-01\n\n"
            "Then resend your [ISSUE STATUS] message."
        )
        return
    
    # Parse the issue status message
    guid, status, errors = _parse_issue_status(text)
    
    if errors:
        await msg.reply_text(
            "Error: Issue status not updated.\n\n"
            "Please fix:\n" + "\n".join(f"• {e}" for e in errors) + 
            "\n\nUse /template to see the correct format."
        )
        return
    
    # Log the issue update
    payload_for_log = {
        "timestamp": msg.date.isoformat(),
        "chat_id": msg.chat_id,
        "message_id": msg.message_id,
        "sender": (
            f"{msg.from_user.first_name or ''} {msg.from_user.last_name or ''}".strip()
            if msg.from_user
            else None
        ),
        "sender_id": (msg.from_user.id if msg.from_user else None),
        "raw_text": text,
        "status": status,
    }
    
    log_issue_update(guid, payload_for_log, project_id)
    
    # Call Flask /update_issue_status
    payload = {
        "issue_guid": guid,
        "status_value": status,
    }
    
    try:
        resp = requests.post(API_UPDATE_ISSUE_URL, json=payload, timeout=15)
    except Exception as e:
        print("Bot: error calling /update_issue_status:", repr(e))
        await msg.reply_text(
            f"Issue update logged for GUID {guid} (Project: {project_id}), "
            "but failed to contact the ACC server.\n"
            f"Error: {str(e)}"
        )
        return
    
    if 200 <= resp.status_code < 300:
        await msg.reply_text(
            f"Issue status updated in ACC!\n\n"
            f"GUID: {guid}\n"
            f"Status: {status}\n"
            f"Project: {project_id}"
        )
    else:
        print("Bot: ACC issue update failed:", resp.status_code, resp.text[:500])
        error_msg = "Unknown error"
        try:
            error_data = resp.json()
            error_msg = error_data.get("error", str(error_data))
        except:
            error_msg = resp.text[:200]
        
        await msg.reply_text(
            f"Issue update logged for GUID {guid} (Project: {project_id}), "
            f"but ACC update FAILED (HTTP {resp.status_code}).\n\n"
            f"Error: {error_msg}"
        )

# -------------------------------------------------------------------
# Telegram handler for [UPDATE] (assets) - UNCHANGED
# -------------------------------------------------------------------

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
            "No Project ID linked to this group yet.\n\n"
            "Please set it once using:\n"
            "Project ID: <project_id>\n\n"
            "Example:\n"
            "Project ID: Pasir Ris-EC-01\n\n"
            "Then resend your [UPDATE] message."
        )
        return


    # Parse the message into a structured dict
    parsed, errors = _parse_update_text(text, message_dt_iso=msg.date.isoformat())

    # If any required fields are missing/blank, STOP here
    if errors:
        await msg.reply_text(
            "Error: Update not logged.\nPlease fix:\n- " + "\n- ".join(errors)
        )
        return

    # --- NLP: get GUID + canonical status (overrides text status) ------
    guid, status_value = resolve_guid_from_nlp(project_id, parsed)

    # DEBUG: confirm what handler received from NLP
    print(f"Bot: handler got from NLP -> GUID={guid}, STATUS={status_value}")

    # If NLP cannot determine GUID or status → log as UNKNOWN and stop
    if not guid or not status_value:
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

        log_site_update("UNKNOWN", payload_for_site_updates, project_id)

        await msg.reply_text(
            "Update logged, but NLP could not determine a valid GUID and status "
            f"for this update. Project: {project_id}."
        )
        return

    # Overwrite parsed status with NLP status so logs & ACC are consistent
    parsed["status"] = status_value

    # Build the payload that we log in site_updates.json
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
        "parsed": parsed,  # now contains NLP status
    }

    # Log the update with the resolved GUID
    clean = log_site_update(guid, payload_for_site_updates, project_id)

    # --- Call Flask /update_status via HTTP using NLP status -----------
    payload = {
        "asset_guid": guid,
        "status_value": status_value,  # from NLP, not from raw text
    }

    print("Bot: calling /update_status with payload:", payload)
    print("API_URL:", API_URL)
    try:
        resp = requests.post(API_URL, json=payload, timeout=15)
    except Exception as e:
        print("Bot: error calling /update_status:", repr(e))
        await msg.reply_text(
            f"Update logged for GUID {guid} (Project: {project_id}), "
            "but failed to contact the ACC server."
        )
        return

    if 200 <= resp.status_code < 300:
        await msg.reply_text(
            f"Update logged and ACC updated for GUID {guid} "
            f"(Project: {project_id})."
        )
    else:
        # Optional: log body for debugging
        print("Bot: ACC update failed:", resp.status_code, resp.text[:500])
        await msg.reply_text(
            f"Update logged for GUID {guid} (Project: {project_id}), "
            f"but ACC update FAILED (HTTP {resp.status_code})."
        )


# Main bootstrap -------------
def main() -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("Please set TELEGRAM_TOKEN environment variable first")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("setproject", cmd_setproject))
    app.add_handler(CommandHandler("issuesinfo", cmd_issues_info))
    app.add_handler(CommandHandler("template", cmd_template))

    # when the bot is added to a group → ask for Project ID
    app.add_handler(ChatMemberHandler(on_new_chat, ChatMemberHandler.MY_CHAT_MEMBER))

    # capture messages like "Project ID: KotaKinabalu-A"
    app.add_handler(
        MessageHandler(filters.Regex(r"(?i)^project\s*id\s*:\s*(.+)"), handle_project_id)
    )


    # IMPORTANT: Order matters! More specific patterns must come first
    
    # Handle [CREATE ISSUE] messages (NEW)
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.ChatType.GROUPS & filters.Regex(r"(?i)^\[CREATE\s+ISSUE\]"),
            create_issue_handler
        )
    )
    
    # Handle [ISSUE STATUS] messages
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.ChatType.GROUPS & filters.Regex(r"(?i)^\[ISSUE\s+STATUS\]"),
            issue_status_handler
        )
    )
    
    # Handle [UPDATE] messages (for assets)
    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.GROUPS, one_shot_update_handler)
    )
    
    print("   Bot is running... listening for messages.")
    print("   Commands available:")
    print("   /template - Show message formats")
    print("   /setproject <id> - Set project ID")
    print("   /issuesinfo - Fetch and display all issue information")
    print("   Message handlers registered:")
    print("   - [CREATE ISSUE] > create_issue")
    print("   - [ISSUE STATUS] > update_issue_status")
    print("   - [UPDATE] > update_status")

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

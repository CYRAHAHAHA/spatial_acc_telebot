from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from datetime import datetime, UTC
from typing import Any, Dict, Optional

from telegram import Message

BASE_DIR = Path(__file__).resolve().parent
ACTIVITY_LOG_PATH = BASE_DIR / "activity_log.json"
LOG_LOCK = Lock()

ACTION_UPDATE_STATUS = "Update Status"
ACTION_CREATE_ISSUE = "Create Issue"
ACTION_UPDATE_ISSUE = "Update Issue"


# ---------- low-level helpers ----------

def _load_log() -> list[dict]:
    if ACTIVITY_LOG_PATH.exists():
        try:
            with open(ACTIVITY_LOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception as e:
            print("ActivityLog: error reading log file:", repr(e))
    return []


def _save_log(entries: list[dict]) -> None:
    with open(ACTIVITY_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _username_from_msg(msg: Message) -> Optional[str]:
    if not msg.from_user:
        return None
    first = msg.from_user.first_name or ""
    last = msg.from_user.last_name or ""
    full = f"{first} {last}".strip()
    return full or msg.from_user.username


def _base_from_msg(msg: Message, project_id: Optional[str]) -> Dict[str, Any]:
    # Format: YYYY-MM-DD (HH:MM:SS)
    dt_obj = msg.date.astimezone(UTC) if msg.date else datetime.now(UTC)
    ts = dt_obj.strftime("%Y-%m-%d (%H:%M:%S)")

    raw_text = (msg.text or msg.caption or "").strip()
    return {
        "timestamp": ts,
        "username": _username_from_msg(msg),
        "raw_text": raw_text,
    }


def _append_entry(entry: dict) -> dict:
    with LOG_LOCK:
        entries = _load_log()
        entries.append(entry)
        _save_log(entries)
    print(f"ActivityLog: appended entry ({entry.get('action_type')}), total={len(entries)}")
    return entry


# ---------- high-level logging APIs ----------

def log_update_status_activity(
    *,
    msg: Message,
    project_id: Optional[str],
    guid: Optional[str],
    status: Optional[str],
    error: Optional[str],
) -> dict:
    """
    Activity log for [UPDATE] (assets).
    Payload: { guid, status }
    """
    base = _base_from_msg(msg, project_id)

    entry = {
        "action_type": ACTION_UPDATE_STATUS,
        "timestamp": base["timestamp"],
        "username": base["username"],
        "payload": {
            "guid": guid,
            "status": status,
        },
        "error": error,
        "raw_text": base["raw_text"],
    }
    return _append_entry(entry)


def log_update_issue_activity(
    *,
    msg: Message,
    project_id: Optional[str],
    guid: Optional[str],
    status: Optional[str],
    error: Optional[str],
) -> dict:
    """
    Activity log for [ISSUE STATUS].
    Payload: { guid, status }
    """
    base = _base_from_msg(msg, project_id)

    entry = {
        "action_type": ACTION_UPDATE_ISSUE,
        "timestamp": base["timestamp"],
        "username": base["username"],
        "payload": {
            "guid": guid,
            "status": status,
        },
        "error": error,
        "raw_text": base["raw_text"],
    }
    return _append_entry(entry)


def log_create_issue_activity(
    *,
    msg: Message,
    project_id: Optional[str],
    subtype_id: Optional[str],
    status: Optional[str],
    title: Optional[str],
    description: Optional[str],
    error: Optional[str],
) -> dict:
    """
    Activity log for [CREATE ISSUE].
    Payload: { subtype_id, status, title, description }
    """
    base = _base_from_msg(msg, project_id)

    entry = {
        "action_type": ACTION_CREATE_ISSUE,
        "timestamp": base["timestamp"],
        "username": base["username"],
        "payload": {
            "subtype_id": subtype_id,
            "status": status,
            "title": title,
            "description": description,
        },
        "error": error,
        "raw_text": base["raw_text"],
    }
    return _append_entry(entry)

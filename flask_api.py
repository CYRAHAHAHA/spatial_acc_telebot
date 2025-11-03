# To run: python flask_api.py
# Receives POSTs from bot_logger.py and writes pretty site_updates.json

from flask import Flask, request, jsonify, abort
import json, os, re
from datetime import datetime, timezone
from threading import Lock
from uuid import UUID
from pathlib import Path

app = Flask(__name__)

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
AUTH_TOKEN = os.getenv("SITE_UPDATES_TOKEN", "super-secret-token")

SITE_UPDATES_PATH = Path("site_updates.json")  # pretty JSON array file

# In-memory store (optional, helpful for versioning and quick lookups)
DB = {}
DB_LOCK = Lock()

GUID_RE = re.compile(r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def is_guid(g: str) -> bool:
    try:
        UUID(g)
        return True
    except Exception:
        return False


def iso_date_from_timestamp(ts: str | None) -> str:
    """
    Extract YYYY-MM-DD safely from a timestamp string like:
    '2025-10-31T03:07:39+00:00' or '2025-10-31'. If missing/invalid,
    fallback to today's UTC date.
    """
    if not ts:
        return datetime.now(timezone.utc).date().isoformat()
    # common ISO-8601: split on 'T' if present
    if "T" in ts:
        return ts.split("T", 1)[0]
    # if it's already YYYY-MM-DD, return as-is; otherwise fallback
    try:
        return datetime.fromisoformat(ts).date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()


def append_pretty_update(entry: dict, path: Path = SITE_UPDATES_PATH) -> None:
    """
    Append one entry into a JSON array file with pretty formatting.
    Creates the file if missing.
    """
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as rf:
                data = json.load(rf)
            if not isinstance(data, list):
                data = []
        except Exception:
            data = []
    else:
        data = []
    data.append(entry)
    with open(path, "w", encoding="utf-8") as wf:
        json.dump(data, wf, ensure_ascii=False, indent=2)
        wf.write("\n")


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.route("/site-updates/<guid>", methods=["POST"])
def update_guid(guid: str):
    # Security: Bearer token
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth.split(" ", 1)[1] != AUTH_TOKEN:
        abort(401)

    # Validate GUID
    if not GUID_RE.match(guid) or not is_guid(guid):
        return jsonify({"ok": False, "error": "invalid_guid"}), 400

    # Get JSON payload from bot
    payload = request.get_json(force=True) or {}

    # Pull date from payload timestamp (YYYY-MM-DD)
    date_only = iso_date_from_timestamp(payload.get("timestamp"))

    # The 'parsed' object sent by the bot (already normalized)
    parsed = payload.get("parsed") or {}

    # Update in-memory DB and versioning
    with DB_LOCK:
        rec = DB.get(guid) or {"guid": guid, "version": 0, "history": []}
        rec["version"] += 1
        rec["updated_at"] = datetime.now(timezone.utc).isoformat()
        rec["last"] = payload
        rec["history"].append(payload)
        DB[guid] = rec

        # Clean, human-friendly entry (no raw_text)
        clean_payload = {
            "guid": guid,
            "version": rec["version"],
            "date": date_only,
            "parsed": parsed,
        }

        # Write to pretty JSON array
        append_pretty_update(clean_payload)

    return jsonify({"ok": True, "guid": guid, "version": DB[guid]["version"]})


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
if __name__ == "__main__":
    # host 0.0.0.0 lets other machines reach you later (e.g., on LAN)
    # port 8080 must match FLASK_BASE in your bot code
    app.run(host="0.0.0.0", port=8080, debug=True)

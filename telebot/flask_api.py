# To run: python flask_api.py
# Receives POST from bot_logger.py and writes site_updates.json

from flask import Flask, request, jsonify, abort
import json, os, re
from datetime import datetime
from threading import Lock
from uuid import UUID
from pathlib import Path
import sys

# --- Fix Python path so we can import from root/app ---
sys.path.append(str(Path(__file__).resolve().parents[1] / "root"))

# --- Project imports ---
from app.authentication import AutodeskAuth
from app.config import config
from app.functions.update_status import update_assets

          

app = Flask(__name__)

AUTH_TOKEN = os.getenv("SITE_UPDATES_TOKEN", "super-secret-token")

# Initialize AutodeskAuth using credentials from config.py
auth = AutodeskAuth(
    client_id=config.client_id,
    client_secret=config.client_secret,
    redirect_uri=config.redirect_uri,
    scopes=config.scopes or "data:read data:write account:read"
)


# Base dir of this file so we always write to the same folder as flask_api.py
BASE_DIR = Path(__file__).resolve().parent
SITE_UPDATES_PATH = BASE_DIR / "site_updates.json"

DB = {}
DB_LOCK = Lock()


GUID_RE = re.compile(r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")


def is_guid(g: str) -> bool:
    try:
        UUID(g)
        return True
    except Exception:
        return False


def append_pretty_update(entry: dict) -> None:
    """
    Append one entry into site_updates.json, stored as a JSON array.
    """
    print("Flask: writing entry to", SITE_UPDATES_PATH)  # debug

    if SITE_UPDATES_PATH.exists():
        try:
            with open(SITE_UPDATES_PATH, "r", encoding="utf-8") as rf:
                data = json.load(rf)
            if not isinstance(data, list):
                data = []
        except Exception as e:
            print("Flask: error reading existing JSON:", repr(e))
            data = []
    else:
        data = []

    data.append(entry)

    with open(SITE_UPDATES_PATH, "w", encoding="utf-8") as wf:
        json.dump(data, wf, ensure_ascii=False, indent=2)
        wf.write("\n")
    print("Flask: write complete, total entries:", len(data))  # debug


@app.route("/site-updates/<guid>", methods=["POST"])
def update_guid(guid: str):
    # Security: Bearer token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer ") or auth_header.split(" ", 1)[1] != AUTH_TOKEN:
        abort(401)

    # Validate GUID format
    if not GUID_RE.match(guid) or not is_guid(guid):
        return jsonify({"ok": False, "error": "invalid_guid"}), 400

    payload = request.get_json(force=True) or {}
    print("Flask: received payload for GUID", guid)  # debug

    # Pull timestamp -> date (YYYY-MM-DD)
    full_ts = payload.get("timestamp", "")
    date_only = full_ts.split("T")[0] if "T" in full_ts else full_ts

    parsed = payload.get("parsed") or {}
    loc = parsed.get("location") or {}
    area = parsed.get("area") or {}

    # Build 'location' string: "Building C, Level 8"
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
        location_str = loc  # in case future versions send a string already

    # Build 'area' string: "Grid 5-7, East Wing"
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

    # Flatten and clean the parsed fields
    flattened_parsed = {
        "location": location_str,
        "area": area_str,
        "task": parsed.get("task"),
        "status": parsed.get("status"),
        "remarks": parsed.get("remarks"),
    }

    # In-memory versioning + save to site_updates.json
    with DB_LOCK:
        rec = DB.get(guid) or {"guid": guid, "version": 0, "history": []}
        rec["version"] += 1
        rec["updated_at"] = datetime.utcnow().isoformat() + "Z"
        rec["last"] = payload
        rec["history"].append(payload)
        DB[guid] = rec

        clean_payload = {
            "guid": guid,
            "version": rec["version"],
            "date": date_only,
            "parsed": flattened_parsed,
        }

        append_pretty_update(clean_payload)

    # --- 🔹 APS/ACC Update Section (New) ---
    status_value = flattened_parsed.get("status")

    # If no status is found, skip the ACC update
    if not status_value:
        return jsonify({
            "ok": True,
            "guid": guid,
            "version": DB[guid]["version"],
            "note": "Update logged locally, but no status provided so ACC update skipped."
        }), 200

    # Get Autodesk access token using your authentication.py class
    try:
        access_token = auth.get_access_token()
    except Exception as e:
        return jsonify({
            "ok": True,
            "guid": guid,
            "version": DB[guid]["version"],
            "warning": f"Update logged, but failed to get APS token: {e}"
        }), 200

    # Call your teammate’s update_assets() to update the status in ACC
    acc_resp, acc_status = update_assets(
        access_token=access_token,
        asset_guid=guid,          # The GUID from Telegram → IFC Global ID
        status_value=status_value # The parsed “Completed” / “In Progress” label
    )

    # Try reading ACC response body
    try:
        acc_body = acc_resp.get_json()
    except Exception:
        acc_body = str(acc_resp)

    # Return combined response (local + ACC)
    return jsonify({
        "ok": True,
        "guid": guid,
        "version": DB[guid]["version"],
        "acc_update": acc_body
    }), acc_status


if __name__ == "__main__":
    print("Flask API starting. Writing to", SITE_UPDATES_PATH)
    app.run(host="0.0.0.0", port=8080, debug=True)

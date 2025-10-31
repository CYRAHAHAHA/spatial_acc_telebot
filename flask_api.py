#To run the flask: python flask_api.py
#Receive POST request from tele
#Update seen in site_update.jsonl
from flask import Flask, request, jsonify, abort
import json, os
from datetime import datetime
from threading import Lock
from uuid import UUID
import re

app = Flask(__name__)

AUTH_TOKEN = os.getenv("SITE_UPDATES_TOKEN", "super-secret-token")

DB = {}
DB_LOCK = Lock()
LOG_PATH = "site_updates.jsonl"

GUID_RE = re.compile(r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")

def is_guid(g):
    try:
        UUID(g)
        return True
    except:
        return False

@app.route("/site-updates/<guid>", methods=["POST"])
def update_guid(guid):
    # Security check
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth.split(" ",1)[1] != AUTH_TOKEN:
        abort(401)

    if not GUID_RE.match(guid) or not is_guid(guid):
        return jsonify({"ok": False, "error": "invalid_guid"}), 400

    payload = request.get_json(force=True)

    with DB_LOCK:
        rec = DB.get(guid) or {"guid": guid, "version": 0, "history": []}
        rec["version"] += 1
        rec["updated_at"] = datetime.utcnow().isoformat() + "Z"
        rec["last"] = payload
        rec["history"].append(payload)
        DB[guid] = rec

        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"guid": guid, "version": rec["version"], **payload}) + "\n")

    return jsonify({"ok": True, "guid": guid, "version": DB[guid]["version"]})

from flask import redirect, request, session, jsonify
from app import app
from app.functions.fetch_assets_config import fetch_assets_config
from app.utils import require_access_token
from app.config import config
from app.functions.create_status_sets import create_status_sets
from app.functions.create_custom_fields import create_custom_fields
from urllib.parse import quote_plus
from pathlib import Path
from app.functions.update_status import update_assets
from app.functions.fetch_all_assets_info import fetch_all_assets_info 
import csv
import json
import re

# Auth flow
@app.route("/authorize")
def authorize():
    auth_url = app.autodesk_auth.get_auth_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return redirect("/?msg=" + quote_plus("No authorization code received."))
    token = app.autodesk_auth.exchange_code_for_tokens(code)
    if not token:
        return redirect("/?msg=" + quote_plus("Token exchange failed."))
    session["access_token"] = token
    return redirect("/?msg=" + quote_plus("Authenticated successfully."))

@app.route("/switch_user/<user>")
def switch_user(user):
    config.switch_user(user)
    session.pop("access_token", None)
    return redirect("/")

@app.route("/fetch_assets_config")
@require_access_token(pass_token=True)
def fetch_assets(token):
    return fetch_assets_config(token)

@app.route("/fetch_all_assets_info")
@require_access_token(pass_token=True)
def fetch_all_assets(token):
    return fetch_all_assets_info(token)

@app.route("/update_status", methods=["POST"])
@require_access_token(pass_token=True)
def update_status(token):
    data = request.get_json(silent=True) or {}
    asset_guid = data.get("asset_guid")
    status_value = data.get("status_value")
    if not asset_guid or not status_value:
        return jsonify({"error": "Missing asset_guid or status_value"}), 400
    return update_assets(token, asset_guid, status_value)

# --- Payload APIs (read hardcoded JSON files for creation) ---
@app.route("/api/payload/status_sets")
def api_payload_status_sets():
    data_dir = Path(__file__).resolve().parents[1] / "data"
    p = data_dir / "new_status_sets.json"
    try:
        with p.open("r", encoding="utf-8") as f:
            items = json.load(f)
        if not isinstance(items, list):
            return jsonify({"error": "new_status_sets.json must be a JSON array."}), 400
        return jsonify(items)
    except Exception as ex:
        return jsonify({"error": f"Failed to read new_status_sets.json: {ex}"}), 404

@app.route("/api/payload/custom_fields")
def api_payload_custom_fields():
    data_dir = Path(__file__).resolve().parents[1] / "data"
    p = data_dir / "new_custom_fields.json"
    try:
        with p.open("r", encoding="utf-8") as f:
            items = json.load(f)
        if not isinstance(items, list):
            return jsonify({"error": "new_custom_fields.json must be a JSON array."}), 400
        return jsonify(items)
    except Exception as ex:
        return jsonify({"error": f"Failed to read new_custom_fields.json: {ex}"}), 404

# --- CSV preview APIs (no auth required) ---
@app.route("/api/preview/status_sets")
def api_preview_status_sets():
    """
    Read data/status_sets.csv and return grouped JSON by status_set_id.
    """
    data_dir = Path(__file__).resolve().parents[1] / "data"
    p = data_dir / "status_sets.csv"
    if not p.exists():
        return jsonify({"error": "status_sets.csv not found"}), 404

    sets = {}
    try:
        with p.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ss_id = row.get("status_set_id") or ""
                ss_name = row.get("status_set_name") or ""
                status = {
                    "statusId": row.get("status_id") or "",
                    "label": row.get("status_label") or "",
                    "description": row.get("status_description") or "",
                }
                if ss_id not in sets:
                    sets[ss_id] = {
                        "statusSetId": ss_id,
                        "name": ss_name,
                        "statuses": [],
                    }
                sets[ss_id]["statuses"].append(status)
        items = list(sets.values())
        return jsonify({"count": len(items), "items": items})
    except Exception as ex:
        return jsonify({"error": f"Failed to read status_sets.csv: {ex}"}), 500

@app.route("/api/preview/custom_fields")
def api_preview_custom_fields():
    """
    Read data/custom_fields.csv and return normalized JSON list.
    """
    data_dir = Path(__file__).resolve().parents[1] / "data"
    p = data_dir / "custom_fields.csv"
    if not p.exists():
        return jsonify({"error": "custom_fields.csv not found"}), 404

    out = []
    pat = re.compile(r"^(.*)\(([^)]+)\)$")  # Label(id)
    try:
        with p.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                enum_pairs = []
                raw = (row.get("values_and_ids") or "").strip()
                if raw:
                    parts = [s.strip() for s in raw.split(";") if s.strip()]
                    for part in parts:
                        m = pat.match(part)
                        if m:
                            enum_pairs.append({"label": m.group(1).strip(), "id": m.group(2).strip()})
                        else:
                            enum_pairs.append({"label": part, "id": ""})
                else:
                    raw_vals = (row.get("values") or "").strip()
                    if raw_vals:
                        enum_pairs = [{"label": s.strip(), "id": ""} for s in raw_vals.split(",") if s.strip()]

                item = {
                    "id": row.get("custom_attribute_id") or "",
                    "displayName": row.get("display_name") or "",
                    "description": row.get("description") or "",
                    "dataType": row.get("data_type") or "",
                    "requiredOnIngress": str(row.get("required") or "").strip().lower() in ("true", "1", "yes", "y"),
                    "enumValues": enum_pairs,  # list of {label,id}
                }
                out.append(item)
        return jsonify({"count": len(out), "items": out})
    except Exception as ex:
        return jsonify({"error": f"Failed to read custom_fields.csv: {ex}"}), 500

# --- Creation APIs (accept JSON payload from client) ---
@app.route("/create_status_sets_from_json", methods=["POST"])
@require_access_token(pass_token=True)
def create_status_sets_from_json(token):
    items = request.get_json(silent=True)
    if not isinstance(items, list):
        return jsonify({"error": "Invalid payload: expected a JSON array."}), 400
    created = create_status_sets(token, items) or []
    return jsonify({"created": len(created)}), 200

@app.route("/create_custom_fields_from_json", methods=["POST"])
@require_access_token(pass_token=True)
def create_custom_fields_from_json(token):
    items = request.get_json(silent=True)
    if not isinstance(items, list):
        return jsonify({"error": "Invalid payload: expected a JSON array."}), 400
    created = create_custom_fields(token, items) or []
    return jsonify({"created": len(created)}), 200
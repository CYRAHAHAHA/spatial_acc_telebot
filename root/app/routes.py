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
from app.functions.create_categories import create_categories
import json

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

# ---- API: assets config and status updates ---- #
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

@app.route("/create_categories_from_json", methods=["POST"])
@require_access_token(pass_token=True)
def create_categories_from_json(token):
    items = request.get_json(silent=True)
    if not isinstance(items, list):
        return jsonify({"error": "Invalid payload: expected a JSON array."}), 400
    created = create_categories(token, items) or []
    return jsonify({"created": len(created)}), 200

@app.route("/api/payload/categories")
def api_payload_categories():
    data_dir = Path(__file__).resolve().parents[1] / "data"
    p = data_dir / "new_categories.json"
    try:
        with p.open("r", encoding="utf-8") as f:
            items = json.load(f)
        if not isinstance(items, list):
            return jsonify({"error": "new_categories.json must be a JSON array."}), 400
        return jsonify(items)
    except Exception as ex:
        return jsonify({"error": f"Failed to read new_categories.json: {ex}"}), 404
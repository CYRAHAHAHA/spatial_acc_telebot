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
from app.functions.update_issue import update_issue 
from app.functions.create_issue import create_issue

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


@app.route("/update_issue", methods=["POST"])
@require_access_token(pass_token=True)
def update_issue_route(token):
    data = request.get_json(silent=True) or {}
    issue_guid = data.get("issue_guid")
    new_status = data.get("new_status")
    if not issue_guid or not new_status:
        return jsonify({"error": "Missing issue_guid or new_status"}), 400
    return update_issue(token, issue_guid, new_status)

@app.route("/create_issue", methods=["POST"])
@require_access_token(pass_token=True)
def create_issue_route(token):
    data = request.get_json(silent=True) or {}
    
    # Required fields
    title = data.get("title")
    status = data.get("status")
    
    # Optional fields
    issue_subtype_id = data.get("issue_subtype_id")
    owner_id = data.get("owner_id")
    description = data.get("description")
    due_date = data.get("due_date")
    location_description = data.get("location_description")
    
    if not title or not status:
        return jsonify({"error": "Missing required fields: title and status"}), 400
    
    return create_issue(
        token,
        title,
        status,
        issue_subtype_id,
        owner_id,
        description,
        due_date,
        location_description
    )
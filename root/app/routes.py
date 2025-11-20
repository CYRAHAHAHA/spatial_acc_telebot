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
from app.functions.fetch_issue_subtypes import fetch_issue_subtypes, format_subtypes_output
import json
import requests

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

# ---- Bot Update Endpoints (No User Auth Required) ---- #

@app.route("/update_status_from_bot", methods=["POST"])
def update_status_from_bot():
    """
    Dedicated endpoint for Telegram bot to update ASSET status.
    Uses stored system tokens from autodesk_tokens.json instead of user session.
    
    Expects: {"asset_guid": "1$p8tACJ938vr1_lKOJJ9g", "status_value": "Completed"}
    """
    data = request.get_json(silent=True) or {}
    asset_guid = data.get("asset_guid")
    status_value = data.get("status_value")
    
    if not asset_guid or not status_value:
        return jsonify({"error": "Missing asset_guid or status_value"}), 400
    
    # Get token from app's auth instance (automatically loads from autodesk_tokens.json)
    token = app.autodesk_auth.get_access_token()
    
    if not token:
        return jsonify({
            "error": "No valid authentication token available.",
            "hint": "Visit http://localhost:8080/authorize to authenticate with Autodesk"
        }), 401
    
    print(f"[BOT → ASSET] Update request: GUID={asset_guid}, Status={status_value}")
    
    # Use the same update_assets function as the authenticated endpoint
    result = update_assets(token, asset_guid, status_value)
    
    print(f"[BOT → ASSET] Result: {result}")
    
    return result


@app.route("/update_issue_from_bot", methods=["POST"])
def update_issue_from_bot():
    """
    Dedicated endpoint for Telegram bot to update ISSUE status.
    Uses stored system tokens from autodesk_tokens.json.
    
    Expects: {"issue_guid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", "status_value": "closed"}
    """
    from app.functions.update_issue import update_issue
    
    data = request.get_json(silent=True) or {}
    issue_guid = data.get("issue_guid")
    status_value = data.get("status_value")
    
    if not issue_guid or not status_value:
        return jsonify({"error": "Missing issue_guid or status_value"}), 400
    
    token = app.autodesk_auth.get_access_token()
    
    if not token:
        return jsonify({
            "error": "No valid authentication token available.",
            "hint": "Visit http://localhost:8080/authorize to authenticate"
        }), 401
    
    print(f"[BOT → ISSUE] Update request: GUID={issue_guid}, Status={status_value}")
    
    # Call update_issue function from update_issue.py
    result = update_issue(token, issue_guid, status_value)
    
    print(f"[BOT → ISSUE] Result: {result}")
    
    return result

@app.route("/create_issue_from_bot", methods=["POST"])
def create_issue_from_bot():
    """
    Dedicated endpoint for Telegram bot to CREATE a new issue.
    Uses stored system tokens from autodesk_tokens.json.
    
    Expects: {
        "title": "Issue title",
        "status": "open",
        "issue_subtype_id": "subtype-uuid",
        "description": "Optional description",
        "location_description": "Optional location"
    }
    """
    from app.functions.create_issue import create_issue
    
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    status = data.get("status", "open")  # Default to "open"
    issue_subtype_id = data.get("issue_subtype_id")
    description = data.get("description")
    location_description = data.get("location_description")
    
    if not title:
        return jsonify({"error": "Missing required field: title"}), 400
    
    token = app.autodesk_auth.get_access_token()
    
    if not token:
        return jsonify({
            "error": "No valid authentication token available.",
            "hint": "Visit http://localhost:8080/authorize to authenticate"
        }), 401
    
    print(f"[BOT → CREATE ISSUE] Request: title={title}, status={status}")
    
    # Call create_issue function
    result = create_issue(
        access_token=token,
        title=title,
        status=status,
        issue_subtype_id=issue_subtype_id,
        description=description,
        location_description=location_description
    )
    
    print(f"[BOT → CREATE ISSUE] Result: {result}")
    
    return result


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

# ---- Issue Subtypes API ---- #
@app.route("/fetch_issue_subtypes")
@require_access_token(pass_token=True)
def fetch_subtypes(token):
    """
    Fetch all issue subtypes from ACC project.
    Returns JSON with subtype details and also prints to console.
    """
    print("\n" + "=" * 80)
    print("🔍 FETCHING ISSUE SUBTYPES...")
    print("=" * 80)
    
    all_subtypes = fetch_issue_subtypes(token)
    
    if not all_subtypes:
        print("\n❌ No subtypes found!")
        print("Make sure you have project access or issue types configured in ACC.")
        return jsonify({
            "success": False,
            "error": "No issue subtypes found. Check your ACC configuration.",
            "count": 0
        }), 400
    
    # Format output for console and file
    console_output, grouped = format_subtypes_output(all_subtypes)
    print(console_output)
    
    # Save to file in root directory
    output_file = Path(__file__).resolve().parents[2] / "issue_subtypes.json"
    try:
        with open(output_file, "w") as f:
            json.dump(all_subtypes, f, indent=2)
        print(f"\n💾 SAVED TO FILE: {output_file}")
    except Exception as e:
        print(f"⚠️ Could not save to file: {e}")
    
    # Build Python dictionary string for copy-paste
    python_dict_lines = []
    python_dict_lines.append("ISSUE_SUBTYPES = {")
    for type_name, subtypes in sorted(grouped.items()):
        python_dict_lines.append(f"    # {type_name}")
        for sub in sorted(subtypes, key=lambda x: x["subtype"]):
            key = f"{type_name}_{sub['subtype']}".replace(" ", "_").replace("-", "_").upper()
            python_dict_lines.append(f'    "{key}": "{sub["id"]}",')
        python_dict_lines.append("")
    python_dict_lines.append("}")
    python_dict = "\n".join(python_dict_lines)
    
    return jsonify({
        "success": True,
        "count": len(all_subtypes),
        "subtypes": all_subtypes,
        "grouped": grouped,
        "python_dict": python_dict
    }), 200


@app.route("/fetch_issue_info_from_bot", methods=["GET"])
def fetch_issue_info_from_bot():
    """
    Telegram bot endpoint to fetch issue subtypes and issues list.
    Returns formatted info about issue types, subtypes, and existing issues.
    """
    token = app.autodesk_auth.get_access_token()
    
    if not token:
        return jsonify({
            "error": "No valid authentication token.",
            "hint": "Visit http://localhost:8080/authorize to authenticate"
        }), 401
    
    print("[BOT → INFO] Fetching issue subtypes and issues...")
    
    # Fetch issue subtypes
    all_subtypes = fetch_issue_subtypes(token)
    
    # Fetch existing issues list
    issues_url = f"https://developer.api.autodesk.com/construction/issues/v1/projects/{config.project_id}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    all_issues = []
    try:
        issues_response = requests.get(issues_url, headers=headers, timeout=10)
        if issues_response.status_code == 200:
            all_issues = issues_response.json().get("results", [])
            print(f"[BOT → INFO] Found {len(all_issues)} issues")
        else:
            print(f"[BOT → INFO] Failed to fetch issues: {issues_response.status_code}")
    except Exception as e:
        print(f"[BOT → INFO] Error fetching issues: {e}")
    
    # Format response for Telegram
    response = {
        "success": True,
        "subtypes_count": len(all_subtypes),
        "issues_count": len(all_issues),
        "subtypes": all_subtypes,
        "issues": [
            {
                "id": issue.get("id"),
                "title": issue.get("title"),
                "status": issue.get("status"),
                "type": issue.get("issueTypeName"),
                "subtype": issue.get("issueSubtypeName"),
                "created": issue.get("createdAt"),
            }
            for issue in all_issues
        ]
    }
    
    return jsonify(response), 200
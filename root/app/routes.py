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
from app.functions.update_issue import update_issue
from app.functions.create_issue import create_issue
from app.functions.fetch_all_assets_info import fetch_all_assets_info 
from app.functions.create_categories import create_categories
from app.functions.fetch_issue_subtypes import fetch_issue_subtypes, format_subtypes_output
import json
import logging
import requests

logger = logging.getLogger(__name__)

# Auth flow
@app.route("/authorize")
def authorize():
    logger.info("Authorization request received")
    auth_url = app.autodesk_auth.get_auth_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return redirect("/?msg=No+authorization+code+received.")
    
    token = app.autodesk_auth.exchange_code_for_tokens(code)
    if not token:
        return redirect("/?msg=Token+exchange+failed.")
    
    session["access_token"] = token
    return redirect("/?msg=Authenticated+successfully.")

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
    """
    Update asset status in ACC.
    Expected JSON: {"asset_guid": "...", "status_value": "..."}
    """
    data = request.get_json(silent=True) or {}
    asset_guid = data.get("asset_guid")
    status_value = data.get("status_value")
    
    if not asset_guid or not status_value:
        return jsonify({"error": "Missing asset_guid or status_value"}), 400
    
    return update_assets(token, asset_guid, status_value)

# ---- Issue status update endpoint ---- #
@app.route("/update_issue_status", methods=["POST"])
@require_access_token(pass_token=True)
def update_issue_status(token):
    """
    Update an issue's status in ACC.
    
    Expected JSON body:
    {
        "issue_guid": "cae94f63-282c-435b-b798-ec527afcde1d",
        "status_value": "open"
    }
    """
    data = request.get_json(silent=True) or {}
    issue_guid = data.get("issue_guid")
    status_value = data.get("status_value")
    
    if not issue_guid or not status_value:
        return jsonify({"error": "Missing issue_guid or status_value"}), 400
    
    # Call your existing update_issue function
    return update_issue(token, issue_guid, status_value)

# ---- Create issue endpoint ---- #
@app.route("/create_issue", methods=["POST"])
@require_access_token(pass_token=True)
def create_issue_endpoint(token):
    """
    Create a new issue in ACC.
    
    Expected JSON body:
    {
        "title": "Water leakage at Level 3",
        "status": "open",
        "issue_subtype_id": "06e9ad10-7a05-43e8-9e27-38fb455dd50f",
        "description": "Water leaking from ceiling",  // optional
        "location_description": "Building A, Level 3"  // optional
    }
    """
    data = request.get_json(silent=True) or {}
    
    title = data.get("title")
    status = data.get("status")
    issue_subtype_id = data.get("issue_subtype_id")
    description = data.get("description")
    location_description = data.get("location_description")
    
    if not title or not status:
        return jsonify({"error": "Missing required fields: title and status"}), 400
    
    # Call your existing create_issue function
    return create_issue(
        access_token=token,
        title=title,
        status=status,
        issue_subtype_id=issue_subtype_id,
        description=description,
        location_description=location_description
    )

# ---- Fetch issue subtypes and recent issues endpoint ---- #
@app.route("/fetch_issue_subtypes")
@require_access_token(pass_token=True)
def fetch_subtypes(token):
    """
    Fetch all issue subtypes and recent issues from ACC.
    Returns JSON with all subtypes grouped by type and recent issues.
    Does NOT save to file.
    """
    try:
        logger.info("Fetching issue information from ACC...")
        
        # Fetch subtypes using your function
        all_subtypes = fetch_issue_subtypes(token)
        
        # Format for display
        console_output, grouped = format_subtypes_output(all_subtypes)
        
        # Print to console (handle encoding safely)
        try:
            print(console_output)
        except UnicodeEncodeError:
            # Fallback: encode with UTF-8 and ignore errors
            print(console_output.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        
        # Fetch recent issues
        logger.info("Fetching recent issues...")
        project_id = config.project_id
        issues_url = f"https://developer.api.autodesk.com/construction/issues/v1/projects/{project_id}/issues"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        recent_issues = []
        try:
            issues_response = requests.get(issues_url, headers=headers, timeout=10)
            if issues_response.status_code == 200:
                issues_data = issues_response.json().get("results", [])
                # Get all issues or limit to recent ones
                recent_issues = issues_data  # You can add [:20] to limit to 20 issues
                logger.info(f"Fetched {len(recent_issues)} recent issues")
            else:
                logger.warning(f"Failed to fetch issues: {issues_response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching issues: {e}")
        
        # Return JSON response (no file saving)
        return jsonify({
            "success": True,
            "total_count": len(all_subtypes),
            "grouped_by_type": grouped,
            "all_subtypes": all_subtypes,
            "recent_issues": recent_issues
        }), 200
        
    except Exception as ex:
        logger.error(f"Failed to fetch issue information: {str(ex)}", exc_info=True)
        return jsonify({
            "error": f"Failed to fetch issue information: {str(ex)}"
        }), 500

# --- Create custom fields, status sets, then categories in one go ---
@app.route("/setup_initial_configs", methods=["POST"])
@require_access_token(pass_token=True)
def setup_initial_configs(token):
    try:
        logger.info("Starting initial configuration setup...")
        # Read from initial folder in root\initial
        initial_dir = Path(__file__).resolve().parents[1] / "initial"
        
        # 1. Create status sets first
        logger.info("Step 1: Creating status sets...")
        ss_path = initial_dir / "new_status_sets.json"
        with ss_path.open("r", encoding="utf-8") as f:
            status_sets_data = json.load(f)
        created_ss = create_status_sets(token, status_sets_data) or []
        logger.info(f"Created {len(created_ss)} status sets")
        
        # 2. Create custom fields
        logger.info("Step 2: Creating custom fields...")
        cf_path = initial_dir / "new_custom_fields.json"
        with cf_path.open("r", encoding="utf-8") as f:
            custom_fields_data = json.load(f)
        created_cf = create_custom_fields(token, custom_fields_data) or []
        logger.info(f"Created {len(created_cf)} custom fields")
        
        # 2.5. Fetch assets config to refresh CSV files with newly created status sets and custom fields
        logger.info("Step 2.5: Fetching assets config to refresh CSV files...")
        fetch_assets_config(token)
        logger.info("CSV files refreshed successfully")
        
        # 3. Create categories (now they can reference updated CSVs)
        logger.info("Step 3: Creating categories...")
        cat_path = initial_dir / "new_categories.json"
        with cat_path.open("r", encoding="utf-8") as f:
            categories_data = json.load(f)
        created_cat = create_categories(token, categories_data) or []
        logger.info(f"Created {len(created_cat)} categories")
        
        logger.info("Initial configuration setup completed successfully!")
        return jsonify({
            "message": "Initial configurations set up successfully.",
            "created": {
                "status_sets": len(created_ss),
                "custom_fields": len(created_cf),
                "categories": len(created_cat)
            }
        }), 200
    except Exception as ex:
        logger.error(f"Failed to set up initial configs: {str(ex)}", exc_info=True)
        return jsonify({"error": f"Failed to set up initial configs: {str(ex)}"}), 500

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
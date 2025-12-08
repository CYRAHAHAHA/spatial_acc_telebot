from flask import redirect, request, session, jsonify, send_from_directory
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
from app.functions.fetch_metadata import fetch_ifc_metadata
from app.functions.create_assets import run_create_assets
from app.functions.get_root_folder_id import discover_root_folder
import json
import logging
import requests

logger = logging.getLogger(__name__)

# Serve files from data directory
@app.route('/data/<path:filename>')
def serve_data_files(filename):
    """Serve files from the data directory"""
    data_dir = Path(__file__).resolve().parents[1] / "data"
    return send_from_directory(data_dir, filename)

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
    Expected JSON: {"asset_guid": ["guid1", "guid2", ...], "status_value": "..."}
    Or single GUID: {"asset_guid": "single-guid", "status_value": "..."}
    """
    data = request.get_json(silent=True) or {}
    asset_guid = data.get("asset_guid")
    status_value = data.get("status_value")
    
    if not status_value:
        return jsonify({"error": "Missing status_value"}), 400
    
    # Handle both list and single GUID
    if not asset_guid:
        return jsonify({"error": "Missing asset_guid"}), 400
    
    # Convert single GUID to list for uniform processing
    if isinstance(asset_guid, str):
        asset_guid_list = [asset_guid]
    elif isinstance(asset_guid, list):
        asset_guid_list = asset_guid
    else:
        return jsonify({"error": "asset_guid must be a string or list"}), 400
    
    # Handle empty list
    if len(asset_guid_list) == 0:
        return jsonify({
            "success": True,
            "message": "No assets to update",
            "total": 0,
            "successful": 0,
            "failed": 0,
            "results": []
        }), 200
    
    # Process each GUID
    results = []
    successful = 0
    failed = 0
    
    for guid in asset_guid_list:
        try:
            logger.info(f"Updating asset {guid} to status {status_value}")
            result = update_assets(token, guid, status_value)
            
            # Check if update was successful
            if isinstance(result, tuple):
                response_data, status_code = result
            else:
                response_data = result
                status_code = 200
            
            if status_code == 200:
                successful += 1
                results.append({
                    "asset_guid": guid,
                    "success": True,
                    "status_value": status_value
                })
            else:
                failed += 1
                # Try to extract error message from various response formats
                error_msg = "Unknown error"
                try:
                    if isinstance(response_data, dict):
                        error_msg = response_data.get("error", "Unknown error")
                    else:
                        error_msg = str(response_data)
                except:
                    error_msg = "Unknown error"
                    
                results.append({
                    "asset_guid": guid,
                    "success": False,
                    "error": error_msg
                })
        except Exception as e:
            logger.error(f"Error updating asset {guid}: {str(e)}")
            failed += 1
            results.append({
                "asset_guid": guid,
                "success": False,
                "error": str(e)
            })
    
    return jsonify({
        "success": True,
        "message": f"Processed {len(asset_guid_list)} asset(s)",
        "total": len(asset_guid_list),
        "successful": successful,
        "failed": failed,
        "results": results
    }), 200

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
            print(console_output.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        
        # Fetch recent issues from ACC
        recent_issues = []
        project_id = config.project_id
        
        logger.info(f"🔍 PROJECT_ID from config: {project_id}")
        
        if project_id:
            try:
                # Use v1 API for fetching issues (v2 requires different authentication/format)
                issues_url = f"https://developer.api.autodesk.com/construction/issues/v1/projects/{project_id}/issues"
                
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                
                params = {
                    "limit": 20,
                    "offset": 0
                }
                
                logger.info(f"🔍 Fetching issues from: {issues_url}")
                issues_response = requests.get(issues_url, headers=headers, params=params, timeout=10)
                
                logger.info(f"Response status: {issues_response.status_code}")
                logger.info(f"📊 Response headers: {dict(issues_response.headers)}")
                
                if issues_response.status_code == 200:
                    issues_json = issues_response.json()
                    logger.info(f"📊 Response JSON keys: {list(issues_json.keys())}")
                    logger.info(f"📊 Full response (first 500 chars): {str(issues_json)[:500]}")
                    
                    # Parse v1 API response format
                    if "results" in issues_json:
                        recent_issues = issues_json["results"][:20]
                        logger.info(f"✅ Found issues in 'results' key: {len(recent_issues)} issues")
                    elif "data" in issues_json:
                        recent_issues = issues_json["data"][:20]
                        logger.info(f"✅ Found issues in 'data' key: {len(recent_issues)} issues")
                    elif isinstance(issues_json, list):
                        recent_issues = issues_json[:20]
                        logger.info(f"✅ Response is a list: {len(recent_issues)} issues")
                    else:
                        logger.warning(f"⚠️ Unexpected response format, no recognized key")
                    
                    logger.info(f"✅ Extracted {len(recent_issues)} recent issues")
                else:
                    logger.warning(f"❌ Failed to fetch issues: HTTP {issues_response.status_code}")
                    logger.warning(f"❌ Response: {issues_response.text[:500]}")
                    
            except Exception as e:
                logger.error(f"💥 Error fetching issues: {e}", exc_info=True)
        else:
            logger.warning("⚠️ Missing PROJECT_ID in config")
        
        logger.info(f"📤 Returning {len(recent_issues)} issues in response")
        
        # Return JSON response
        return jsonify({
            "success": True,
            "total_count": len(all_subtypes),
            "grouped_by_type": grouped,
            "all_subtypes": all_subtypes,
            "recent_issues": recent_issues,
            "recent_issues_count": len(recent_issues)
        }), 200
        
    except Exception as ex:
        logger.error(f"❌ Failed to fetch issue information: {str(ex)}", exc_info=True)
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

# ---- API: fetching of metadata ---- #
@app.route("/fetch_metadata")
@require_access_token(pass_token=True)
def fetch_metadata_route(token):
    result = fetch_ifc_metadata(token)   
    return jsonify(result), 200

# ---- API: fetching of metadata ---- #
@app.route("/get_root_folder_id")
@require_access_token(pass_token=True)
def fetch_root_id_route(token):
    result = discover_root_folder(token)   
    return jsonify(result), 200

# ---- API: create assets ---- #
@app.route("/createassets", methods=["POST"])
@require_access_token(pass_token=True)
def upload_ai_assets(token):
    result = run_create_assets(token)
    return jsonify(result)

# --- Fetch Activity Log endpoint ---
@app.route("/fetch_activity_log")
def fetch_activity_log():
    """
    Fetch the activity log from telebot/activity_log.json.
    Returns JSON array of activity log entries with unique IDs added.
    """
    try:
        logger.info("Fetching activity log...")
        # Path to activity log in telebot folder
        activity_log_path = Path(__file__).resolve().parents[2] / "telebot" / "activity_log.json"
        
        if not activity_log_path.exists():
            logger.warning(f"Activity log file not found at {activity_log_path}")
            return jsonify({"error": "Activity log file not found", "path": str(activity_log_path)}), 404
        
        with activity_log_path.open("r", encoding="utf-8") as f:
            activity_log = json.load(f)
        
        # Reverse to show latest entries first
        activity_log.reverse()
        
        # Add unique IDs and ensure all required fields exist
        for idx, entry in enumerate(activity_log):
            if "id" not in entry:
                entry["id"] = f"log-entry-{idx}-{entry.get('timestamp', '').replace(' ', '-').replace(':', '-')}"
            
            # Ensure all required fields are present
            entry.setdefault("action_type", "N/A")
            entry.setdefault("timestamp", "N/A")
            entry.setdefault("username", "N/A")
            entry.setdefault("payload", {})
            entry.setdefault("error", None)
            entry.setdefault("raw_text", "N/A")
            entry.setdefault("raw_message", entry.get("raw_text", "N/A"))  # For compatibility
        
        logger.info(f"Successfully fetched {len(activity_log)} activity log entries")
        return jsonify({
            "success": True,
            "total_count": len(activity_log),
            "logs": activity_log
        }), 200
        
    except json.JSONDecodeError as je:
        logger.error(f"Failed to parse activity log JSON: {str(je)}", exc_info=True)
        return jsonify({"error": f"Invalid JSON format: {str(je)}"}), 500
    except Exception as ex:
        logger.error(f"Failed to fetch activity log: {str(ex)}", exc_info=True)
        return jsonify({"error": f"Failed to fetch activity log: {str(ex)}"}), 500
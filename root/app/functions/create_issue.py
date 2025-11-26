from __future__ import annotations
from typing import Optional, Dict, Any
from flask import jsonify
import requests
from app.config import config

API_BASE_ISSUES = "https://developer.api.autodesk.com/construction/issues/v1/projects"

def _get_current_user_id(access_token: str) -> Optional[str]:
    """
    Fetch the current user's ID from Autodesk API.
    """
    user_url = "https://developer.api.autodesk.com/userprofile/v1/users/@me"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        resp = requests.get(user_url, headers=headers, timeout=30)
        if resp.status_code == 200:
            user_data = resp.json()
            return user_data.get("userId")
    except Exception as e:
        print(f"Error fetching user ID: {e}")
    
    return None

def _get_issue_subtypes(access_token: str, project_id: str) -> Dict[str, Dict[str, str]]:
    """
    Fetch existing issues to discover available issue subtypes.
    Returns a dict mapping subtype_id -> {type, subtype}
    """
    issues_url = f"{API_BASE_ISSUES}/{project_id}/issues"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    subtypes_found = {}
    
    try:
        resp = requests.get(issues_url, headers=headers, timeout=30)
        if resp.status_code == 200:
            issues_data = resp.json().get("results", [])
            print(f"Found {len(issues_data)} existing issues")
            
            for issue in issues_data:
                subtype_id = issue.get("issueSubtypeId")
                subtype_name = issue.get("issueSubtypeName", "Unknown")
                type_name = issue.get("issueTypeName", "Unknown")
                
                if subtype_id and subtype_id not in subtypes_found:
                    subtypes_found[subtype_id] = {
                        "type": type_name,
                        "subtype": subtype_name
                    }
    except Exception as e:
        print(f"Error fetching issue subtypes: {e}")
    
    return subtypes_found

def create_issue(
    access_token: str,
    title: str,
    status: str,
    issue_subtype_id: Optional[str] = None,
    owner_id: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    location_description: Optional[str] = None
):
    """
    Create a new issue in Autodesk Construction Cloud.
    
    Args:
        access_token: Valid Autodesk access token
        title: Issue title (required)
        status: Issue status (e.g., "open", "pending", "closed")
        issue_subtype_id: The issue subtype ID (required). If not provided, will attempt to discover
        owner_id: User ID of the issue owner. If not provided, will use current user
        description: Optional issue description
        due_date: Optional due date (ISO format)
        location_description: Optional location description
    
    Returns:
        JSON response and status code tuple
    """
    project_id = config.project_id
    
    if not title or not status:
        return jsonify({"error": "Missing required fields: title and status"}), 400
    
    # Get current user ID if owner_id not provided
    if not owner_id:
        owner_id = _get_current_user_id(access_token)
        if not owner_id:
            return jsonify({"error": "Could not determine user ID"}), 500
        print(f"Using current user ID: {owner_id}")
    
    # If no subtype ID provided, try to discover available subtypes
    if not issue_subtype_id:
        print("No issue_subtype_id provided, fetching available subtypes...")
        subtypes = _get_issue_subtypes(access_token, project_id)
        
        if not subtypes:
            return jsonify({
                "error": "issue_subtype_id is required but none provided. No existing issues found to discover subtypes.",
                "hint": "Create an issue manually in ACC first, or provide issue_subtype_id in the request"
            }), 400
        
        # Print available subtypes for reference
        print("Available Issue Subtypes:")
        for subtype_id, info in subtypes.items():
            print(f"   • {info['type']} > {info['subtype']} (ID: {subtype_id})")
        
        return jsonify({
            "error": "issue_subtype_id is required",
            "available_subtypes": subtypes,
            "hint": "Choose one of the subtype IDs above and include it in your request"
        }), 400
    
    # Build the payload
    payload = {
        "title": title,
        "status": status,
        "ownerId": owner_id,
        "issueSubtypeId": issue_subtype_id
    }
    
    # Add optional fields if provided
    if description:
        payload["description"] = description
    if due_date:
        payload["dueDate"] = due_date
    if location_description:
        payload["locationDescription"] = location_description
    
    url = f"{API_BASE_ISSUES}/{project_id}/issues"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    print("--- Creating new issue via APS Issues API ---")
    print("POST", url)
    print("Payload:", payload)
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if resp.status_code >= 200 and resp.status_code < 300:
            try:
                result = resp.json()
                issue_id = result.get("id")
                print(f"Issue created successfully! ID: {issue_id}")
                return jsonify(result), resp.status_code
            except Exception:
                return jsonify({"success": True, "message": "Issue created"}), resp.status_code
        else:
            detail = {
                "url": url,
                "status_code": resp.status_code,
                "response": None
            }
            try:
                detail["response"] = resp.json()
            except Exception:
                detail["response"] = resp.text
            detail["request_body"] = payload
            return jsonify({"error": "APS issue creation failed", **detail}), resp.status_code
            
    except requests.RequestException as e:
        return jsonify({"error": f"Request to APS failed: {e}"}), 502
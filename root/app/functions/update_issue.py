from __future__ import annotations
from typing import Optional
from flask import jsonify
import requests
from app.config import config

API_BASE_ISSUES = "https://developer.api.autodesk.com/construction/issues/v1/projects"

def update_issue(access_token: str, issue_guid: str, new_status: str):
    """
    Update a single issue's status in Autodesk Construction Cloud.
    
    Args:
        access_token: Valid Autodesk access token
        issue_guid: The GUID of the issue to update
        new_status: The new status value (e.g., "pending", "open", "closed")
    
    Returns:
        JSON response and status code tuple
    """
    project_id = config.project_id
    
    if not issue_guid or not new_status:
        return jsonify({"error": "Missing issue_guid or new_status"}), 400
    
    url = f"{API_BASE_ISSUES}/{project_id}/issues/{issue_guid}"
    
    payload = {
        "status": new_status
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    print("--- Updating issue status via APS Issues API ---")
    print("PATCH", url, payload)
    
    try:
        resp = requests.patch(url, json=payload, headers=headers, timeout=30)
        
        if resp.status_code >= 200 and resp.status_code < 300:
            try:
                return jsonify(resp.json()), resp.status_code
            except Exception:
                return jsonify({"success": True, "message": f"Issue {issue_guid} updated to '{new_status}'"}), resp.status_code
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
            return jsonify({"error": "APS update failed", **detail}), resp.status_code
            
    except requests.RequestException as e:
        return jsonify({"error": f"Request to APS failed: {e}"}), 502
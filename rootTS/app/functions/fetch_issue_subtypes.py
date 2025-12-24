"""
Fetch all issue subtypes from ACC project.
Tries Configuration API first, then falls back to existing issues.
"""
import requests
import json
from flask import jsonify
from app.config import config

def fetch_issue_subtypes(access_token):
    """
    Fetch all issue subtypes from ACC.
    Returns dict with subtype IDs as keys, containing type/subtype/source info.
    """
    all_subtypes = {}
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # STEP 1: Fetch from ACC Configuration API
    print("\nFetching from ACC Issue Types API (default + custom)...")
    
    types_url = f"https://developer.api.autodesk.com/issues/v1/projects/{config.project_id}/issue-types"
    try:
        types_response = requests.get(types_url, headers=headers, timeout=10)
        
        if types_response.status_code == 200:
            print("   SUCCESS! Retrieved issue types from configuration.")
            types_data = types_response.json().get("results", [])
            
            for issue_type in types_data:
                type_name = issue_type.get("title", "Unknown Type")
                subtypes = issue_type.get("subtypes", [])
                for subtype in subtypes:
                    subtype_id = subtype.get("id")
                    subtype_name = subtype.get("title", "Unknown Subtype")
                    if subtype_id:
                        all_subtypes[subtype_id] = {
                            "type": type_name,
                            "subtype": subtype_name,
                            "source": "Configuration API"
                        }
            
            print(f"   Found {len(all_subtypes)} subtypes from configuration.")
        else:
            print(f"   Failed to fetch issue types ({types_response.status_code})")
            print(f"   Response: {types_response.text[:200]}")
    
    except requests.exceptions.RequestException as e:
        print(f"   Request error: {e}")
    
    # STEP 2: Fallback – Check Existing Issues
    if not all_subtypes:
        print("\nNo configuration data found. Checking existing issues (fallback)...")
        issues_url = f"https://developer.api.autodesk.com/construction/issues/v1/projects/{config.project_id}/issues"
        
        try:
            issues_response = requests.get(issues_url, headers=headers, timeout=10)
            
            if issues_response.status_code == 200:
                issues_data = issues_response.json().get("results", [])
                for issue in issues_data:
                    subtype_id = issue.get("issueSubtypeId")
                    subtype_name = issue.get("issueSubtypeName", "Unknown Subtype")
                    type_name = issue.get("issueTypeName", "Unknown Type")
                    if subtype_id:
                        all_subtypes[subtype_id] = {
                            "type": type_name,
                            "subtype": subtype_name,
                            "source": "Existing Issue"
                        }
                print(f"   Found {len(all_subtypes)} subtypes from existing issues.")
            else:
                print(f"   Could not fetch fallback issues: {issues_response.text[:200]}")
        
        except requests.exceptions.RequestException as e:
            print(f"   Request error: {e}")
    
    return all_subtypes


def format_subtypes_output(all_subtypes):
    """Format subtypes for display and file output."""
    
    # Group by type
    grouped = {}
    for subtype_id, info in all_subtypes.items():
        type_name = info["type"]
        if type_name not in grouped:
            grouped[type_name] = []
        grouped[type_name].append({
            "subtype": info["subtype"],
            "id": subtype_id,
            "source": info["source"]
        })
    
    # Build console output
    output_lines = []
    output_lines.append("\n" + "=" * 80)
    output_lines.append(f" COMPLETE LIST OF ISSUE SUBTYPES ({len(all_subtypes)} total)")
    output_lines.append("=" * 80)
    
    if not all_subtypes:
        output_lines.append("\n No subtypes found!")
        output_lines.append("Make sure you have project access or issue types configured in ACC.")
    else:
        for type_name, subtypes in sorted(grouped.items()):
            output_lines.append(f"\n {type_name}")
            for sub in sorted(subtypes, key=lambda x: x["subtype"]):
                output_lines.append(f"   +- {sub['subtype']}")
                output_lines.append(f"   |  ID: {sub['id']}")
                output_lines.append(f"   |  Source: {sub['source']}")
        
        output_lines.append("\n" + "=" * 80)
        output_lines.append(" PYTHON DICTIONARY:")
        output_lines.append("=" * 80)
        output_lines.append("ISSUE_SUBTYPES = {")
        for type_name, subtypes in sorted(grouped.items()):
            output_lines.append(f"    # {type_name}")
            for sub in sorted(subtypes, key=lambda x: x["subtype"]):
                key = f"{type_name}_{sub['subtype']}".replace(" ", "_").replace("-", "_").upper()
                output_lines.append(f'    "{key}": "{sub["id"]}",')
            output_lines.append("")
        output_lines.append("}")
    
    output_lines.append("=" * 80)
    
    return "\n".join(output_lines), grouped

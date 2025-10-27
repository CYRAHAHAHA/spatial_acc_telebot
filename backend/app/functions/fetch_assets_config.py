import requests, json, urllib.parse
from flask import request, redirect, session
from app.config import config

def fetch_assets_config():
    access_token = request.args.get("access_token")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    project_id = config.project_id
    base_url = "https://developer.api.autodesk.com/construction/assets/v1/projects"

    try:
        # Fetch custom attributes
        ca_resp = requests.get(f"{base_url}/{project_id}/custom-attributes", headers=headers)
        custom_attributes = ca_resp.json().get("results", []) if ca_resp.status_code == 200 else []

        # Fetch status-step sets
        ss_resp = requests.get(f"{base_url}/{project_id}/status-step-sets", headers=headers)
        status_sets = ss_resp.json().get("results", []) if ss_resp.status_code == 200 else []

        # Fetch categories
        cat_resp = requests.get(f"{base_url}/{project_id}/categories", headers=headers)
        categories = cat_resp.json().get("results", []) if cat_resp.status_code == 200 else []

        # Map categories to status sets
        status_sets_dict = {s["id"]: s for s in status_sets}
        categories_with_status = []
        for cat in categories:
            status_set_id = cat.get("statusSetId")
            status_set = status_sets_dict.get(status_set_id, {})
            categories_with_status.append({
                "categoryName": cat.get("name"),
                "statusSetName": status_set.get("name", "None"),
                "statusSetId": status_set_id
            })

        # Aggregate
        aggregated_data = {
            "customAttributes": [{ca.get("displayName"): ca.get("description", "")} for ca in custom_attributes],
            "statusSets": status_sets,
            "categories": categories_with_status
        }

        # Store in session for homepage display
        session["aggregated_data"] = aggregated_data

        # Short redirect message
        msg = urllib.parse.quote_plus(f"Fetched {len(custom_attributes)} attributes, "
                                      f"{len(status_sets)} status sets, "
                                      f"{len(categories)} categories")
        return redirect(f"/?msg={msg}")

    except Exception as e:
        msg = urllib.parse.quote_plus(f"Error fetching assets info: {e}")
        return redirect(f"/?msg={msg}")

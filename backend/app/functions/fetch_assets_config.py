import requests, json, urllib.parse
from flask import request, redirect
from app.config import config

def fetch_assets_config():
    access_token = request.args.get("access_token")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    url = f"https://developer.api.autodesk.com/construction/assets/v1/projects/{config.project_id}/custom-attributes"

    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("results", data if isinstance(data, list) else [])
            output = {item["displayName"]: item.get("description", "") for item in items}
            msg = urllib.parse.quote_plus(f"Custom Attributes fetched: {json.dumps(output)}")
            return redirect(f"/?msg={msg}")
        else:
            msg = urllib.parse.quote_plus(f"Failed to fetch custom attributes: {resp.status_code} {resp.text}")
            return redirect(f"/?msg={msg}")
    except Exception as e:
        msg = urllib.parse.quote_plus(f"Error fetching custom attributes: {e}")
        return redirect(f"/?msg={msg}")

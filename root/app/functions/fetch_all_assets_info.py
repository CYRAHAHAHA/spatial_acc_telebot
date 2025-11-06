from __future__ import annotations
from typing import List, Dict, Any
from pathlib import Path
from urllib.parse import quote_plus
from flask import redirect, jsonify
from app.config import config
import requests
import csv

API_BASE_V2 = "https://developer.api.autodesk.com/construction/assets/v2/projects"

def fetch_all_assets_info(token: str):
    """
    Calls GET /construction/assets/v2/projects/{projectId}/assets (paginated),
    aggregates all assets, and writes them to data/assets_total.csv.
    """
    project_id = getattr(config, "project_id", None) or getattr(config, "projectId", None)
    if not project_id:
        return jsonify({"error": "Missing project_id in config."}), 500

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    limit = 1000
    all_assets: List[Dict[str, Any]] = []

    while True:
        params = {
            "includeCustomAttributes": "true",
            # Add filters if needed, e.g. "filter[deleted]": "false"
        }
        url = f"{API_BASE_V2}/{project_id}/assets"
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            # Pass-through upstream error for easier debugging
            try:
                payload = resp.json()
            except Exception:
                payload = resp.text
            return jsonify({
                "error": "Failed to fetch assets",
                "status_code": resp.status_code,
                "response": payload
            }), resp.status_code

        try:
            data = resp.json()
        except Exception:
            return jsonify({"error": "Invalid JSON from APS assets API"}), 502

        records = data.get("results")
        if not records:
            break
        # log this raw data into a json file for debugging
        with open("./data/assets_raw.json", "w", encoding="utf-8") as f:
            #with indentation for readability jsonify
            f.write(jsonify(data).get_data(as_text=True))

        all_assets.extend(records)

        if len(records) < limit:
            break
        offset += limit

    # Write CSV next to status_sets.csv
    data_dir = Path("./data")
    data_dir.mkdir(parents=True, exist_ok=True)
    csv_path = data_dir / "assets_total.csv"

    # Choose a stable subset of fields commonly returned by ACC Assets v2
    headers_row = [
        "B3F_id",
        "description",
        "companyId",
        "clientAssetId",
        "categoryId",
        "status_id",
        "ifc_global_id"
    ]

    def retrieve_GUID_ca_name() -> str:
        # find the name of the custom field that matches IFCGlobalId from root\data\custom_fields.csv
        custom_fields_path = data_dir / "custom_fields.csv"
        if not custom_fields_path.exists():
            return ""
        with custom_fields_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("display_name") == "IFCGlobalId":
                    field_id = row.get("name")
                    print("found correct name for IFCGlobalId:", field_id)
                    break
            else:
                return ""
        return field_id
        # now find the value of that custom field for the given asset


    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers_row)
        for asset in all_assets:
            row = [
                asset.get("id") or "",
                asset.get("description") or "",
                asset.get("companyId") or "",
                asset.get("clientAssetId") or "",
                asset.get("categoryId") or "",
                asset.get("statusId") or "",
                asset.get("customAttributes")[retrieve_GUID_ca_name()] or ""
            ]
            writer.writerow(row)

    msg = f"Saved assets_total.csv with {len(all_assets)} assets"
    return redirect(f"/?msg={quote_plus(msg)}")

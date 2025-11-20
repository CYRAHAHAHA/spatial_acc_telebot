from __future__ import annotations
from typing import List, Dict, Any
from pathlib import Path
from urllib.parse import quote_plus
from flask import redirect, jsonify
from app.config import config
from app.utils import get_data_dir, get_output_dir, write_csv, get_csv_path
import requests
import csv
import json

API_BASE_V2 = "https://developer.api.autodesk.com/construction/assets/v2/projects"

def fetch_all_assets_info(token: str):
    """
    Calls GET /construction/assets/v2/projects/{projectId}/assets (paginated),
    aggregates all assets, and writes them to data/assets_total.csv.
    Also generates guid_status_names.json mapping IFC Global IDs to available status names.
    """
    project_id = config.project_id

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    limit = 200  # API maximum limit
    offset = 0
    all_assets: List[Dict[str, Any]] = []

    while True:
        params = {
            "includeCustomAttributes": "true",
            "limit": limit,
            "offset": offset,
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
        
        # Save raw data to output folder for debugging
        output_dir = get_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "assets_raw.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        all_assets.extend(records)

        if len(records) < limit:
            break
        offset += limit

    # Find the IFCGlobalId custom attribute name
    ifc_global_id_name = retrieve_GUID_ca_name()

    # Prepare CSV data
    csv_headers = [
        "B3F_id",
        "description",
        "companyId",
        "clientAssetId",
        "category_id",
        "status_id",
        "ifc_global_id"
    ]

    csv_data = []
    for asset in all_assets:
        custom_attrs = asset.get("customAttributes") or {}
        ifc_global_id_value = custom_attrs.get(ifc_global_id_name, "")
        
        csv_data.append({
            "B3F_id": asset.get("id") or "",
            "description": asset.get("description") or "",
            "companyId": asset.get("companyId") or "",
            "clientAssetId": asset.get("clientAssetId") or "",
            "category_id": asset.get("categoryId") or "",
            "status_id": asset.get("statusId") or "",
            "ifc_global_id": ifc_global_id_value
        })

    # Write CSV to workspace data directory
    write_csv("assets_total.csv", csv_data, csv_headers)

    # Generate guid_status_names.json
    generate_guid_status_names_mapping(csv_data)

    msg = f"Saved assets_total.csv with {len(all_assets)} assets and generated guid_status_names.json"
    print(msg)
    return redirect(f"/?msg={quote_plus(msg)}")


def retrieve_GUID_ca_name() -> str:
    """
    Find the name of the custom field that matches IFCGlobalId from custom_fields.csv
    """
    custom_fields_path = get_csv_path("custom_fields.csv")
    if not custom_fields_path.exists():
        print("custom_fields.csv not found")
        return ""
    
    with custom_fields_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("display_name") == "IFCGlobalId":
                field_id = row.get("name")
                print("Found correct name for IFCGlobalId:", field_id)
                return field_id
    
    print("IFCGlobalId custom field not found")
    return ""


def generate_guid_status_names_mapping(csv_data: List[Dict[str, Any]]) -> None:
    """
    Generate guid_status_names.json mapping IFC Global IDs to available status names.
    
    Logic:
    1. For each asset in csv_data, get its category_id and ifc_global_id
    2. Match category_id to categories.csv to find status_set_name
    3. Match status_set_name to status_sets.csv to get all status_label values
    4. Create mapping: {ifc_global_id: [list of status_label]}
    """
    data_dir = get_data_dir()
    categories_path = data_dir / "categories.csv"
    status_sets_path = data_dir / "status_sets.csv"
    
    # Build category_id -> status_set_name mapping
    category_to_status_set: Dict[str, str] = {}
    if categories_path.exists():
        with categories_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cat_id = row.get("category_id", "").strip()
                status_set_name = row.get("status_set_name", "").strip()
                if cat_id and status_set_name:
                    category_to_status_set[cat_id] = status_set_name
    
    # Build status_set_name -> [status_label, ...] mapping
    status_set_to_labels: Dict[str, List[str]] = {}
    if status_sets_path.exists():
        with status_sets_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                status_set_name = row.get("status_set_name", "").strip()
                status_label = row.get("status_label", "").strip()
                if status_set_name and status_label:
                    if status_set_name not in status_set_to_labels:
                        status_set_to_labels[status_set_name] = []
                    if status_label not in status_set_to_labels[status_set_name]:
                        status_set_to_labels[status_set_name].append(status_label)
    
    # Build guid -> status_names mapping
    guid_status_mapping: Dict[str, List[str]] = {}
    for asset in csv_data:
        ifc_global_id = asset.get("ifc_global_id", "").strip()
        category_id = asset.get("category_id", "").strip()
        
        if not ifc_global_id:
            continue
        
        # Find status_set_name for this category
        status_set_name = category_to_status_set.get(category_id)
        if not status_set_name:
            guid_status_mapping[ifc_global_id] = []
            continue
        
        # Get all status labels for this status set
        status_labels = status_set_to_labels.get(status_set_name, [])
        guid_status_mapping[ifc_global_id] = status_labels
    
    # Write to JSON file in data directory
    output_path = data_dir / "guid_status_names.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(guid_status_mapping, f, indent=2)
    
    print(f"Generated guid_status_names.json with {len(guid_status_mapping)} entries")

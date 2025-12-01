from __future__ import annotations
from typing import Optional, Dict, Any
from pathlib import Path
import csv
import requests
from flask import jsonify
from app.config import config
from app.utils import get_csv_path, get_data_dir, get_output_dir

API_BASE_V2 = "https://developer.api.autodesk.com/construction/assets/v2/projects"

# Base dir = root folder (…\spatial_acc_telebot\root - added base path) 
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

def _lookup_status_id_by_label(label: str, status_set_id: str) -> Optional[str]:
    """
    Look up a statusId in data/status_sets.csv by matching BOTH status_label and status_set_id.
    This ensures we get the correct status from the right status set.
    Returns the first match.
    """
    csv_path = get_csv_path("status_sets.csv")
    if not csv_path.exists():
        print(f"ERROR: status_sets.csv not found at {csv_path}")
        return None
    
    needle_label = (label or "").strip().lower()
    needle_status_set_id = (status_set_id or "").strip()
    
    print(f"Looking up status: label='{needle_label}', status_set_id='{needle_status_set_id}'")
    
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_label = (row.get("status_label") or "").strip().lower()
                row_status_set_id = (row.get("status_set_id") or "").strip()
                
                if row_label == needle_label and row_status_set_id == needle_status_set_id:
                    found_status_id = row.get("status_id") or None
                    print(f"✓ Match found! status_id='{found_status_id}'")
                    return found_status_id
        
        print(f"✗ No match found for label='{needle_label}' in status_set_id='{needle_status_set_id}'")
    except Exception as e:
        print(f"ERROR reading status_sets.csv: {e}")
        return None
    
    return None

def _resolve_asset_info_from_guid(asset_guid: str) -> Optional[Dict[str, str]]:
    """
    Look up asset information from assets_total.csv using the IFC Global ID.
    Returns a dict with B3F_id and status_set_id, or None if not found.
    """
    csv_path = get_data_dir() / "assets_total.csv"
    if not csv_path.exists():
        print(f"ERROR: assets_total.csv not found at {csv_path}")
        return None
    
    needle_guid = asset_guid.strip()
    print(f"Looking up asset with GUID: '{needle_guid}'")
    
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_guid = (row.get("ifc_global_id") or "").strip()
                
                if row_guid == needle_guid:
                    asset_info = {
                        "B3F_id": row.get("B3F_id") or None,
                        "status_set_id": row.get("status_set_id") or None,
                        "category_id": row.get("category_id") or None
                    }
                    print(f"✓ Asset found! B3F_id='{asset_info['B3F_id']}', status_set_id='{asset_info['status_set_id']}'")
                    return asset_info
        
        print(f"✗ No asset found with GUID '{needle_guid}'")
    except Exception as e:
        print(f"ERROR reading assets_total.csv: {e}")
        return None
    
    return None


def update_assets(access_token: str, asset_guid: str, status_value: str):
    """
    Update a single asset's status using the APS Assets Batch PATCH v2 API.
    - Maps asset_guid -> asset info (B3F_id, status_set_id) via assets_total.csv
    - Maps (status_value + status_set_id) -> status_id via status_sets.csv
    - Sends PATCH to /construction/assets/v2/projects/{projectId}/assets:batch
    Body shape per request:
      {
        "<assetId>": { "statusId": "<statusId>" }
      }
    """
    print("\n" + "="*60)
    print("UPDATE_ASSETS called")
    print(f"  asset_guid: {asset_guid}")
    print(f"  status_value: {status_value}")
    print("="*60)
    
    project_id = config.project_id
    
    # Step 1: Get asset info (B3F_id and status_set_id) from assets_total.csv
    asset_info = _resolve_asset_info_from_guid(asset_guid)
    if not asset_info or not asset_info.get("B3F_id"):
        print("✗ FAILED: Could not find asset with GUID:", asset_guid)
        return jsonify({"error": f"Asset with GUID '{asset_guid}' not found in assets_total.csv"}), 404
    
    asset_id = asset_info["B3F_id"]
    status_set_id = asset_info["status_set_id"]
    
    print(f"\nStep 1 complete:")
    print(f"  asset_id (B3F_id): {asset_id}")
    print(f"  status_set_id: {status_set_id}")
    
    if not status_set_id:
        print("✗ FAILED: Asset has no status_set_id")
        return jsonify({"error": "Asset has no status_set_id assigned"}), 400
    
    # Step 2: Lookup status_id using BOTH status_value and status_set_id
    status_id = _lookup_status_id_by_label(status_value, status_set_id)
    if not status_id:
        print(f"✗ FAILED: Could not find status_id for '{status_value}' in status_set '{status_set_id}'")
        return jsonify({
            "error": f"Status '{status_value}' not found in status_set_id '{status_set_id}'",
            "hint": "Check status_sets.csv for available statuses in this status set"
        }), 404
    
    print(f"\nStep 2 complete:")
    print(f"  status_id: {status_id}")

    # Step 3: Call APS API to update the asset
    url = f"{API_BASE_V2}/{project_id}/assets:batch-patch"
    body = {
        asset_id: {
            "statusId": status_id
        }
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    print(f"\nStep 3: Calling APS API")
    print(f"  URL: {url}")
    print(f"  Body: {body}")
    
    try:
        resp = requests.patch(url, json=body, headers=headers, timeout=30)
        print(f"  Response status: {resp.status_code}")
        
        # Pass through upstream response for transparency
        if resp.status_code >= 200 and resp.status_code < 300:
            print("✓ SUCCESS: Asset status updated")
            try:
                return jsonify(resp.json()), resp.status_code
            except Exception:
                return resp.text, resp.status_code
        else:
            print(f"✗ FAILED: APS API returned error {resp.status_code}")
            # Include request body context to aid debugging (exclude token)
            detail = {
                "url": url,
                "status_code": resp.status_code,
                "response": None
            }
            try:
                detail["response"] = resp.json()
            except Exception:
                detail["response"] = resp.text
            detail["request_body"] = body
            return jsonify({"error": "APS update failed", **detail}), resp.status_code
    except requests.RequestException as e:
        print(f"✗ FAILED: Request exception: {e}")
        return jsonify({"error": f"Request to APS failed: {e}"}), 502
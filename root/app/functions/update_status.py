from __future__ import annotations
from typing import Optional, Dict, Any
from pathlib import Path
import csv
import requests
from flask import jsonify
from app.config import config

API_BASE_V2 = "https://developer.api.autodesk.com/construction/assets/v2/projects"

def _lookup_status_id_by_label(label: str) -> Optional[str]:
    """
    Look up a statusId in data/status_sets.csv by matching status_label (case-insensitive).
    Returns the first match.
    """
    csv_path = Path("./data/status_sets.csv")
    if not csv_path.exists():
        return None
    needle = (label or "").strip().lower()
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row.get("status_label") or "").strip().lower() == needle:
                    return row.get("status_id") or None
    except Exception:
        return None
    return None

def _resolve_asset_id_from_guid(asset_guid: str) -> Optional[str]:
    # with the asset_guid, search root\data\assets_total.csv to find the header ifc_global_id and then get the corresponding b3f_id
    csv_path = Path("./data/assets_total.csv")
    if not csv_path.exists():
        print("no assets_total.csv found")
        return None
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row.get("ifc_global_id")).strip() == (asset_guid.strip()):
                    print("Found matching asset_b3f_id:", row.get("B3F_id"))
                    return row.get("B3F_id") or None
    except Exception:
        return None
    

def update_assets(access_token: str, asset_guid: str, status_value: str):
    """
    Update a single asset's status using the APS Assets Batch PATCH v2 API.
    - Maps status_value -> statusId via status_sets.csv
    - Maps asset_guid -> assetId (placeholder: direct passthrough)
    - Sends PATCH to /construction/assets/v2/projects/{projectId}/assets:batch
    Body shape per request:
      {
        "<assetId>": { "statusId": "<statusId>" }
      }
    """
    project_id = getattr(config, "project_id", None) or getattr(config, "projectId", None)
    if not project_id:
        return jsonify({"error": "Missing project_id in config."}), 500

    status_id = _lookup_status_id_by_label(status_value)
    if not status_id:
        return jsonify({"error": f"Status '{status_value}' not found in status_sets.csv"}), 404

    asset_id = _resolve_asset_id_from_guid(asset_guid)
    if not asset_id:
        return jsonify({"error": "Invalid asset B3F_ID."}), 400

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
    print("--- Updating asset status via APS Assets Batch PATCH v2 API ---")
    print("PATCH", url, body)
    try:
        resp = requests.patch(url, json=body, headers=headers, timeout=30)
        # Pass through upstream response for transparency
        if resp.status_code >= 200 and resp.status_code < 300:
            try:
                return jsonify(resp.json()), resp.status_code
            except Exception:
                return resp.text, resp.status_code
        else:
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
        return jsonify({"error": f"Request to APS failed: {e}"}), 502
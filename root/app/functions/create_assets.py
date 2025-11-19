import requests
from typing import List, Dict, Any
from app.config import config


# ------------------------------------------------------------
# Normalize list input
# ------------------------------------------------------------
def _normalize_items(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


# ------------------------------------------------------------
# Batch Create Assets (mapped from IFC → ACC)
# ------------------------------------------------------------
def create_assets_batch(access_token: str, data: List[Dict[str, Any]]):
    items = _normalize_items(data)
    if not items:
        return ({
            "success": False,
            "error": "Empty payload for asset batch creation"
        }, 400, {"Content-Type": "application/json"})

    # ✔ Use project ID exactly as-is (no auto-prefix)
    project_id = config.project_id.strip()

    url = (
        f"https://developer.api.autodesk.com/"
        f"construction/assets/v2/projects/{project_id}/assets:batch-create"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = []

    for item in items:
        name = (item.get("name") or "").strip()
        if not name:
            continue

        global_id = (
            item.get("custom_attributes", {}).get("GlobalId")
            or item.get("globalId")
            or item.get("global_id")
            or ""
        )

        # TODO: Replace hard-coded mapping once categories / statuses mapped properly
        asset_obj = {
            "clientAssetId": name,
            "categoryId": "2",  # temporary
            "statusId": "0f25c967-714b-4281-a360-6eb86c3ad7f1",  # temporary
            "description": item.get("description") or "",
            "locationId": None,
            "customAttributes": {
                "ca1": global_id
            }
        }

        payload.append(asset_obj)

    if not payload:
        return ({
            "success": False,
            "error": "No valid assets to create"
        }, 400, {"Content-Type": "application/json"})

    resp = requests.post(url, headers=headers, json=payload, timeout=60)

    if 200 <= resp.status_code < 300:
        return ({
            "success": True,
            "created": len(payload),
            "response": resp.json()
        }, 200, {"Content-Type": "application/json"})

    return ({
        "success": False,
        "status": resp.status_code,
        "error": resp.text
    }, resp.status_code, {"Content-Type": "application/json"})
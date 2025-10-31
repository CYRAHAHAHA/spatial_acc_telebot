import csv
from pathlib import Path
from typing import List, Optional, Any, Dict

import requests
from app.config import config

API_BASE = "https://developer.api.autodesk.com/construction/assets/v1/projects"


def _to_bool(v: Any) -> bool:
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in ("true", "1", "yes", "y")


def _to_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _to_list(v: Any) -> List[str]:
    if not v:
        return []
    return [item.strip() for item in str(v).split(",") if item.strip()]


def create_custom_fields(access_token: str) -> List[Dict[str, Any]]:
    """
    Reads custom_fields_configuration.csv and creates Asset custom attributes
    via POST /projects/{projectId}/custom-attributes.
    Access token is provided by the route decorator.
    """
    if not access_token:
        print("❌ Missing access token.")
        return []

    project_id = getattr(config, "project_id", None) or getattr(config, "PROJECT_ID", None)
    if not project_id:
        print("❌ Missing project_id in config.")
        return []

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    csv_path = Path(__file__).resolve().parents[2] / "custom_fields_configuration.csv"
    if not csv_path.exists():
        print(f"❌ CSV not found at: {csv_path}")
        return []

    url = f"{API_BASE}/{project_id}/custom-attributes"
    created: List[Dict[str, Any]] = []

    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for idx, row in enumerate(reader, start=1):
            try:
                display_name = (row.get("displayName") or "").strip()
                data_type = (row.get("dataType") or "").strip()
                description = (row.get("description") or "").strip() or None
                required_on_ingress = _to_bool(row.get("requiredOnIngress"))

                if not display_name or not data_type:
                    print(f"⚠️ Row {idx}: missing displayName or dataType. Skipping.")
                    continue

                enum_values = _to_list(row.get("enumValues"))
                if data_type in ("select", "multi_select") and not enum_values:
                    print(f"⚠️ Row {idx} ({display_name}): dataType={data_type} requires enumValues. Skipping.")
                    continue

                max_len = _to_int(row.get("maxLengthOnIngress")) if data_type == "text" else None

                default_raw = (row.get("defaultValue") or "").strip()
                default_value: Any = None
                if default_raw:
                    if data_type == "boolean":
                        default_value = _to_bool(default_raw)
                    elif data_type == "multi_select":
                        default_value = _to_list(default_raw)
                    else:
                        default_value = default_raw

                payload: Dict[str, Any] = {
                    "displayName": display_name,
                    "description": description,
                    "dataType": data_type,
                    "requiredOnIngress": required_on_ingress,
                    "enumValues": enum_values if data_type in ("select", "multi_select") else None,
                    "maxLengthOnIngress": max_len,
                    "defaultValue": default_value,
                }
                payload = {k: v for k, v in payload.items() if v is not None}

                print(f"Creating custom attribute: {display_name} ...")
                print(payload)

                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                if 200 <= resp.status_code < 300:
                    data = resp.json() if resp.content else {"displayName": display_name}
                    print(f"✅ Created '{display_name}' (row {idx}).")
                    created.append(data)
                else:
                    print(f"❌ Failed to create '{display_name}' (row {idx}): {resp.status_code} {resp.text}")
            except Exception as ex:
                print(f"❌ Exception processing row {idx}: {ex}")

    return created

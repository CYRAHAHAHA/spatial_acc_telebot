import requests
from typing import List, Optional, Any, Dict
from app.config import config

API_BASE = "https://developer.api.autodesk.com/construction/assets/v1/projects"


def _normalize_items(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def _to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in ("true", "1", "yes", "y")


def _to_int(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except Exception:
        try:
            return int(str(v).strip())
        except Exception:
            return None


def _to_list(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [item.strip() for item in str(v).split(",") if item.strip()]


def create_custom_fields(access_token: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Posts custom attributes using the provided JSON payload (array or single object).
    """
    items = _normalize_items(data)
    if not items:
        print("⚠️ Empty or invalid payload for custom fields.")
        return []

    if not access_token:
        print("❌ Missing access token.")
        return []

    project_id = config.project_id

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    url = f"{API_BASE}/{project_id}/custom-attributes"
    created: List[Dict[str, Any]] = []

    for idx, row in enumerate(items, start=1):
        try:
            display_name = (row.get("displayName") or "").strip()
            data_type = (row.get("dataType") or "").strip()
            description = (row.get("description") or "").strip() or None
            required_on_ingress = _to_bool(row.get("requiredOnIngress"))

            if not display_name or not data_type:
                print(f"⚠️ Item {idx}: missing displayName or dataType. Skipping.")
                continue

            enum_values = _to_list(row.get("enumValues"))
            if data_type in ("select", "multi_select") and not enum_values:
                print(f"⚠️ Item {idx} ({display_name}): dataType={data_type} requires enumValues. Skipping.")
                continue

            max_len = _to_int(row.get("maxLengthOnIngress")) if data_type == "text" else None

            default_raw = row.get("defaultValue", None)
            default_value: Any = None
            if default_raw is not None and default_raw != "":
                if data_type == "boolean":
                    default_value = _to_bool(default_raw)
                elif data_type == "multi_select":
                    default_value = _to_list(default_raw)
                elif data_type == "numeric":
                    default_value = str(default_raw)
                else:
                    default_value = str(default_raw)

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
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if 200 <= resp.status_code < 300:
                data_resp = resp.json() if resp.content else {"displayName": display_name}
                print(f"✅ Created '{display_name}'")
                created.append(data_resp)
            else:
                print(f"❌ Failed to create '{display_name}': {resp.status_code} {resp.text}")
        except Exception as ex:
            print(f"❌ Exception processing item {idx}: {ex}")

    return created

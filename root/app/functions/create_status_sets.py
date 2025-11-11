import requests
from typing import List, Dict, Any
from app.config import config

def _normalize_items(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []

def create_status_sets(access_token: str, data: List[Dict[str, Any]]):
    """
    Posts status sets using the provided JSON payload (array or single object).
    """
    items = _normalize_items(data)
    if not items:
        print("⚠️ Empty or invalid payload for status sets.")
        return []

    project_id = config.project_id

    base_url = "https://developer.api.autodesk.com/construction/assets/v1/projects"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    created: List[Dict[str, Any]] = []

    for idx, item in enumerate(items, start=1):
        try:
            name = (item.get("name") or "").strip()
            status_set_desc = (item.get("status_set_description") or "").strip() or None
            labels = item.get("status_label") or []
            descriptions = item.get("description") or []
            colors = item.get("status_colors") or []

            if not name or not labels:
                print(f"⚠️ Row {idx}: missing name or status_label list. Skipping.")
                continue

            n = len(labels)
            if len(descriptions) < n:
                descriptions += [""] * (n - len(descriptions))
            if len(colors) < n:
                colors += [""] * (n - len(colors))

            values = []
            for lbl, desc, col in zip(labels, descriptions, colors):
                if not lbl:
                    continue
                entry = {"label": str(lbl)}
                if desc:
                    entry["description"] = str(desc)
                if col:
                    entry["color"] = str(col)
                values.append(entry)

            if not values:
                print(f"⚠️ Row {idx} ('{name}'): no valid status values. Skipping.")
                continue

            payload = {"name": name, "description": status_set_desc, "values": values}

            print(f"Creating status set: {name} ...")
            resp = requests.post(
                f"{base_url}/{project_id}/status-step-sets",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if 200 <= resp.status_code < 300:
                data_resp = resp.json() if resp.content else {"name": name}
                print(f"✅ Created '{name}'")
                created.append(data_resp)
            else:
                print(f"❌ Failed to create '{name}': {resp.status_code} {resp.text}")
        except Exception as ex:
            print(f"❌ Exception on item {idx}: {ex}")

    return created

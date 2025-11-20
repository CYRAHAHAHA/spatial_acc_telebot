import csv
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.config import config
import re

# filepath: c:\Users\User\Documents\GitHub\spatial_acc_telebot\root\app\functions\create_categories.py

BASE_URL = "https://developer.api.autodesk.com/construction/assets/v1/projects"


def _normalize_items(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def _project_root() -> Path:
    # file is at root/app/functions/..., go up 2 levels to reach root
    return Path(__file__).resolve().parents[2]


def _load_status_sets(csv_path: Path, project_id: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not csv_path.exists():
        print(f"Status sets CSV not found at {csv_path}")
        return mapping
    try:
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                # prefer rows that match project_id, but accept others too
                name = (row.get("status_set_name") or "").strip()
                sid = (row.get("status_set_id") or "").strip()
                proj = (row.get("project_id") or "").strip()
                if not name or not sid:
                    continue
                # keep first match for a given name
                if name not in mapping:
                    mapping[name] = sid
                # if a row matches current project override to ensure correct one
                if proj == project_id:
                    mapping[name] = sid
    except Exception as ex:
        print(f"Failed to read status sets CSV: {ex}")
    return mapping


def _load_custom_attributes(csv_path: Path, project_id: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not csv_path.exists():
        print(f"Custom fields CSV not found at {csv_path}")
        return mapping
    try:
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                proj = (row.get("project_id") or "").strip()
                attr_id = (row.get("custom_attribute_id") or "").strip()
                name = (row.get("name") or "").strip()
                display = (row.get("display_name") or "").strip()
                if not attr_id:
                    continue
                # map both name and display name to id (display names are used in user's JSON)
                if display and display not in mapping:
                    mapping[display] = attr_id
                if name and name not in mapping:
                    mapping[name] = attr_id
                # prefer entries matching project_id
                if proj == project_id:
                    if display:
                        mapping[display] = attr_id
                    if name:
                        mapping[name] = attr_id
    except Exception as ex:
        print(f"Failed to read custom fields CSV: {ex}")
    return mapping


def _load_categories_map(csv_path: Path, project_id: str) -> Dict[str, str]:
    """Load mapping of category_name -> category_id from categories.csv"""
    mapping: Dict[str, str] = {}
    if not csv_path.exists():
        print(f"Categories CSV not found at {csv_path}")
        return mapping
    try:
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                proj = (row.get("project_id") or "").strip()
                cat_id = (row.get("category_id") or "").strip()
                cat_name = (row.get("category_name") or "").strip()
                if not cat_id or not cat_name:
                    continue
                # keep first match for a given name
                if cat_name not in mapping:
                    mapping[cat_name] = cat_id
                # prefer entries matching project_id
                if proj == project_id:
                    mapping[cat_name] = cat_id
    except Exception as ex:
        print(f"Failed to read categories CSV: {ex}")
    return mapping


def _extract_category_id(resp_json: Any) -> Optional[str]:
    """Attempt to find a category id from the response JSON using common keys."""
    if not isinstance(resp_json, dict):
        return None
    # common keys to try
    for key in ("id", "categoryId", "category_id", "data", "result"):
        val = resp_json.get(key)
        if isinstance(val, str) and val:
            return val
        if isinstance(val, dict):
            # try nested id
            for subkey in ("id", "categoryId", "category_id"):
                subval = val.get(subkey)
                if isinstance(subval, str) and subval:
                    return subval
    # fallback: search any string value that looks like a uuid

    uuid_re = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
    def find_uuid(obj):
        if isinstance(obj, str):
            return uuid_re.search(obj).group(0) if uuid_re.search(obj) else None
        if isinstance(obj, dict):
            for v in obj.values():
                res = find_uuid(v)
                if res:
                    return res
        if isinstance(obj, list):
            for v in obj:
                res = find_uuid(v)
                if res:
                    return res
        return None

    return find_uuid(resp_json)


def create_categories(access_token: str, data: List[Dict[str, Any]]):
    """
    Creates categories, assigns status sets and attaches custom attributes.
    Handles subcategories by iterating multiple times and refreshing CSV between iterations.

    Input expected: list of objects like the provided new_categories.json
    """
    from app.functions.fetch_assets_config import fetch_assets_config
    
    items = _normalize_items(data)
    if not items:
        print("Empty or invalid payload for categories.")
        return []

    project_id = config.project_id
    project_root = _project_root()
    output_dir = project_root / "output"
    status_csv = output_dir / "status_sets.csv"
    custom_csv = output_dir / "custom_fields.csv"
    categories_csv = output_dir / "categories.csv"

    status_map = _load_status_sets(status_csv, project_id)
    custom_map = _load_custom_attributes(custom_csv, project_id)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    created: List[Dict[str, Any]] = []
    remaining_items = items.copy()
    max_iterations = 10  # Prevent infinite loops
    iteration = 0

    while remaining_items and iteration < max_iterations:
        iteration += 1
        print(f"\n=== Iteration {iteration}: Processing {len(remaining_items)} remaining categories ===")
        
        # Load current category mappings from CSV
        categories_map = _load_categories_map(categories_csv, project_id)
        
        skipped_items = []
        created_in_iteration = 0

        for idx, item in enumerate(remaining_items, start=1):
            try:
                name = (item.get("name") or "").strip()
                description = (item.get("description") or "").strip() or None
                parent_id = item.get("category_parent_id")
                parent_name = (item.get("category_parent_name") or "").strip()
                status_set_name = (item.get("status_set_name") or "").strip()
                custom_fields = item.get("custom_fields") or []

                if not name:
                    print(f"Item {idx}: missing 'name'. Skipping permanently.")
                    continue

                # Resolve parent_id if not provided
                if parent_id is None or parent_id == "":
                    if parent_name == "ROOT":
                        parent_id = "1"
                    elif parent_name in categories_map:
                        parent_id = categories_map[parent_name]
                        print(f"Resolved parent '{parent_name}' to ID {parent_id} for category '{name}'")
                    else:
                        print(f"Item {idx} ('{name}'): parent '{parent_name}' not found in categories CSV. Skipping for now.")
                        skipped_items.append(item)
                        continue
                else:
                    # Cast to string
                    parent_id = str(parent_id)

                if not parent_id:
                    print(f"Item {idx} ('{name}'): no valid parent_id. Skipping for now.")
                    skipped_items.append(item)
                    continue

                payload = {"name": name, "parentId": parent_id}
                if description:
                    payload["description"] = description

                print(f"Creating category: {name} (parent_id={parent_id}) ...")
                resp = requests.post(
                    f"{BASE_URL}/{project_id}/categories",
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
                if not (200 <= resp.status_code < 300):
                    print(f"Failed to create category '{name}': {resp.status_code} {resp.text}")
                    continue

                resp_json = resp.json() if resp.content else {}
                category_id = _extract_category_id(resp_json)
                if not category_id:
                    print(f"Created category '{name}' but could not extract category ID from response.")
                    created.append({"name": name, "category_id": None, "status_assigned": False, "customs_attached": []})
                    created_in_iteration += 1
                    continue

                print(f"[SUCCESS] Created category '{name}' (id={category_id})")

                status_assigned = False
                # Only assign status sets to root-level categories (parent_id = "1")
                if status_set_name and parent_id == "1":
                    status_id = status_map.get(status_set_name)
                    if not status_id:
                        print(f"  '{name}': status set '{status_set_name}' not found in CSV. Skipping status assignment.")
                    else:
                        put_payload = {"projectId": project_id, "categoryId": category_id, "statusStepSetId": status_id}
                        print(f"  Assigning status set '{status_set_name}' to '{name}' ...")
                        resp2 = requests.put(
                            f"{BASE_URL}/{project_id}/categories/{category_id}/status-step-set/{status_id}",
                            headers=headers,
                            json=put_payload,
                            timeout=30,
                        )
                        if 200 <= resp2.status_code < 300:
                            print(f"  [SUCCESS] Assigned status set '{status_set_name}'")
                            status_assigned = True
                        else:
                            print(f"  [FAILED] Failed to assign status set: {resp2.status_code} {resp2.text}")
                elif status_set_name and parent_id != "1":
                    print(f"  Skipping status set assignment for subcategory '{name}' (inherits from parent)")
                    status_assigned = True  # Mark as "assigned" since it inherits from parent

                customs_attached: List[Dict[str, Any]] = []
                # Only assign custom fields to root-level categories (parent_id = "1")
                if parent_id == "1":
                    for cf in custom_fields:
                        cf_name = (cf or "").strip()
                        if not cf_name:
                            continue
                        cf_id = custom_map.get(cf_name)
                        if not cf_id:
                            print(f"  '{name}': custom field '{cf_name}' not found in CSV. Skipping.")
                            customs_attached.append({"name": cf_name, "custom_attribute_id": None, "attached": False})
                            continue
                        put_payload = {"projectId": project_id, "categoryId": category_id, "customAttributeId": cf_id}
                        resp3 = requests.put(
                            f"{BASE_URL}/{project_id}/categories/{category_id}/custom-attributes/{cf_id}",
                            headers=headers,
                            json=put_payload,
                            timeout=30,
                        )
                        if 200 <= resp3.status_code < 300:
                            customs_attached.append({"name": cf_name, "custom_attribute_id": cf_id, "attached": True})
                        else:
                            print(f"  [FAILED] Failed to attach custom field '{cf_name}': {resp3.status_code} {resp3.text}")
                            customs_attached.append({"name": cf_name, "custom_attribute_id": cf_id, "attached": False})
                else:
                    # Subcategory - inherits custom fields from parent
                    print(f"  Skipping custom field assignment for subcategory '{name}' (inherits from parent)")
                    for cf in custom_fields:
                        cf_name = (cf or "").strip()
                        if cf_name:
                            customs_attached.append({"name": cf_name, "custom_attribute_id": None, "attached": True, "inherited": True})

                created.append({
                    "name": name,
                    "category_id": category_id,
                    "status_assigned": status_assigned,
                    "customs_attached": customs_attached,
                })
                created_in_iteration += 1

            except Exception as ex:
                print(f"Exception on item {idx} ('{name}'): {ex}")
                skipped_items.append(item)

        # Update remaining items for next iteration
        remaining_items = skipped_items
        
        if created_in_iteration > 0 and remaining_items:
            # Refresh the categories CSV for next iteration
            print(f"\n>>> Refreshing categories CSV for next iteration (created {created_in_iteration} categories)...")
            try:
                fetch_assets_config(access_token)
                print(">>> Categories CSV refreshed successfully")
            except Exception as ex:
                print(f">>> Failed to refresh categories CSV: {ex}")
        elif created_in_iteration == 0 and remaining_items:
            print(f"\n[WARNING] No categories created in iteration {iteration}, but {len(remaining_items)} items remain. Stopping to prevent infinite loop.")
            print("Remaining items:")
            for item in remaining_items:
                print(f"  - {item.get('name')} (parent: {item.get('category_parent_name')})")
            break

    if remaining_items:
        print(f"\n[WARNING] {len(remaining_items)} categories could not be created after {iteration} iterations.")
        for item in remaining_items:
            print(f"  - {item.get('name')} (parent: {item.get('category_parent_name')})")
    
    print(f"\n[SUCCESS] Successfully created {len(created)} categories")
    return created
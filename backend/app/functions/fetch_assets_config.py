import requests, json, urllib.parse
from flask import request, redirect, session
from app.config import config
from pathlib import Path

def fetch_assets_config():
    access_token = request.args.get("access_token")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    project_id = config.project_id
    base_url = "https://developer.api.autodesk.com/construction/assets/v1/projects"

    try:
        # === 1️⃣ Fetch custom attributes ===
        ca_resp = requests.get(f"{base_url}/{project_id}/custom-attributes", headers=headers)
        custom_attributes = ca_resp.json().get("results", []) if ca_resp.status_code == 200 else []

        # === 2️⃣ Fetch status-step sets ===
        ss_resp = requests.get(f"{base_url}/{project_id}/status-step-sets", headers=headers)
        status_sets_raw = ss_resp.json().get("results", []) if ss_resp.status_code == 200 else []

        status_sets = []
        status_sets_dict = {}
        for ss in status_sets_raw:
            ss_obj = {
                "id": ss.get("id"),
                "name": ss.get("name"),
                "description": ss.get("description", ""),
                "statuses": ss.get("values", [])
            }
            status_sets.append(ss_obj)
            status_sets_dict[ss.get("id")] = ss_obj

        # === 3️⃣ Fetch raw categories ===
        cat_resp = requests.get(f"{base_url}/{project_id}/categories", headers=headers)
        categories_raw = cat_resp.json().get("results", []) if cat_resp.status_code == 200 else []

        # === 4️⃣ Fetch category → status set mappings using batch API ===
        category_ids = [cat["id"] for cat in categories_raw]
        batch_url = f"{base_url}/{project_id}/category-status-step-sets/status-step-sets:batch-get"
        batch_payload = {"ids": category_ids}
        print("Fetching category to status set mappings via batch API...", batch_payload)
        batch_resp = requests.post(batch_url, headers=headers, json=batch_payload)
        category_status_raw = batch_resp.json().get("results", []) if batch_resp.status_code == 200 else []

        # Build a mapping: categoryId -> statusStepSetId
        category_to_statusSet = {c["categoryId"]: c.get("statusStepSetId") for c in category_status_raw}

        # === 5️⃣ Map categories with their status sets and custom attributes ===
        categories_with_status = []
        for cat in categories_raw:
            status_set_id = category_to_statusSet.get(cat["id"])
            status_set = status_sets_dict.get(status_set_id)

            # Determine display name for root/system categories
            status_set_name = status_set.get("name") if status_set else "No Status Set (system)"
            statuses = status_set.get("statuses", []) if status_set else []

            category_custom_attributes = [
                {
                    "displayName": ca.get("displayName"),
                    "description": ca.get("description"),
                    "dataType": ca.get("dataType"),
                    "enumValues": ca.get("enumValues", []),
                }
                for ca in custom_attributes
            ]

            categories_with_status.append({
                "categoryName": cat.get("name"),
                "categoryId": cat.get("id"),
                "parentId": cat.get("parentId"),
                "statusSetId": status_set_id,
                "statusSetName": status_set_name,
                "statuses": statuses,
                "customAttributes": category_custom_attributes,
                "children": cat.get("subcategoryIds", [])
            })

        # === 6️⃣ Aggregate data ===
        aggregated_data = {
            "customAttributes": [{ca.get("displayName"): ca.get("description", "")} for ca in custom_attributes],
            "statusSets": status_sets,
            "categories": categories_with_status
        }

        # Store in session
        session["aggregated_data"] = aggregated_data

        print(aggregated_data)

        # === 7️⃣ Save all raw and mapped data to log.json ===
        log_path = Path("log.json")
        with log_path.open("w", encoding="utf-8") as f:
            json.dump({
                "customAttributesRaw": custom_attributes,
                "statusSetsRaw": status_sets_raw,
                "categoriesRaw": categories_raw,
                "categoryStatusMappingRaw": category_status_raw,
                "categoriesWithStatus": categories_with_status
            }, f, indent=2)

        print("\n=== Saved log.json with all debug info ===")
        print(log_path.resolve())

        # Redirect message
        msg = urllib.parse.quote_plus(
            f"Fetched {len(custom_attributes)} attributes, "
            f"{len(status_sets)} status sets, "
            f"{len(categories_raw)} categories"
        )
        return redirect(f"/?msg={msg}")

    except Exception as e:
        msg = urllib.parse.quote_plus(f"Error fetching assets info: {e}")
        return redirect(f"/?msg={msg}")

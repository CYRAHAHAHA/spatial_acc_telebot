import requests, json, urllib.parse
from flask import redirect, session
from app.config import config
from pathlib import Path

def fetch_assets_config(access_token: str):
    """
    Refactored to accept token from route decorator.
    Use 'access_token' instead of reading from session/request.
    """
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
            "customAttributes": [{ca.get("displayName"): ca.get("description", ""), "id": ca.get("id")} for ca in custom_attributes],
            "statusSets": status_sets,
            "categories": categories_with_status
        }

        # Store in session
        session["aggregated_data"] = aggregated_data

        # === 7️⃣ Save all raw and mapped data to log.json ===
        log_path = Path("./data/log.json")
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

        # === 8️⃣ Save aggregated data to log_aggregated.json ===
        log_aggregated_path = Path("./data/log_aggregated.json")
        with log_aggregated_path.open("w", encoding="utf-8") as f:
            json.dump(aggregated_data, f, indent=2)
        print("\n=== Saved log_aggregated.json with aggregated data ===")
        # Redirect message
        msg = urllib.parse.quote_plus(
            f"Fetched {len(custom_attributes)} attributes, "
            f"{len(status_sets)} status sets, "
            f"{len(categories_raw)} categories"
        )

        # === 8️⃣ Save useful data in database table style to 3 separate status_sets.csv, custom_fields.csv and categories.csv ===
        # Status Sets CSV, retrieve from status_sets_raw the project_id, status set id, and status set name, all status values within each status set. Retrieve the id, label, and description.
        status_sets_csv = []
        for ss in status_sets:
            for status in ss.get("statuses", []):
                status_sets_csv.append({
                    "project_id": ss.get("projectId"),
                    "status_set_id": ss.get("id"),
                    "status_set_name": ss.get("name"),
                    "status_id": status.get("id"),
                    "status_label": status.get("label"),
                    "status_description": status.get("description", "")
                })
        status_sets_csv_path = Path("./data/status_sets.csv")
        with status_sets_csv_path.open("w", encoding="utf-8") as f:
                # Write CSV header
                f.write("project_id,status_set_id,status_set_name,status_id,status_label,status_description\n")
                for row in status_sets_csv:
                    f.write(f"{row['project_id']},{row['status_set_id']},{row['status_set_name']},{row['status_id']},{row['status_label']},{row['status_description']}\n")
        print("\n=== Saved status_sets.csv with status sets data ===")

        # Custom Fields CSV, retrieve from custom_attributes the project_id, custom attribute id, display
        custom_fields_csv = []
        for ca in custom_attributes:
            custom_fields_csv.append({
                "project_id": ca.get("projectId"),
                "custom_attribute_id": ca.get("id"),
                "display_name": ca.get("displayName"),
                "description": ca.get("description", ""),
                "data_type": ca.get("dataType"),
                "required": ca.get("requiredOnIngress", False),
                "values": ";".join(ca.get("enumValues", [])) if ca.get("dataType") == "enum" else "",
                #corresponding displayName and id for array of values
                "values_and_ids": ";".join([f"{value.get('displayName')}({value.get('id')})" for value in ca.get("values", [])]) if ca.get("values") else ""
            })
        custom_fields_csv_path = Path("./data/custom_fields.csv")
        with custom_fields_csv_path.open("w", encoding="utf-8") as f:
                # Write CSV header
                f.write("project_id,custom_attribute_id,display_name,description,data_type,required,values,values_and_ids\n")
                for row in custom_fields_csv:
                    f.write(f"{row['project_id']},{row['custom_attribute_id']},{row['display_name']},{row['description']},{row['data_type']},{row['required']},{row['values']},{row['values_and_ids']}\n")
        print("\n=== Saved custom_fields.csv with custom attributes data ===")

        return redirect(f"/?msg={msg}")

    except Exception as e:
        msg = urllib.parse.quote_plus(f"Error fetching assets info: {e}")
        return redirect(f"/?msg={msg}")

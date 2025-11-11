import requests, json, urllib.parse
from flask import redirect, session
from app.config import config
from pathlib import Path
import csv

def fetch_assets_config(access_token: str):

    project_id = config.project_id
    base_url = "https://developer.api.autodesk.com/construction/assets/v1/projects"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

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
                "projectId": ss.get("projectId"),
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
        print("HIII CHECK ME OUT")
        params = {
            "includeInherited": "true"   # query string ?includeInherited=true
        }
        print("Fetching category to status set mappings via batch API...", batch_payload)
        batch_resp = requests.post(batch_url, headers=headers, json=batch_payload, params=params)
        category_status_raw = batch_resp.json().get("results", []) if batch_resp.status_code == 200 else []
        print("GOTCHA")
        print(category_status_raw)
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
        log_path = Path("./output/log.json")
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
        log_aggregated_path = Path("./output/log_aggregated.json")
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
        # Status Sets CSV
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
        status_sets_csv_path = Path("./output/status_sets.csv")
        with status_sets_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=",", lineterminator="\n")
            writer.writerow(["project_id","status_set_id","status_set_name","status_id","status_label","status_description"])
            for row in status_sets_csv:
                writer.writerow([
                    row.get("project_id") or "",
                    row.get("status_set_id") or "",
                    row.get("status_set_name") or "",
                    row.get("status_id") or "",
                    row.get("status_label") or "",
                    row.get("status_description") or "",
                ])
        print("\n=== Saved status_sets.csv with status sets data ===")

        # Custom Fields CSV
        custom_fields_csv = []
        for ca in custom_attributes:
            # keep semicolons inside the cell to separate multiple values, CSV delimiter is still a comma
            values_raw = ""
            if ca.get("dataType") == "enum":
                ev = ca.get("enumValues") or []
                # enumValues can be strings or objects; stringify safely
                values_raw = ";".join([v if isinstance(v, str) else str(v) for v in ev])

            values_and_ids_raw = ""
            if ca.get("values"):
                values_and_ids_raw = ";".join([
                    f"{(value.get('displayName') or '').strip()}({(value.get('id') or '').strip()})"
                    for value in (ca.get("values") or [])
                ])

            custom_fields_csv.append({
                "project_id": ca.get("projectId"),
                "custom_attribute_id": ca.get("id"),
                "name": ca.get("name"),
                "display_name": ca.get("displayName"),
                "description": ca.get("description", ""),
                "data_type": ca.get("dataType"),
                "required": ca.get("requiredOnIngress", False),
                "values": values_raw,
                "values_and_ids": values_and_ids_raw
            })

        custom_fields_csv_path = Path("./output/custom_fields.csv")
        with custom_fields_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=",", lineterminator="\n")
            writer.writerow(["project_id","custom_attribute_id","name","display_name","description","data_type","required","values","values_and_ids"])
            for row in custom_fields_csv:
                writer.writerow([
                    row.get("project_id") or "",
                    row.get("custom_attribute_id") or "",
                    row.get("name") or "",
                    row.get("display_name") or "",
                    row.get("description") or "",
                    row.get("data_type") or "",
                    "True" if row.get("required") else "False",
                    row.get("values") or "",
                    row.get("values_and_ids") or "",
                ])
        print("\n=== Saved custom_fields.csv with custom attributes data ===")

        # Categories CSV
        categories_csv = []
        for cat in categories_with_status:
            categories_csv.append({
                "project_id": project_id,
                "category_id": cat.get("categoryId"),
                "category_name": cat.get("categoryName"),
                "parent_id": cat.get("parentId"),
                "status_set_id": cat.get("statusSetId"),
                "status_set_name": cat.get("statusSetName"),
                "custom_attributes": ";".join([ca.get("displayName") for ca in cat.get("customAttributes", []) if ca.get("displayName")])
            })
        categories_csv_path = Path("./output/categories.csv")
        with categories_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=",", lineterminator="\n")
            writer.writerow(["project_id","category_id","category_name","parent_id","status_set_id","status_set_name","custom_attributes"])
            for row in categories_csv:
                writer.writerow([
                    row.get("project_id") or "",
                    row.get("category_id") or "",
                    row.get("category_name") or "",
                    row.get("parent_id") or "",
                    row.get("status_set_id") or "",
                    row.get("status_set_name") or "",
                    row.get("custom_attributes") or "",
                ])

        print(msg)
        return redirect(f"/?msg={msg}")

    except Exception as e:
        msg = urllib.parse.quote_plus(f"Error fetching assets info: {e}")
        return redirect(f"/?msg={msg}")

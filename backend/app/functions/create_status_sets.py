import csv
import requests
from pathlib import Path
from app.config import config
from flask import request

def create_status_sets():
    access_token = request.args.get("access_token")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    """
    Reads the CSV file and creates status sets on Autodesk ACC.
    """

    project_id = config.project_id
    csv_path = Path(__file__).resolve().parents[2] / "status_sets_configuration.csv"
    base_url = "https://developer.api.autodesk.com/construction/assets/v1/projects"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    created_sets = []

    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            print(row)
            name = row.get("name")
            status_set_desc = row.get("status_set_description", "")
            statuses = [s.strip() for s in row["status_label"].split(",")]
            descriptions = [d.strip() for d in row["description"].split(",")]
            colors = [c.strip() for c in row["status_colors"].split(",")]

            if len(statuses) != len(colors):
                print(f"⚠️ Mismatch in counts for '{name}'. Skipping.")
                continue

            values = [{"label": s, "description": d, "color": c} for s, d, c in zip(statuses, descriptions, colors)]
            print("values payload:", values)

            payload = {
                "name": name,
                "description": status_set_desc,
                "values": values
            }

            print(f"Creating status set: {name} ...")
            print(payload)
            resp = requests.post(
                f"{base_url}/{project_id}/status-step-sets",
                headers=headers,
                json=payload
            )

            if resp.status_code == 201:
                data = resp.json()
                print(f"✅ Created '{name}' with ID: {data['id']}")
                created_sets.append(data)
            else:
                print(f"❌ Failed to create '{name}': {resp.text}")

    return created_sets

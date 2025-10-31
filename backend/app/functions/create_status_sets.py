import csv
import requests
from pathlib import Path
from app.config import config

def create_status_sets(access_token: str):
    """
    Reads status_sets_configuration.csv and POSTs /projects/{projectId}/status-step-sets
    using the provided access_token.
    """
    project_id = getattr(config, "project_id", None) or getattr(config, "PROJECT_ID", None)
    if not project_id:
        print("❌ Missing project_id in config.")
        return []

    base_url = "https://developer.api.autodesk.com/construction/assets/v1/projects"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    csv_path = Path(__file__).resolve().parents[2] / "status_sets_configuration.csv"
    if not csv_path.exists():
        print(f"❌ CSV not found at: {csv_path}")
        return []

    created_sets = []

    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = (row.get("name") or "").strip()
            status_set_desc = (row.get("status_set_description") or "").strip()
            labels = [s.strip() for s in (row.get("status_label") or "").split(",") if s.strip()]
            descriptions = [d.strip() for d in (row.get("description") or "").split(",")]  # allow empty desc
            colors = [c.strip() for c in (row.get("status_colors") or "").split(",")]

            if not name or not labels:
                print(f"⚠️ Missing name or status labels. Skipping row: {row}")
                continue

            # Normalize lists to same length (pad missing desc/colors with "")
            if len(descriptions) < len(labels):
                descriptions += [""] * (len(labels) - len(descriptions))
            if len(colors) < len(labels):
                colors += [""] * (len(labels) - len(colors))
            if len(descriptions) != len(labels) or len(colors) != len(labels):
                print(f"⚠️ Mismatch in counts for '{name}'. Skipping.")
                continue

            values = [
                {"label": s, **({"description": d} if d else {}), **({"color": c} if c else {})}
                for s, d, c in zip(labels, descriptions, colors)
            ]

            payload = {
                "name": name,
                "description": status_set_desc,
                "values": values,
            }

            print(f"Creating status set: {name} ...")
            resp = requests.post(
                f"{base_url}/{project_id}/status-step-sets",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if 200 <= resp.status_code < 300:
                data = resp.json() if resp.content else {"name": name}
                print(f"✅ Created '{name}' with response: {data}")
                created_sets.append(data)
            else:
                print(f"❌ Failed to create '{name}': {resp.status_code} {resp.text}")

    return created_sets

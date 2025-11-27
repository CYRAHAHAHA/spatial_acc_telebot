# root/app/functions/create_assets_ai.py

from pathlib import Path
import json
import csv
import time
import requests
from openai import OpenAI
from app.config import config

client = OpenAI(api_key=config.openai_api_key)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"
CATEGORY_CSV = OUTPUT_DIR / "category_status_default.csv"
MAPPED_ASSETS_FILE = OUTPUT_DIR / "mapped_assets.json"

ASSETS_PER_BATCH = 15


# Load JSON File
def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Load CSV Map: category_name → IDs + custom_attributes
def load_categories_from_csv():
    categories = {}
    with open(CATEGORY_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items()}
            name = cleaned.get("category_name")
            if not name:
                continue
            categories[name.lower()] = {
                "categoryId": cleaned.get("category_id"),
                "statusId": cleaned.get("default_status_id"),
                "ca_key": cleaned.get("ifcglobalid_cat_name") or "ca1",
            }
    return categories


# AI Classification
def ai_classify_asset(asset, valid_categories, retries=3):
    safe_categories = [c for c in valid_categories if c != "root"]

    prompt = f"""
You are an expert BIM classification model.

Asset Name: {asset.get('name')}
IFC Type: {asset.get('category')}

Allowed ACC Categories:
{safe_categories}

Respond only with one category name from the list EXACTLY.
"""

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            result = response.choices[0].message.content.strip().lower()
            if result in safe_categories:
                return result

            print(f"⚠ Invalid category: '{result}' — retrying...")

        except Exception as e:
            print(f"⚠ OpenAI Error: {e}")

        time.sleep(1.2)

    fallback = safe_categories[0]
    print(f"❌ Final fallback for {asset.get('name')} → {fallback}")
    return fallback


# Build Payload for ACC Upload
def build_ai_payload():
    categories_map = load_categories_from_csv()
    assets = load_json(MAPPED_ASSETS_FILE)

    valid_names = list(categories_map.keys())
    payload = []

    print(f"\n🚀 Classifying {len(assets)} assets...\n")

    for i, asset in enumerate(assets, start=1):
        cat_name = ai_classify_asset(asset, valid_names)
        cat_info = categories_map.get(cat_name)

        if not cat_info:
            # Catch for unexpected values
            print(f"⚠ Missing cat info for '{cat_name}', fallback root")
            cat_info = categories_map["root"]

        payload.append({
            "clientAssetId": asset.get("name"),
            "categoryId": cat_info["categoryId"],
            "statusId": cat_info["statusId"],
            "description": asset.get("description") or "",
            "locationId": None,
            "customAttributes": {
                cat_info["ca_key"]: asset.get("custom_attributes", {}).get("GlobalId")
            }
        })

        print(f"{i}. {asset.get('name')} → {cat_name}")

        time.sleep(0.25)

    print("\n🎯 Finished AI Mapping!\n")
    return payload


# Upload to Autodesk ACC
def upload_batches(payload, token):
    project_id = config.project_id.strip()
    url = (
        "https://developer.api.autodesk.com/"
        f"construction/assets/v2/projects/{project_id}/assets:batch-create"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    results = []
    print("\n☁️ Uploading to ACC...\n")

    for i in range(0, len(payload), ASSETS_PER_BATCH):
        batch = payload[i:i + ASSETS_PER_BATCH]
        print(f"📤 Batch {i // ASSETS_PER_BATCH + 1} → {len(batch)} assets")

        resp = requests.post(url, headers=headers, json=batch)
        results.append(resp.json())
        print(f"  ↳ ACC Response: {resp.status_code}")

        time.sleep(2)

    result_path = OUTPUT_DIR / "acc_upload_results.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results, str(result_path)


def run_create_assets(token: str):
    payload = build_ai_payload()
    results, path = upload_batches(payload, token)
    return {
        "assets_uploaded": len(payload),
        "results_file": path,
        "acc_response": results
    }
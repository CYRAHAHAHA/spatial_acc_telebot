# root/app/functions/create_assets_ai.py

from pathlib import Path
import json
import csv
import time
import requests
from google import genai
from app.config import config


# 🧠 Gemini AI Setup (secured through .env config)
client = genai.Client(api_key=config.gemini_key)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"
CATEGORY_CSV = OUTPUT_DIR / "category_status_default.csv"
MAPPED_ASSETS_FILE = OUTPUT_DIR / "mapped_assets.json"

ASSETS_PER_BATCH = 15   # ACC API batching
ASSETS_LIMIT = 10       # AI API rate limit (configure based on quota)


# ------------------------------------------------------------
# Helper: Load JSON File
# ------------------------------------------------------------
def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------
# Load ACC CSV: category_name, category_id, default_status_id, ifcglobalid_cat_name
# ------------------------------------------------------------
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
                "ca_key": cleaned.get("ifcglobalid_cat_name") or "ca1"
            }
    return categories


# ------------------------------------------------------------
# 🔍 AI Classifier — prevents ROOT category "1"
# ------------------------------------------------------------
def ai_classify_asset(asset, valid_categories, retries=3):
    safe_categories = [c for c in valid_categories if c != "root"]  # remove root from candidates

    prompt = f"""
Asset:
Name: {asset.get('name')}
IFC Class: {asset.get('category')}

Allowed ACC Categories:
{safe_categories}

Return ONLY the exact category name from the list above.
"""

    for attempt in range(1, retries + 1):
        try:
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            result = res.text.strip().lower()

            if result in safe_categories:
                return result

            print(f"⚠ Attempt {attempt}: AI returned invalid category '{result}'. Retrying...")

        except Exception as e:
            print(f"⚠ Gemini API error attempt {attempt}: {e}")

        time.sleep(1.5)

    # 🚨 FINAL FALLBACK: First valid category (not root)
    fallback = safe_categories[0]
    print(f"❌ AI failed after {retries} attempts — fallback to '{fallback}'")
    return fallback


# ------------------------------------------------------------
# Build AI Mapped Payload for ACC
# ------------------------------------------------------------
def build_ai_payload():
    categories_map = load_categories_from_csv()
    assets = load_json(MAPPED_ASSETS_FILE)[:ASSETS_LIMIT]  # limit for testing

    valid_names = list(categories_map.keys())
    payload = []

    print(f"\n🚀 Classifying & Mapping {len(assets)} assets using Gemini AI...\n")

    for i, asset in enumerate(assets, start=1):
        cat_name = ai_classify_asset(asset, valid_names)
        cat_info = categories_map.get(cat_name)

        if not cat_info:
            # fallback safety (should rarely trigger)
            fallback_key = [k for k in valid_names if k != "root"][0]
            print(f"⚠ Fallback: {asset['name']} assigned to {fallback_key}")
            cat_info = categories_map[fallback_key]

        payload.append({
            "clientAssetId": asset["name"],
            "categoryId": cat_info["categoryId"],
            "statusId": cat_info["statusId"],  # default mapped status!
            "description": asset.get("description") or "",
            "locationId": None,
            "customAttributes": {
                cat_info["ca_key"]: asset.get("custom_attributes", {}).get("GlobalId")
            }
        })

        print(f"{i}. {asset['name']} → {cat_name.upper()} "
              f"(catId={cat_info['categoryId']} status={cat_info['statusId']})")

    print("\n🎉 Payload Build Complete!")
    return payload


# ------------------------------------------------------------
# 🚀 Upload to Autodesk ACC (in batches)
# ------------------------------------------------------------
def upload_batches(payload, token):
    project_id = config.project_id.strip()

    url = (
        f"https://developer.api.autodesk.com/"
        f"construction/assets/v2/projects/{project_id}/assets:batch-create"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    results = []

    print("\n📡 Uploading asset batches to ACC...\n")
    for i in range(0, len(payload), ASSETS_PER_BATCH):
        batch = payload[i:i + ASSETS_PER_BATCH]
        print(f"📤 Batch {i // ASSETS_PER_BATCH + 1} → {len(batch)} assets")

        resp = requests.post(url, headers=headers, json=batch)

        try:
            results.append(resp.json())
        except:
            results.append({"error": resp.text})

        print(f"   ↳ Status: {resp.status_code}\n")
        time.sleep(2)

    result_path = OUTPUT_DIR / "acc_upload_results.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results, str(result_path)


# ------------------------------------------------------------
# Main Public Function Called by Route
# ------------------------------------------------------------
def run_create_assets(token: str):
    payload = build_ai_payload()
    results, path = upload_batches(payload, token)
    return {
        "assets_uploaded": len(payload),
        "results_file": path,
        "acc_response": results
    }
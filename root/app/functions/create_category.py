import json
import requests
from typing import List
from app.config import config
from pathlib import Path
from app.functions.authentication import AutodeskAuth

# ------------------------------------------------------------
# AUTH
# ------------------------------------------------------------
auth = AutodeskAuth(
    client_id=config.client_id,
    client_secret=config.client_secret,
    redirect_uri=config.redirect_uri,
    scopes=config.scopes
)


def get_token():
    token = auth.get_access_token()
    if not token:
        raise Exception("❌ No valid token. Please login via /authorize first.")
    return token


# ------------------------------------------------------------
# Create category 
# ------------------------------------------------------------
def create_category(token: str, name: str):
    project_id = config.project_id.strip()
    if not project_id.startswith("b."):
        project_id = f"b.{project_id}"

    url = f"https://developer.api.autodesk.com/construction/assets/v1/projects/{project_id}/categories"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "name": name,
        "parentId": "1"  # ACC requires this param
    }

    print(f"📦 Creating category: {name}")
    response = requests.post(url, headers=headers, json=payload)

    if 200 <= response.status_code < 300:
        data = response.json()
        print(f"   ✅ Created '{name}' → id: {data.get('id')}")
        return data

    print(f"   ❌ Failed for '{name}' [{response.status_code}]: {response.text}")
    return None


# ------------------------------------------------------------
# Load mapped IFC categories from output
# ------------------------------------------------------------
def extract_unique_categories(mapped_file: str) -> List[str]:
    with open(mapped_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    categories = sorted({obj.get("category") for obj in data if obj.get("category")})

    print(f"\n📌 Found {len(categories)} unique categories:")
    for c in categories:
        print(f"   • {c}")

    return categories

# ------------------------------------------------------------
# Main Workflow - Load mapped IFC categories + create them in ACC
# ------------------------------------------------------------

def create_categories_from_mapped(token: str):
    print("🚀 Creating categories from mapped IFC assets")

    # 1️⃣ Locate mapped assets file
    mapped_path = Path(__file__).resolve().parents[1] / "output" / "mapped_assets.json"

    if not mapped_path.exists():
        return {
            "success": False,
            "error": "mapped_assets.json not found in /output folder"
        }, 400, {"Content-Type": "application/json"}

    # 2️⃣ Extract unique IFC categories
    categories = extract_unique_categories(str(mapped_path))

    if not categories:
        return {
            "success": False,
            "error": "No categories found in mapped assets file"
        }, 400, {"Content-Type": "application/json"}

    # 3️⃣ Create categories via ACC API
    token = get_token()
    created = []
    failed = []

    for cat in categories:
        result = create_category(token, cat)
        if result:
            created.append(cat)
        else:
            failed.append(cat)

    print(f"\n🎉 DONE — Created {len(created)}/{len(categories)} ACC categories")

    # 4️⃣ Response for UI
    return ({
        "success": True,
        "total": len(categories),
        "created": len(created),
        "failed": failed
    }, 200, {"Content-Type": "application/json"})
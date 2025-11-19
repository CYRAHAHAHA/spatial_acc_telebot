import json
import requests
import base64
import os
from pathlib import Path

from app.functions.authentication import AutodeskAuth
from app.config import config


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
        raise Exception("❌ No valid token. Please login via /login first.")
    return token


# ------------------------------------------------------------
# Decode externalId
# ------------------------------------------------------------
def decode_external_id(b64_id):
    try:
        padding = "=" * (-len(b64_id) % 4)
        return base64.b64decode(b64_id + padding).decode("utf-8")
    except:
        return None


# ------------------------------------------------------------
# LIST HUBS
# ------------------------------------------------------------
def list_hubs(token):
    url = "https://developer.api.autodesk.com/project/v1/hubs"
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(url, headers=headers)
    r.raise_for_status()
    hubs = r.json()["data"]

    print(f"\n🏢 Found {len(hubs)} hub(s):")
    for h in hubs:
        print(f"   - {h['attributes']['name']} → {h['id']}")

    return hubs


# ------------------------------------------------------------
# GET ROOT FOLDER
# ------------------------------------------------------------
def get_root_folder(hub_id, project_id, token):
    url = f"https://developer.api.autodesk.com/project/v1/hubs/{hub_id}/projects/{project_id}/topFolders"
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()["data"]

    pf = next((f for f in data if f["attributes"]["name"].lower() == "project files"), None)
    folder_id = pf["id"] if pf else data[0]["id"]

    print(f"\n📦 Root Folder ID → {folder_id}")
    return folder_id


# ------------------------------------------------------------
# LIST IFC FILES
# ------------------------------------------------------------
def list_ifc_files(project_id, folder_id, token):
    headers = {"Authorization": f"Bearer {token}"}

    def get_contents(fid):
        url = f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/folders/{fid}/contents"
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.json().get("data", [])

    found = []
    stack = [folder_id]

    while stack:
        fid = stack.pop()
        for item in get_contents(fid):
            name = item.get("attributes", {}).get("displayName", "")
            if item["type"] == "folders":
                stack.append(item["id"])
            elif name.lower().endswith(".ifc"):
                found.append(item)

    print(f"\n🔍 Found {len(found)} IFC file(s).")
    return found


# ------------------------------------------------------------
# GET LATEST VERSION
# ------------------------------------------------------------
def get_latest_version(project_id, item_id, token):
    url = f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/items/{item_id}/versions"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()["data"][0]["id"]


# ------------------------------------------------------------
# EXTRACT IFC PROPERTIES
# ------------------------------------------------------------
def extract_ifc_properties(version_urn, token):
    headers = {"Authorization": f"Bearer {token}"}

    encoded = base64.urlsafe_b64encode(version_urn.encode()).decode().rstrip("=")
    meta_url = f"https://developer.api.autodesk.com/modelderivative/v2/designdata/{encoded}/metadata"
    meta = requests.get(meta_url, headers=headers).json()

    views = meta.get("data", {}).get("metadata", [])
    if not views:
        return []

    view_guid = views[0]["guid"]

    prop_url = f"https://developer.api.autodesk.com/modelderivative/v2/designdata/{encoded}/metadata/{view_guid}/properties"
    props = requests.get(prop_url, headers=headers).json()

    items = []

    for e in props.get("data", {}).get("collection", []):
        ext = e.get("externalId")
        if not ext:
            continue

        ifc = e.get("properties", {}).get("IFC Attributes", {}) or {}
        ifc_class = ifc.get("IfcClass")
        if not ifc_class:
            continue

        items.append({
            "name": e.get("name"),
            "externalId": ext,
            "decodedExternalId": decode_external_id(ext),
            "ifcClass": ifc_class,
            "objectType": ifc.get("ObjectType"),
            "predefinedType": ifc.get("predefinedType"),
            "tag": ifc.get("Tag"),
            "spatialContainer": ifc.get("IfcSpatialContainer"),
            "rawAttributes": ifc
        })

    return items


# ------------------------------------------------------------
# MAP IFC → ASSET FORMAT
# ------------------------------------------------------------
def map_ifc_to_assets(ifc_items):
    assets = []

    for idx, item in enumerate(ifc_items, start=1):
        name = item.get("name")
        raw = item.get("rawAttributes", {})
        global_id = raw.get("GlobalId")

        # Skip invalid rows
        if not name or not global_id:
            continue

        asset = {
            "name": name,
            "description": item.get("tag") or "",
            "category": item.get("ifcClass") or "Default",
            "status": item.get("predefinedType") or "Default",
            "location": {
                "latitude": None,
                "longitude": None
            },
            "custom_attributes": {
                "GlobalId": global_id
            }
        }

        assets.append(asset)

    return assets

# ------------------------------------------------------------
# MAIN WORKFLOW (extract + map)
# ------------------------------------------------------------
def fetch_ifc_metadata():
    print("🚀 Fetching IFC Metadata & Mapping to Asset Format")

    token = get_token()
    hubs = list_hubs(token)
    HUB_ID = hubs[0]["id"]  # auto-select first hub

    raw = config.project_id.strip()
    PROJECT_ID = raw if raw.startswith("b.") else f"b.{raw}"

    root = get_root_folder(HUB_ID, PROJECT_ID, token)
    files = list_ifc_files(PROJECT_ID, root, token)

    all_ifc = []
    for f in files:
        urn = get_latest_version(PROJECT_ID, f["id"], token)
        all_ifc.extend(extract_ifc_properties(urn, token))

    # Save output to root/output directory
    output_dir = Path(__file__).resolve().parents[2] / "output"
    output_dir.mkdir(exist_ok=True)

    raw_path = output_dir / "ifc_raw_metadata.json"
    with raw_path.open("w", encoding="utf-8") as f:
        json.dump(all_ifc, f, indent=2)
    print(f"💾 Saved Raw IFC metadata → {raw_path}")

    mapped = map_ifc_to_assets(all_ifc)
    mapped_path = output_dir / "mapped_assets.json"
    with mapped_path.open("w", encoding="utf-8") as f:
        json.dump(mapped, f, indent=2)
    print(f"💾 Saved Mapped Asset Data → {mapped_path}")

    print(f"\n🎉 DONE! Extracted {len(all_ifc)} IFC items, mapped {len(mapped)} assets.\n")

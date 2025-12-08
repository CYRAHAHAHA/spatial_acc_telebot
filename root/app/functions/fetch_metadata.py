import json
import requests
import base64
import csv
from pathlib import Path

from app.functions.authentication import AutodeskAuth
from app.functions.fetch_all_assets_info import fetch_all_assets_info
from app.config import config


# ------------------------------------------------------------
# Decode externalId
# ------------------------------------------------------------
def decode_external_id(b64_id: str):
    try:
        padding = "=" * (-len(b64_id) % 4)
        return base64.b64decode(b64_id + padding).decode("utf-8")
    except Exception:
        return None

# ------------------------------------------------------------
# LIST IFC FILES
# ------------------------------------------------------------
def list_ifc_files(project_id: str, folder_id: str, token: str):
    headers = {"Authorization": f"Bearer {token}"}

    def get_contents(folder):
        url = f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/folders/{folder}/contents"
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        return res.json().get("data", [])

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

    print(f"🔍 Found {len(found)} IFC file(s)")
    return found


# ------------------------------------------------------------
# GET LATEST VERSION
# ------------------------------------------------------------
def get_latest_version(project_id: str, item_id: str, token: str):
    url = f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/items/{item_id}/versions"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()["data"][0]["id"]


# ------------------------------------------------------------
# EXTRACT IFC METADATA (FULL)
# ------------------------------------------------------------
def extract_ifc_properties(version_urn: str, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    encoded_urn = base64.urlsafe_b64encode(version_urn.encode()).decode().rstrip("=")

    meta_url = f"https://developer.api.autodesk.com/modelderivative/v2/designdata/{encoded_urn}/metadata"
    meta = requests.get(meta_url, headers=headers).json()

    all_items = []
    metadata_views = meta.get("data", {}).get("metadata", [])

    for view in metadata_views:
        guid = view.get("guid")
        view_name = view.get("name")

        print(f"📄 Reading view → {view_name}")

        prop_url = f"https://developer.api.autodesk.com/modelderivative/v2/designdata/{encoded_urn}/metadata/{guid}/properties"
        res = requests.get(prop_url, headers=headers).json()

        for e in res.get("data", {}).get("collection", []):
            ext_id = e.get("externalId")
            if not ext_id:
                continue

            props = e.get("properties", {}) or {}
            ifc = props.get("IFC Attributes") or {}

            all_items.append({
                "name": e.get("name"),
                "externalId": ext_id,
                "decodedExternalId": decode_external_id(ext_id),
                "geometry": e.get("geometry", {}),
                "viewGuid": guid,
                "viewName": view_name,
                "allProperties": props,
                "ifcAttributes": ifc
            })

    print(f"📌 Extracted {len(all_items)} metadata elements")
    return all_items


# ------------------------------------------------------------
# LOAD ASSET NAMES FROM CSV → MATCH EXACT IFC .name
# ------------------------------------------------------------
def load_asset_names_from_csv(csv_path: Path):
    if not csv_path.exists():
        print(f"⚠ Missing CSV: {csv_path}")
        return set()

    names = set()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if "clientAssetId" not in (reader.fieldnames or []):
            print("⚠ Missing 'clientAssetId' column!")
            return set()

        for row in reader:
            val = (row.get("clientAssetId") or "").strip().lower()
            if val:
                names.add(val)

    print(f"📄 Loaded {len(names)} clientAssetId entries")
    return names


# ------------------------------------------------------------
# MAIN WORKFLOW
# ------------------------------------------------------------
def fetch_ifc_metadata(token: str):
    #hubs = list_hubs(token)
    #hub_id = hubs[0]["id"]

    project_id = config.project_id.strip()
    if not project_id.startswith("b."):
        project_id = f"b.{project_id}"

    #root = get_root_folder(hub_id, project_id, token)
    root = config.root_id
    ifc_files = list_ifc_files(project_id, root, token)

    final_ifc = []
    for file in ifc_files:
        urn = get_latest_version(project_id, file["id"], token)
        final_ifc.extend(extract_ifc_properties(urn, token))

    data_dir = Path(__file__).resolve().parents[3] / "data"
    data_dir.mkdir(exist_ok=True)

    raw_path = data_dir / "nlp_raw_metadata.json"
    json.dump(final_ifc, raw_path.open("w", encoding="utf-8"), indent=2)
    print(f"💾 Raw metadata saved → {raw_path}")

    print("\n📥 Fetching all ACC assets before filtering IFC metadata...")
    fetch_all_assets_info(token)

    # Filter results using CSV names
    csv_path = data_dir / "assets_total.csv"
    ids = load_asset_names_from_csv(csv_path)

    if ids:
        filtered = []

        for item in final_ifc:
            name = (item.get("name") or "").strip().lower()
            if name not in ids:
                continue

            props = item.get("allProperties", {})
            ifc = item.get("ifcAttributes", {})

            # Identify the LargeBuilding classifier key
            large_building_key = None
            for key in props.keys():
                if key.startswith("LargeBuilding-"):
                    large_building_key = key
                    break

            host = ifc.get("IfcContainedInHost")

            filtered.append({
                "name": item.get("name"),
                "ifcAttributes": {
                    "GlobalId": ifc.get("GlobalId"),
                    "ObjectType": ifc.get("ObjectType"),
                    "IfcClass": ifc.get("IfcClass"),
                    "IfcPropertySetList": ifc.get("IfcPropertySetList"),
                    "IfcSpatialContainer": ifc.get("IfcSpatialContainer"),
                    "IfcContainedInHost": host,
                },
                # Only keep the classifier ID, not its content
                "classificationId": large_building_key
            })

        filtered_path = data_dir / "model.json"
        json.dump(filtered, filtered_path.open("w", encoding="utf-8"), indent=2)
        print(f"💾 Filtered metadata saved ({len(filtered)} items) → {filtered_path}")
    else:
        print("⚠ No matches — filtered JSON not created")

    print("\n🎉 Metadata extraction complete!\n")



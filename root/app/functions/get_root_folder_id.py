import requests
from app.config import config

# Helper function used exclusively to obtain the project’s Root Folder ID,
# which will later be persisted in the environment configuration (.env).
# Root folder id can only be obtined by the root folder owner 

def discover_root_folder(token: str):
    """
    Complete workflow:
    1. Use provided token
    2. Get hubs
    3. Pick correct hub
    4. Format project_id as 'b.<id>'
    5. Fetch top-level folders
    6. Return the root folder ID
    """

    # Prepare headers for all API calls
    headers = {"Authorization": f"Bearer {token}"}

    # ------------------------------------------------------------
    # 2. List hubs
    # ------------------------------------------------------------
    hubs_url = "https://developer.api.autodesk.com/project/v1/hubs"
    hubs_res = requests.get(hubs_url, headers=headers)
    hubs_res.raise_for_status()

    hubs = hubs_res.json().get("data", [])
    if not hubs:
        raise Exception("❌ No hubs found!")

    print(f"🏢 Found {len(hubs)} hub(s)")

    # Use the first hub (typical Autodesk setup)
    hub_id = hubs[0]["id"]
    print(f"🏢 Using Hub ID: {hub_id}")

    # ------------------------------------------------------------
    # 3. Ensure proper project_id format (must start with 'b.')
    # ------------------------------------------------------------
    project_id = config.project_id.strip()
    if not project_id.startswith("b."):
        project_id = f"b.{project_id}"

    print(f"📁 Project ID: {project_id}")

    # ------------------------------------------------------------
    # 4. Fetch top-level folders
    # ------------------------------------------------------------
    folder_url = (
        f"https://developer.api.autodesk.com/project/v1/hubs/"
        f"{hub_id}/projects/{project_id}/topFolders"
    )

    folder_res = requests.get(folder_url, headers=headers)
    folder_res.raise_for_status()

    folders = folder_res.json().get("data", [])
    if not folders:
        raise Exception("❌ No top folders found!")

    # ------------------------------------------------------------
    # 5. Find the “Project Files” folder (case-insensitive)
    # ------------------------------------------------------------
    root_folder = next(
        (f for f in folders if f["attributes"]["name"].lower() == "project files"),
        None
    )

    # Fallback: use first folder if “Project Files” isn't present
    root_id = root_folder["id"] if root_folder else folders[0]["id"]

    print(f"📦 Root Folder ID Found → {root_id}")

    # ------------------------------------------------------------
    # 6. Return results
    # ------------------------------------------------------------
    return {
        "hub_id": hub_id,
        "project_id": project_id,
        "root_folder_id": root_id,
        "token": token
    }

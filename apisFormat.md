# API Routes Reference

Use this guide to call the Flask backend from Python scripts. 

```python
import requests

BASE_URL = "http://localhost:8080"
HEADERS = {
    "Content-Type": "application/json",
}
```


## 1. Asset & Configuration Operations

Functional routes to interact with ACC.

### `GET /fetch_assets_config`

Fetch ACC configuration from Autodesk and regenerate CSVs (`status_sets.csv`, `custom_fields.csv`, `categories.csv`).

```python
resp = requests.get(f"{BASE_URL}/fetch_assets_config", headers=HEADERS, allow_redirects=False)
print(resp.status_code, resp.headers.get("Location"))
```

### `GET /fetch_all_assets_info`

Fetch all assets from ACC and save `data/assets_total.csv`.

```python
resp = requests.get(f"{BASE_URL}/fetch_all_assets_info", headers=HEADERS, allow_redirects=False)
print(resp.status_code, resp.headers.get("Location"))
```

### `POST /update_status`

Update a single asset’s status. Body must include `asset_guid` (maps to assetId) and `status_value` (status label from `status_sets.csv`).

```python
payload = {
    "asset_guid": "2f845f53-d5d1-4e1b-a5f0-1234567890ab",
    "status_value": "Specified"
}
resp = requests.post(f"{BASE_URL}/update_status", headers=HEADERS, json=payload, timeout=15)
print(resp.status_code, resp.json())
```

### `POST /create_status_sets_from_json`

Send an array of status set definitions to ACC. You can reuse the payload returned by `/api/payload/status_sets`.

```python
# Use payload fetched earlier or construct your own list of status sets
status_sets_payload = [
    {
        "name": "Fabrication",
        "status_set_description": "Stages of fabrication",
        "status_label": ["Pending", "In Progress", "Completed"],
        "description": ["Pending", "In Progress", "Completed"],
        "status_colors": ["adsk-blue-500", "adsk-blue-500", "adsk-blue-500"]
    }
]

resp = requests.post(
    f"{BASE_URL}/create_status_sets_from_json",
    headers=HEADERS,
    json=status_sets_payload,
    timeout=30
)
print(resp.status_code, resp.json())
```

### `POST /create_custom_fields_from_json`

Send an array of custom field definitions to ACC. You can reuse the payload returned by `/api/payload/custom_fields`.

```python
custom_fields_payload = [
    {
        "displayName": "Inspection Date",
        "dataType": "date",
        "requiredOnIngress": False,
        "description": "Date of most recent inspection",
        "enumValues": []
    }
]

resp = requests.post(
    f"{BASE_URL}/create_custom_fields_from_json",
    headers=HEADERS,
    json=custom_fields_payload,
    timeout=30
)
print(resp.status_code, resp.json())
```

## Notes

Copy the snippets above into your Python code and adjust payloads to match your use case.// filepath: c:\Users\User\Documents\GitHub\spatial_acc_telebot\apisFormat.md

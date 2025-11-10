# API Routes Reference

Use this guide to call the Flask backend from Python scripts. 

```python
import requests

BASE_URL = "http://localhost:8080"
HEADERS = {
    "Content-Type": "application/json",
}
```

---

## 1. Asset & Configuration Operations

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
Update a single asset’s status. Provide `asset_guid` (maps to assetId) and `status_value` (status label from `status_sets.csv`).

```python
payload = {
    "asset_guid": "2f845f53-d5d1-4e1b-a5f0-1234567890ab",
    "status_value": "Specified"
}
resp = requests.post(f"{BASE_URL}/update_status", headers=HEADERS, json=payload, timeout=15)
print(resp.status_code, resp.json())
```

---

## 2. Creation APIs

### `GET /api/payload/status_sets`
Return the hardcoded payload from `data/new_status_sets.json`.

```python
resp = requests.get(f"{BASE_URL}/api/payload/status_sets", timeout=10)
resp.raise_for_status()
status_sets_payload = resp.json()
print(status_sets_payload)
```

### `POST /create_status_sets_from_json`
Post an array of status set definitions to ACC.

```python
status_sets_payload = [
    {
        "name": "Fabrication",
        "status_set_description": "Stages of fabrication",
        "status_label": ["Pending", "In Progress", "Completed"],
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

### `GET /api/payload/custom_fields`
Return the hardcoded payload from `data/new_custom_fields.json`.

```python
resp = requests.get(f"{BASE_URL}/api/payload/custom_fields", timeout=10)
resp.raise_for_status()
custom_fields_payload = resp.json()
print(custom_fields_payload)
```

### `POST /create_custom_fields_from_json`
Post an array of custom field definitions to ACC.

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

### `GET /api/payload/categories`
Return the hardcoded payload from `data/new_categories.json`.

```python
resp = requests.get(f"{BASE_URL}/api/payload/categories", timeout=10)
resp.raise_for_status()
categories_payload = resp.json()
print(categories_payload)
```

### `POST /create_categories_from_json`
Create categories, assign status sets, and attach custom fields based on the JSON payload.

```python
categories_payload = [
    {
        "name": "Custom asdasd",
        "description": "This is a description for Custom Category 1",
        "category_parent_id": 1,
        "status_set_name": "Default",
        "custom_fields": ["IFCGlobalId", "Discipline"]
    }
]
resp = requests.post(
    f"{BASE_URL}/create_categories_from_json",
    headers=HEADERS,
    json=categories_payload,
    timeout=30
)
print(resp.status_code, resp.json())
```

---

## Notes

- Protected routes (`fetch_*`, `create_*`, `update_status`) require a valid Autodesk access token. Supply it via the `Authorization` header as shown.
- Responses include detailed error messages; always check `resp.status_code` before using the data.
- Payloads provided here match the JSON files in `data/` and can be copied directly into your scripts.

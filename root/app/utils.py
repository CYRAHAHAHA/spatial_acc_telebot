from functools import wraps
from urllib.parse import quote_plus
from flask import current_app, session, redirect
from pathlib import Path
from typing import Dict, List, Any
import csv
import os


def require_access_token(pass_token: bool = False, msg: str = "Please configure Autodesk credentials and authenticate."):
    """
    Ensures a valid access token via current_app.autodesk_auth.
    - Reloads tokens from file (load_tokens), then tries to refresh/get.
    - Stores it in session["access_token"].
    - Injects it into the view as kwarg 'token' when pass_token=True.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            auth = getattr(current_app, "autodesk_auth", None)
            token = None
            if auth:
                # Always reload from file to pick up tokens saved by /callback or other processes
                auth.load_tokens()
                token = auth.get_access_token()
            if not token:
                return redirect("/?msg=" + quote_plus(msg))
            session["access_token"] = token
            if pass_token:
                kwargs["token"] = token
            return view_func(*args, **kwargs)
        return wrapper
    return decorator


# ============ CSV Utility Functions ============

def get_persistent_dir(subdir: str = "") -> Path:
    """
    Get persistent directory path for Railway or local development.
    Railway volumes should be mounted at /app/data for persistence.
    
    Args:
        subdir: Optional subdirectory name
    
    Returns:
        Path object to persistent directory
    """
    if os.getenv("RAILWAY_ENVIRONMENT"):
        # Railway deployment - use mounted volume
        base = Path("/app/data")
    else:
        # Local development - use workspace data directory
        base = Path(__file__).resolve().parents[2] / "data"
    
    base.mkdir(parents=True, exist_ok=True)
    
    if subdir:
        full_path = base / subdir
        full_path.mkdir(parents=True, exist_ok=True)
        return full_path
    
    return base


def get_data_dir() -> Path:
    """Get the path to the data directory at workspace root level (spatial_acc_telebot/data)"""
    return get_persistent_dir()


def get_output_dir() -> Path:
    """Get the path to the output directory (root/output or Railway persistent)"""
    if os.getenv("RAILWAY_ENVIRONMENT"):
        # On Railway, use persistent volume for output too
        return get_persistent_dir("output")
    else:
        # Local development - use root/output
        return Path(__file__).resolve().parents[1] / "output"


def get_token_file_path() -> Path:
    """
    Get path for autodesk_tokens.json (must be persistent across deploys).
    
    Returns:
        Path object to token file location
    """
    if os.getenv("RAILWAY_ENVIRONMENT"):
        # Railway - store in persistent volume
        return get_persistent_dir() / "autodesk_tokens.json"
    else:
        # Local - store in root directory
        return Path(__file__).resolve().parents[1] / "autodesk_tokens.json"


def get_csv_path(filename: str) -> Path:
    """
    Get the full path to a CSV file in the data directory.
    
    Args:
        filename: Name of the CSV file (e.g., 'status_sets.csv')
    
    Returns:
        Path object to the CSV file in data directory
    """
    return get_data_dir() / filename


def read_status_sets_csv(project_id: str) -> Dict[str, str]:
    """
    Read status_sets.csv and return mapping of status_set_name -> status_set_id
    
    Args:
        project_id: Project ID to filter by (prefers matching project_id)
    
    Returns:
        Dictionary mapping status set names to IDs
    """
    csv_path = get_csv_path("status_sets.csv")
    mapping: Dict[str, str] = {}
    
    if not csv_path.exists():
        print(f"Status sets CSV not found at {csv_path}")
        return mapping
    
    try:
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = (row.get("status_set_name") or "").strip()
                sid = (row.get("status_set_id") or "").strip()
                proj = (row.get("project_id") or "").strip()
                
                if not name or not sid:
                    continue
                
                # Keep first match for a given name
                if name not in mapping:
                    mapping[name] = sid
                
                # If a row matches current project, override to ensure correct one
                if proj == project_id:
                    mapping[name] = sid
    except Exception as ex:
        print(f"Failed to read status sets CSV: {ex}")
    
    return mapping


def read_custom_fields_csv(project_id: str) -> Dict[str, str]:
    """
    Read custom_fields.csv and return mapping of field name/display_name -> custom_attribute_id
    
    Args:
        project_id: Project ID to filter by (prefers matching project_id)
    
    Returns:
        Dictionary mapping custom field names to IDs
    """
    csv_path = get_csv_path("custom_fields.csv")
    mapping: Dict[str, str] = {}
    
    if not csv_path.exists():
        print(f"Custom fields CSV not found at {csv_path}")
        return mapping
    
    try:
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                proj = (row.get("project_id") or "").strip()
                attr_id = (row.get("custom_attribute_id") or "").strip()
                name = (row.get("name") or "").strip()
                display = (row.get("display_name") or "").strip()
                
                if not attr_id:
                    continue
                
                # Map both name and display name to id (display names are used in user's JSON)
                if display and display not in mapping:
                    mapping[display] = attr_id
                if name and name not in mapping:
                    mapping[name] = attr_id
                
                # Prefer entries matching project_id
                if proj == project_id:
                    if display:
                        mapping[display] = attr_id
                    if name:
                        mapping[name] = attr_id
    except Exception as ex:
        print(f"Failed to read custom fields CSV: {ex}")
    
    return mapping


def read_categories_csv(project_id: str) -> Dict[str, str]:
    """
    Read categories.csv and return mapping of category_name -> category_id
    
    Args:
        project_id: Project ID to filter by (prefers matching project_id)
    
    Returns:
        Dictionary mapping category names to IDs
    """
    csv_path = get_csv_path("categories.csv")
    mapping: Dict[str, str] = {}
    
    if not csv_path.exists():
        print(f"Categories CSV not found at {csv_path}")
        return mapping
    
    try:
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                proj = (row.get("project_id") or "").strip()
                cat_id = (row.get("category_id") or "").strip()
                cat_name = (row.get("category_name") or "").strip()
                
                if not cat_id or not cat_name:
                    continue
                
                # Keep first match for a given name
                if cat_name not in mapping:
                    mapping[cat_name] = cat_id
                
                # Prefer entries matching project_id
                if proj == project_id:
                    mapping[cat_name] = cat_id
    except Exception as ex:
        print(f"Failed to read categories CSV: {ex}")
    
    return mapping


def write_csv(filename: str, data: List[Dict[str, Any]], headers: List[str]) -> None:
    """
    Write data to a CSV file in the data directory.
    
    Args:
        filename: Name of the CSV file (e.g., 'status_sets.csv')
        data: List of dictionaries containing row data
        headers: List of column headers
    """
    csv_path = get_csv_path(filename)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with csv_path.open('w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=headers, lineterminator='\n')
            writer.writeheader()
            # Convert all values to strings and handle None/empty values
            for row in data:
                formatted_row = {}
                for key in headers:
                    value = row.get(key)
                    if value is None:
                        formatted_row[key] = ""
                    elif isinstance(value, bool):
                        formatted_row[key] = "True" if value else "False"
                    else:
                        formatted_row[key] = str(value) if value != "" else ""
                writer.writerow(formatted_row)
        print(f"Successfully wrote {len(data)} rows to {csv_path}")
    except Exception as ex:
        print(f"Failed to write CSV {filename}: {ex}")
        raise

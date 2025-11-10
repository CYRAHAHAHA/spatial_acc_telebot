from pathlib import Path
from flask import Flask, jsonify, request, session
from app.config import config
from app.authentication import AutodeskAuth
from datetime import datetime, timezone
from flask_cors import CORS
import csv
import json
import re

app = Flask(__name__, static_folder="src", static_url_path="/")
app.secret_key = "supersecretkey"

# Enable CORS for API routes
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# Token manager (persists tokens, refreshes when needed)
app.autodesk_auth = AutodeskAuth(
    client_id=getattr(config, "client_id", ""),
    client_secret=getattr(config, "client_secret", ""),
    redirect_uri=getattr(config, "redirect_uri", ""),
    scopes=getattr(config, "scopes", "data:read data:write data:create"),
)

# Register server-side routes (authorize, preview, create, etc.)
from app import routes

# ---- Static front page ----
@app.route("/")
def index():
    # Serve the SPA/static page
    return app.send_static_file("index.html")

# ---- Routes for UI interface ---- (not API) ---- #
# ---- API: token/env status ----
@app.route("/api/status")
def api_status():
    auth = app.autodesk_auth
    try:
        auth.load_tokens()
    except Exception:
        pass

    token_valid = bool(auth.is_token_valid())
    expires_at_iso = getattr(auth, "expires_at", None)

    expires_in_minutes = None
    if expires_at_iso:
        try:
            exp_dt = datetime.fromisoformat(expires_at_iso)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            delta = exp_dt - datetime.now(timezone.utc)
            expires_in_minutes = max(0, int(delta.total_seconds() // 60))
        except Exception:
            expires_in_minutes = None

    # Build env keys (primitive-only for safety)
    env = {}
    for k in dir(config):
        if k.startswith("__"):
            continue
        try:
            v = getattr(config, k)
            if callable(v):
                continue
            env[k] = v
        except Exception:
            continue

    return jsonify({
        "user": getattr(config, "user", ""),
        "token": {
            "valid": token_valid,
            "expiresAt": expires_at_iso,
            "expiresInMinutes": expires_in_minutes,
        },
        "env": env,
        "message": request.args.get("msg", "")
    })

# ---- API: categories and hierarchy (from session.aggregated_data) ----
@app.route("/api/categories")
def api_categories():
    aggregated = session.get("aggregated_data") or {}
    cats = aggregated.get("categories", [])

    # Build children map if not present
    by_id = {c.get("categoryId"): dict(c) for c in cats if c.get("categoryId")}
    for c in by_id.values():
        c.setdefault("children", [])

    # If no children arrays, derive from parentId
    if cats and not any(c.get("children") for c in cats):
        for c in cats:
            pid = c.get("parentId")
            cid = c.get("categoryId")
            if pid and pid in by_id and cid:
                by_id[pid].setdefault("children", []).append(cid)

    roots = [c for c in by_id.values() if not c.get("parentId")]

    def build_tree(node):
        out = {
            "categoryId": node.get("categoryId"),
            "categoryName": node.get("categoryName"),
            "statusSetName": node.get("statusSetName"),
            "parentId": node.get("parentId"),
            "children": []
        }
        for ch_id in node.get("children", []):
            child = by_id.get(ch_id)
            if child:
                out["children"].append(build_tree(child))
        return out

    tree = [build_tree(r) for r in roots] if roots else []

    return jsonify({
        "count": len(cats),
        "categories": cats,
        "tree": tree
    })

# --- Payload APIs (read hardcoded JSON files for creation) ---
@app.route("/api/payload/status_sets")
def api_payload_status_sets():
    data_dir = Path(__file__).resolve().parents[1] / "output"
    p = data_dir / "new_status_sets.json"
    try:
        with p.open("r", encoding="utf-8") as f:
            items = json.load(f)
        if not isinstance(items, list):
            return jsonify({"error": "new_status_sets.json must be a JSON array."}), 400
        return jsonify(items)
    except Exception as ex:
        return jsonify({"error": f"Failed to read new_status_sets.json: {ex}"}), 404

@app.route("/api/payload/custom_fields")
def api_payload_custom_fields():
    data_dir = Path(__file__).resolve().parents[1] / "output"
    p = data_dir / "new_custom_fields.json"
    try:
        with p.open("r", encoding="utf-8") as f:
            items = json.load(f)
        if not isinstance(items, list):
            return jsonify({"error": "new_custom_fields.json must be a JSON array."}), 400
        return jsonify(items)
    except Exception as ex:
        return jsonify({"error": f"Failed to read new_custom_fields.json: {ex}"}), 404

# --- CSV preview APIs (no auth required) ---
@app.route("/api/preview/status_sets")
def api_preview_status_sets():
    """
    Read data/status_sets.csv and return grouped JSON by status_set_id.
    """
    data_dir = Path(__file__).resolve().parents[1] / "output"
    p = data_dir / "status_sets.csv"
    if not p.exists():
        return jsonify({"error": "status_sets.csv not found"}), 404

    sets = {}
    try:
        with p.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ss_id = row.get("status_set_id") or ""
                ss_name = row.get("status_set_name") or ""
                status = {
                    "statusId": row.get("status_id") or "",
                    "label": row.get("status_label") or "",
                    "description": row.get("status_description") or "",
                }
                if ss_id not in sets:
                    sets[ss_id] = {
                        "statusSetId": ss_id,
                        "name": ss_name,
                        "statuses": [],
                    }
                sets[ss_id]["statuses"].append(status)
        items = list(sets.values())
        return jsonify({"count": len(items), "items": items})
    except Exception as ex:
        return jsonify({"error": f"Failed to read status_sets.csv: {ex}"}), 500

@app.route("/api/preview/custom_fields")
def api_preview_custom_fields():
    """
    Read data/custom_fields.csv and return normalized JSON list.
    """
    data_dir = Path(__file__).resolve().parents[1] / "output"
    p = data_dir / "custom_fields.csv"
    if not p.exists():
        return jsonify({"error": "custom_fields.csv not found"}), 404

    out = []
    pat = re.compile(r"^(.*)\(([^)]+)\)$")  # Label(id)
    try:
        with p.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                enum_pairs = []
                raw = (row.get("values_and_ids") or "").strip()
                if raw:
                    parts = [s.strip() for s in raw.split(";") if s.strip()]
                    for part in parts:
                        m = pat.match(part)
                        if m:
                            enum_pairs.append({"label": m.group(1).strip(), "id": m.group(2).strip()})
                        else:
                            enum_pairs.append({"label": part, "id": ""})
                else:
                    raw_vals = (row.get("values") or "").strip()
                    if raw_vals:
                        enum_pairs = [{"label": s.strip(), "id": ""} for s in raw_vals.split(",") if s.strip()]

                item = {
                    "id": row.get("custom_attribute_id") or "",
                    "displayName": row.get("display_name") or "",
                    "description": row.get("description") or "",
                    "dataType": row.get("data_type") or "",
                    "requiredOnIngress": str(row.get("required") or "").strip().lower() in ("true", "1", "yes", "y"),
                    "enumValues": enum_pairs,  # list of {label,id}
                }
                out.append(item)
        return jsonify({"count": len(out), "items": out})
    except Exception as ex:
        return jsonify({"error": f"Failed to read custom_fields.csv: {ex}"}), 500


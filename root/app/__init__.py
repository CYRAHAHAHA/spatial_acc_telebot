from click import Path
from flask import Flask, jsonify, request, session
from app.config import config
from app.authentication import AutodeskAuth
from datetime import datetime, timezone
from flask_cors import CORS

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
from flask import Flask, request, session
from app.config import config
from app.authentication import AutodeskAuth
from datetime import datetime  # added

app = Flask(__name__)
app.secret_key = "supersecretkey"  # required for session

# Instantiate token manager (persists tokens to file and refreshes when needed)
app.autodesk_auth = AutodeskAuth(
    client_id=getattr(config, "client_id", ""),
    client_secret=getattr(config, "client_secret", ""),
    redirect_uri=getattr(config, "redirect_uri", ""),
    scopes=getattr(config, "scopes", "data:read data:write data:create"),
)

from app import routes

@app.route("/")
def home():
    msg = request.args.get("msg", "")
    msg_html = f'<div class="msg">{msg}</div>' if msg else ""

    # Token status (load from file, check validity, show expiry)
    auth = app.autodesk_auth
    auth.load_tokens()
    token_valid = auth.is_token_valid()
    expires_at = auth.expires_at
    remaining_html = ""
    if expires_at:
        try:
            exp_dt = datetime.fromisoformat(expires_at)
            delta = exp_dt - datetime.now()
            mins = max(0, int(delta.total_seconds() // 60))
            remaining_html = f" — expires at {exp_dt.strftime('%Y-%m-%d %H:%M:%S')} (in ~{mins} min)"
        except Exception:
            pass
    token_status_html = f"<p><strong>Token:</strong> {'VALID' if token_valid else 'MISSING/EXPIRED'}{remaining_html}</p>"

    # List env var key and values
    keys = [attr for attr in dir(config) if not attr.startswith('__') and not callable(getattr(config, attr))]
    keys_list_html = "<ul>" + "".join(f"<li>{k}: {getattr(config, k)}</li>" for k in keys) + "</ul>"

    # Pull aggregated data from session
    aggregated_data = session.get("aggregated_data")
    assets_html = ""

    if aggregated_data:
        print("---Rendering aggregated data----")
        # ---- Custom Attributes ----
        assets_html += "<h3>Custom Attributes</h3><ul>"
        for ca in aggregated_data.get("customAttributes", []):
            for k, v in ca.items():
                if k != "id":
                    assets_html += f"<li><strong>{k}</strong> – {v} - {ca.get('id')}</li>"
        assets_html += "</ul>"

        # ---- Status Sets ----
        assets_html += "<h3>Status Sets (Expanded)</h3>"
        for ss in aggregated_data.get("statusSets", []):
            assets_html += f"<p><strong>{ss.get('name')}</strong> – {ss.get('description','')} - {ss.get('id')}</p><ul>"
            for st in ss.get("statuses", []):
                assets_html += f"<li>{st.get('label')} – {st.get('description','')} - {st.get('id')}</li>"
            assets_html += "</ul>"

        # ---- Categories ----
        assets_html += "<h3>Categories & Their Statuses</h3>"
        for cat in aggregated_data.get("categories", []):
            assets_html += f"<p><strong>{cat.get('categoryName')}</strong> → Status Set: {cat.get('statusSetName')}</p><ul>"
            for st in cat.get("statuses", []):
                assets_html += f"<li>{st.get('label')} – {st.get('description','')}</li>"
            assets_html += "</ul>"

    return f'''
        <h1>ACC API Integration</h1>
        {msg_html}
        {token_status_html}
        <h3>Current user: {config.user}</h3>
        <p>Env variable keys for this user:</p>
        {keys_list_html}

        <form action="/authorize">
            <button type="submit">Authorize with Autodesk</button>
        </form>

        <form action="/fetch_assets_config">
            <button type="submit">Fetch Assets Config</button>
        </form>

        <form action="/create_status_sets_from_csv">
            <button type="submit">📊 Create Status Sets from CSV</button>
        </form>

        <form action="/create_custom_fields_from_csv">
            <button type="submit">📊 Create Custom Fields from CSV</button>
        </form>

        <hr/>
        {assets_html}
    '''

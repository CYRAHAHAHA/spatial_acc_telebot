from flask import Flask, request, session
from app.config import config

app = Flask(__name__)
app.secret_key = "supersecretkey"  # required for session
from app import routes

@app.route("/")
def home():
    msg = request.args.get("msg", "")
    msg_html = f'<div class="msg">{msg}</div>' if msg else ""

    # List env var key and values
    keys = [attr for attr in dir(config) if not attr.startswith("__") and not callable(getattr(config, attr))]
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
                assets_html += f"<li><strong>{k}</strong> – {v}</li>"
        assets_html += "</ul>"

        # ---- Status Sets ----
        assets_html += "<h3>Status Sets (Expanded)</h3>"
        for ss in aggregated_data.get("statusSets", []):
            assets_html += f"<p><strong>{ss.get('name')}</strong> – {ss.get('description','')}</p><ul>"
            for st in ss.get("statuses", []):
                assets_html += f"<li>{st.get('label')} – {st.get('description','')}</li>"
            assets_html += "</ul>"

        # ---- Categories ----
        assets_html += "<h3>Categories & Their Statuses</h3>"
        for cat in aggregated_data.get("categories", []):
            assets_html += f"<p><strong>{cat.get('categoryName')}</strong> → Status Set: {cat.get('statusSetName')}</p><ul>"
            for st in cat.get("statuses", []):
                assets_html += f"<li>{st.get('label')} – {st.get('description','')}</li>"
            assets_html += "</ul>"

        # ---- Hierarchy Tree ----
        # Build dict of categoryId -> category for fast lookup
        categories_dict = {c["categoryId"]: c for c in aggregated_data["categories"]}
        # Find root categories (no parentId)
        roots = [c for c in aggregated_data["categories"] if not c.get("parentId")]

        def render_category_tree(cat):
            html = f"<li><strong>{cat['categoryName']}</strong> → Status Set: {cat['statusSetName']}</li>"
            children = [categories_dict[ch_id] for ch_id in cat.get("children", []) if ch_id in categories_dict]
            if children:
                html += "<ul>"
                for child in children:
                    html += render_category_tree(child)
                html += "</ul>"
            return html

        assets_html += "<h3>Category Hierarchy</h3><ul>"
        for root in roots:
            assets_html += render_category_tree(root)
        assets_html += "</ul>"
        print("----- Aggregated Data Rendered Below -----")
        print(assets_html)

    return f'''
        <h1>ACC API Integration</h1>
        {msg_html}
        <h3>Current user: {config.user}</h3>
        <p>Env variable keys for this user:</p>
        {keys_list_html}

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

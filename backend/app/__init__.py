from flask import Flask, request, session
from app.config import config

app = Flask(__name__)
app.secret_key = "supersecretkey"  # required for session
# import routes so Flask registers them
from app import routes

@app.route("/")
def home():
    msg = request.args.get("msg", "")
    msg_html = f'<div class="msg">{msg}</div>' if msg else ""

    # List all keys for current user
    keys = [attr for attr in dir(config) if not attr.startswith("__") and not callable(getattr(config, attr))]
    keys_list_html = "<ul>" + "".join(f"<li>{k}</li>" for k in keys) + "</ul>"

    # Display aggregated data if present
    agg = session.get("aggregated_data")
    agg_html = ""
    if agg:
        agg_html += "<h3>Categories & Linked Status Sets</h3><ul>"
        for cat in agg["categories"]:
            agg_html += f"<li>{cat['categoryName']} → Status Set: {cat['statusSetName']}</li>"
        agg_html += "</ul>"

        agg_html += f"<p>Custom Attributes Count: {len(agg['customAttributes'])}</p>"
        agg_html += f"<p>Status Sets Count: {len(agg['statusSets'])}</p>"

    return f'''
        <h1>ACC API Integration</h1>
        {msg_html}
        <h3>Current user: {config.user}</h3>
        <p>Env variable keys for this user:</p>
        {keys_list_html}
        <form action="/fetch_assets_config">
            <button type="submit">Fetch Assets Config</button>
        </form>
        {agg_html}
    '''
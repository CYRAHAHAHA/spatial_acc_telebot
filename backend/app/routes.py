from flask import redirect, request, session
from app import app
from app.functions.fetch_assets_config import fetch_assets_config
from app.utils import require_access_token
from app.config import config
from app.functions.create_status_sets import create_status_sets
from app.functions.create_custom_fields import create_custom_fields
from urllib.parse import quote_plus
from app.authentication import AutodeskAuth

# Use the AutodeskAuth instance attached to the Flask app
@app.route("/authorize")
def authorize():
    auth_url = app.autodesk_auth.get_auth_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return redirect("/?msg=" + quote_plus("No authorization code received."))
    token = app.autodesk_auth.exchange_code_for_tokens(code)
    if not token:
        return redirect("/?msg=" + quote_plus("Token exchange failed."))
    # Persist the fresh token for immediate use
    session["access_token"] = token
    return redirect("/?msg=" + quote_plus("Authenticated successfully."))

@app.route("/switch_user/<user>")
def switch_user(user):
    config.switch_user(user)
    session.pop("access_token", None)
    return redirect("/")

@app.route("/fetch_assets_config")
@require_access_token(pass_token=True)
def fetch_assets(token):
    return fetch_assets_config(token)

@app.route("/create_status_sets_from_csv")
@require_access_token(pass_token=True)
def create_status_sets_from_csv(token):
    create_status_sets(token)
    return redirect("/?msg=Created+status+sets+from+CSV")

@app.route("/create_custom_fields_from_csv")
@require_access_token(pass_token=True)
def create_custom_fields_from_csv(token):
    create_custom_fields(token)
    return redirect("/?msg=Created+custom+fields+from+CSV")
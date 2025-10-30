from flask import redirect, request, session
from app import app
from app.functions.auth import build_auth_url, exchange_token
from app.functions.fetch_assets_config import fetch_assets_config
from app.utils import require_access_token
from app.config import config
from app.functions.create_status_sets import create_status_sets
from app.functions.create_custom_fields import create_custom_fields

@app.route("/authorize")
def authorize():
    next_func = request.args.get("next", "/")
    return redirect(build_auth_url(next_func))

@app.route("/callback")
def callback():
    return exchange_token()

@app.route("/switch_user/<user>")
def switch_user(user):
    config.switch_user(user)
    return redirect("/")

@app.route("/fetch_assets_config")
@require_access_token("/fetch_assets_config")
def fetch_assets():
    return fetch_assets_config()

@app.route("/create_status_sets_from_csv")
@require_access_token("/create_status_sets_from_csv")
def create_status_sets_from_csv():
    create_status_sets()
    return redirect("/?msg=Created+status+sets+from+CSV")

@app.route("/create_custom_fields_from_csv")
@require_access_token("/create_custom_fields_from_csv")
def create_custom_fields_from_csv():
    create_custom_fields()
    return redirect("/?msg=Created+custom+fields+from+CSV")
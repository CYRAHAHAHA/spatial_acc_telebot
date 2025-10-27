import requests, urllib.parse
from flask import request, redirect
from app.config import config

def build_auth_url(next_func="/"):
    auth_url = (
        "https://developer.api.autodesk.com/authentication/v2/authorize"
        f"?response_type=code"
        f"&client_id={config.client_id}"
        f"&redirect_uri={urllib.parse.quote_plus(config.redirect_uri)}"
        f"&scope={urllib.parse.quote_plus(config.scopes)}"
    )
    return f"{auth_url}&state={urllib.parse.quote_plus(next_func)}"

def exchange_token():
    code = request.args.get("code")
    next_func = request.args.get("state", "/")

    if not code:
        msg = urllib.parse.quote_plus("No authorization code received.")
        return redirect(f"/?msg={msg}")

    token_url = "https://developer.api.autodesk.com/authentication/v2/token"
    data = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.redirect_uri
    }

    token_response = requests.post(token_url, data=data)
    if token_response.status_code != 200:
        msg = urllib.parse.quote_plus(f"Token exchange failed: {token_response.text}")
        return redirect(f"/?msg={msg}")

    access_token = token_response.json()["access_token"]
    return redirect(f"{next_func}?access_token={access_token}")

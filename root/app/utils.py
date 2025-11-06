from functools import wraps
from urllib.parse import quote_plus
from flask import current_app, session, redirect

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

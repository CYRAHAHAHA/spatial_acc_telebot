from functools import wraps
from flask import request, redirect

def require_access_token(next_func=None):
    """
    Decorator to ensure access_token exists in query params.
    If missing, redirects to /authorize and comes back here.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = request.args.get("access_token")
            endpoint = next_func if next_func else request.path
            if not token:
                return redirect(f"/authorize?next={endpoint}")
            return f(*args, **kwargs)
        return wrapper
    return decorator

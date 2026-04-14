from functools import wraps
from flask import request, jsonify
from services.auth_service import decode_token

def _token():
    auth = request.headers.get("Authorization","")
    if auth.startswith("Bearer "): return auth[7:]
    return request.cookies.get("token")

def require_auth(f):
    @wraps(f)
    def wrap(*a,**kw):
        t = _token()
        if not t: return jsonify({"error":"No token"}),401
        p,e = decode_token(t)
        if e:  return jsonify({"error":e}),401
        request.user = p; return f(*a,**kw)
    return wrap

def require_role(*roles):
    def dec(f):
        @wraps(f)
        def wrap(*a,**kw):
            t = _token()
            if not t: return jsonify({"error":"Unauthorized"}),401
            p,e = decode_token(t)
            if e: return jsonify({"error":e}),401
            if p.get("role") not in roles:
                return jsonify({"error":f"Forbidden. Requires: {list(roles)}"}),403
            request.user = p; return f(*a,**kw)
        return wrap
    return dec

"""
RBACMatrix AI — app.py
Your original smart MFA code + RBAC system added on top.
Roles: super_admin, admin, user
"""

from flask import Flask, request, jsonify, render_template, make_response
import pickle
import pandas as pd
import sqlite3
import hashlib
import jwt
import time
import random
import string
import datetime
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════════════════
#  CONFIG — edit these
# ══════════════════════════════════════════════════════════════════════════

EMAIL_SENDER   = "smart7mfa@gmail.com"
EMAIL_PASSWORD = "qbfq ujgg pnpo ikrc"

JWT_SECRET     = "rbacmatrix-secret-key-change-in-prod"
JWT_EXPIRY_HRS = 8

# Hardcoded Super Admin — change here anytime
SUPER_ADMIN_EMAIL    = "sanjay22522g@gmail.com"
SUPER_ADMIN_PASSWORD = "rbac@2006"
SUPER_ADMIN_NAME     = "Super Admin"

DB_PATH = "rbacmatrix.db"

# ══════════════════════════════════════════════════════════════════════════
#  YOUR ORIGINAL MODEL LOAD (unchanged)
# ══════════════════════════════════════════════════════════════════════════

with open("model.pkl", "rb") as f:
    model = pickle.load(f)

# ══════════════════════════════════════════════════════════════════════════
#  DATABASE SETUP
# ══════════════════════════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name          TEXT DEFAULT '',
                role          TEXT DEFAULT 'user',
                status        TEXT DEFAULT 'active',
                created_at    TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER,
                email      TEXT,
                action     TEXT,
                risk_label TEXT DEFAULT 'low',
                status     TEXT,
                device     TEXT DEFAULT '',
                location   TEXT DEFAULT '',
                timestamp  TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_logs_ts   ON logs(timestamp);
        """)

def ensure_super_admin():
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email=?", (SUPER_ADMIN_EMAIL,)
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO users (email,password_hash,name,role) VALUES (?,?,?,?)",
                (SUPER_ADMIN_EMAIL, hash_pw(SUPER_ADMIN_PASSWORD), SUPER_ADMIN_NAME, "super_admin")
            )
            print(f"[INIT] Super Admin created: {SUPER_ADMIN_EMAIL}")

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_by_email(email):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    return dict(row) if row else None

def get_user_by_id(uid):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return dict(row) if row else None

def save_log(user_id, email, action, risk_label, status, device="", location=""):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO logs (user_id,email,action,risk_label,status,device,location) VALUES (?,?,?,?,?,?,?)",
            (user_id, email, action, risk_label, status, device, location)
        )

# OTP store
_otp_store = {}  # { user_id: {otp, expires} }

def make_jwt(user):
    payload = {
        "user_id": user["id"],
        "email":   user["email"],
        "role":    user["role"],
        "name":    user["name"],
        "exp":     datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRY_HRS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_jwt(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"]), None
    except jwt.ExpiredSignatureError:
        return None, "Token expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"

def get_token_from_request():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("token")

def require_role(*roles):
    token = get_token_from_request()
    if not token:
        return None, (jsonify({"error": "Unauthorized"}), 401)
    payload, err = decode_jwt(token)
    if err:
        return None, (jsonify({"error": err}), 401)
    if payload.get("role") not in roles:
        return None, (jsonify({"error": "Forbidden"}), 403)
    return payload, None

# Init on startup
init_db()
ensure_super_admin()

# ══════════════════════════════════════════════════════════════════════════
#  YOUR ORIGINAL ROUTES (completely unchanged)
# ══════════════════════════════════════════════════════════════════════════

@app.route("/")
def login():
    return render_template("index.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/otp")
def otp():
    return render_template("otp.html")

@app.route("/home")
def home():
    return render_template("home.html")

# ── YOUR ORIGINAL send_email (unchanged) ──────────────────────────────────
def send_email(receiver, otp):
    if not receiver or not otp:
        print("❌ Email Error: Missing receiver or OTP")
        return False
    try:
        msg            = MIMEText(f"Your Smart MFA OTP is: {otp}\n\nThis OTP is valid for 60 seconds.\nDo not share it with anyone.")
        msg["Subject"] = "Your Smart MFA OTP Code"
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = receiver
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo(); server.starttls(); server.ehlo()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg); server.quit()
        print(f"✅ OTP Email sent to {receiver}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Email Error: Authentication failed.")
        return False
    except smtplib.SMTPException as e:
        print("❌ SMTP Error:", e)
        return False
    except Exception as e:
        print("❌ Email Error:", e)
        return False

@app.route("/send-otp", methods=["POST"])
def send_otp():
    data    = request.json
    email   = data.get("email")
    otp     = data.get("otp")
    success = send_email(email, otp)
    return jsonify({"status": "sent" if success else "failed"})

# ── YOUR ORIGINAL encode/predict (unchanged) ──────────────────────────────
def safe_int(value, default=0):
    try: return int(value)
    except: return default

def parse_time(time_str):
    try: return int(str(time_str).split(":")[0])
    except: return 12

def parse_location(location):
    if not location: return 0
    loc = str(location).strip().lower()
    if loc in ["india", "unknown", ""]: return 0
    return 1

def parse_device(device):
    if not device: return 0
    if "mobile" in str(device).strip().lower(): return 1
    return 0

def encode(data):
    device         = parse_device(data.get("device"))
    location       = parse_location(data.get("location"))
    loginCount     = safe_int(data.get("loginCount"),     1)
    failedAttempts = safe_int(data.get("failedAttempts"), 0)
    hour           = parse_time(data.get("time"))
    df = pd.DataFrame(
        [[device, location, loginCount, hour, failedAttempts]],
        columns=["device", "location", "loginCount", "hour", "failedAttempts"]
    )
    print("FINAL INPUT TO MODEL:", df.values.tolist())
    return df

@app.route("/predict", methods=["POST"])
def predict():
    data       = request.json
    print("RECEIVED:", data)
    input_data = encode(data)
    pred       = model.predict(input_data)[0]
    print("PREDICTION:", pred, "(0=safe, 1=risky)")
    return jsonify({"prediction": int(pred)})

# ══════════════════════════════════════════════════════════════════════════
#  NEW — RBAC AUTH API
# ══════════════════════════════════════════════════════════════════════════

@app.route("/api/signup", methods=["POST"])
def api_signup():
    d        = request.get_json() or {}
    email    = d.get("email","").strip().lower()
    password = d.get("password","")
    name     = d.get("name","").strip()
    if not email or not password or not name:
        return jsonify({"error": "All fields required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if get_user_by_email(email):
        return jsonify({"error": "Email already registered"}), 409
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (email,password_hash,name,role) VALUES (?,?,?,?)",
            (email, hash_pw(password), name, "user")
        )
    user = get_user_by_email(email)
    save_log(user["id"], email, "signup", "low", "success")
    return jsonify({"message": "Account created"}), 201

@app.route("/api/login", methods=["POST"])
def api_login():
    d        = request.get_json() or {}
    email    = d.get("email","").strip().lower()
    password = d.get("password","")
    context  = d.get("context", {})

    user = get_user_by_email(email)
    if not user or user["password_hash"] != hash_pw(password):
        if user:
            save_log(user["id"], email, "login_failed", "low", "failed",
                     context.get("device",""), context.get("location",""))
        return jsonify({"error": "Invalid email or password"}), 401

    if user["status"] == "blocked":
        return jsonify({"error": "Account blocked. Contact Super Admin."}), 403

    # Risk prediction using YOUR model
    pred_result = encode(context)
    pred        = int(model.predict(pred_result)[0])
    risk_label  = "high" if pred == 1 else "low"

    save_log(user["id"], email, "login_attempt", risk_label, "pending",
             context.get("device",""), context.get("location",""))

    if pred == 1:
        # Generate OTP and send email
        otp_code = "".join(random.choices(string.digits, k=6))
        _otp_store[user["id"]] = {"otp": otp_code, "expires": time.time() + 60}
        send_email(email, otp_code)
        return jsonify({
            "status":    "otp_required",
            "user_id":   user["id"],
            "email":     user["email"],
            "risk_label": risk_label
        })

    # Safe — issue JWT
    save_log(user["id"], email, "login_success", risk_label, "success",
             context.get("device",""), context.get("location",""))
    token = make_jwt(user)
    resp  = make_response(jsonify({
        "status": "success",
        "token":  token,
        "role":   user["role"],
        "email":  user["email"],
        "name":   user["name"]
    }))
    resp.set_cookie("token", token, httponly=True, samesite="Strict", max_age=28800)
    return resp

@app.route("/api/verify-otp", methods=["POST"])
def api_verify_otp():
    d       = request.get_json() or {}
    user_id = d.get("user_id")
    otp_in  = (d.get("otp") or "").strip()
    if not user_id or not otp_in:
        return jsonify({"error": "user_id and otp required"}), 400

    record = _otp_store.get(int(user_id))
    if not record:
        return jsonify({"error": "OTP not found or expired"}), 400
    if time.time() > record["expires"]:
        del _otp_store[int(user_id)]
        return jsonify({"error": "OTP expired"}), 400
    if record["otp"] != otp_in:
        user = get_user_by_id(int(user_id))
        if user: save_log(user_id, user["email"], "otp_failed", "high", "failed")
        return jsonify({"error": "Wrong OTP ❌"}), 401

    del _otp_store[int(user_id)]
    user = get_user_by_id(int(user_id))
    save_log(user_id, user["email"], "otp_verified", "high", "success")
    token = make_jwt(user)
    resp  = make_response(jsonify({
        "status": "success",
        "token":  token,
        "role":   user["role"],
        "email":  user["email"],
        "name":   user["name"]
    }))
    resp.set_cookie("token", token, httponly=True, samesite="Strict", max_age=28800)
    return resp

@app.route("/api/resend-otp", methods=["POST"])
def api_resend_otp():
    d       = request.get_json() or {}
    user_id = d.get("user_id")
    email   = d.get("email","")
    if not user_id: return jsonify({"error": "user_id required"}), 400
    otp_code = "".join(random.choices(string.digits, k=6))
    _otp_store[int(user_id)] = {"otp": otp_code, "expires": time.time() + 60}
    send_email(email, otp_code)
    return jsonify({"status": "sent"})

@app.route("/api/logout", methods=["POST"])
def api_logout():
    resp = make_response(jsonify({"status": "logged out"}))
    resp.delete_cookie("token")
    return resp

# ══════════════════════════════════════════════════════════════════════════
#  NEW DASHBOARD PAGE ROUTES
# ══════════════════════════════════════════════════════════════════════════

@app.route("/super-admin")
def super_admin_page(): return render_template("super_admin.html")

@app.route("/admin")
def admin_page(): return render_template("admin.html")

@app.route("/user")
def user_page(): return render_template("user.html")

# ══════════════════════════════════════════════════════════════════════════
#  SUPER ADMIN API
# ══════════════════════════════════════════════════════════════════════════

@app.route("/api/super-admin/stats")
def sa_stats():
    payload, err = require_role("super_admin")
    if err: return err
    with get_db() as conn:
        users = [dict(r) for r in conn.execute("SELECT * FROM users").fetchall()]
        logs  = [dict(r) for r in conn.execute("SELECT * FROM logs").fetchall()]
    return jsonify({
        "total_users":    len(users),
        "active_users":   sum(1 for u in users if u["status"]=="active"),
        "blocked_users":  sum(1 for u in users if u["status"]=="blocked"),
        "admin_count":    sum(1 for u in users if u["role"]=="admin"),
        "user_count":     sum(1 for u in users if u["role"]=="user"),
        "success_logins": sum(1 for l in logs if l["status"]=="success"),
        "failed_logins":  sum(1 for l in logs if l["status"]=="failed"),
        "high_risk":      sum(1 for l in logs if l["risk_label"]=="high"),
        "total_events":   len(logs)
    })

@app.route("/api/super-admin/users")
def sa_users():
    payload, err = require_role("super_admin")
    if err: return err
    with get_db() as conn:
        users = [dict(r) for r in conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()]
    for u in users: u.pop("password_hash", None)
    return jsonify({"users": users})

@app.route("/api/super-admin/users/<int:uid>/role", methods=["PUT"])
def sa_set_role(uid):
    payload, err = require_role("super_admin")
    if err: return err
    role = (request.get_json() or {}).get("role")
    if role not in ("super_admin","admin","user"):
        return jsonify({"error": "Invalid role"}), 400
    user = get_user_by_id(uid)
    if user and user["email"] == SUPER_ADMIN_EMAIL:
        return jsonify({"error": "Cannot change Super Admin role"}), 403
    with get_db() as conn:
        conn.execute("UPDATE users SET role=? WHERE id=?", (role, uid))
    return jsonify({"message": "Role updated"})

@app.route("/api/super-admin/users/<int:uid>/status", methods=["PUT"])
def sa_set_status(uid):
    payload, err = require_role("super_admin")
    if err: return err
    status = (request.get_json() or {}).get("status")
    if status not in ("active","blocked"):
        return jsonify({"error": "Invalid status"}), 400
    user = get_user_by_id(uid)
    if user and user["email"] == SUPER_ADMIN_EMAIL:
        return jsonify({"error": "Cannot block Super Admin"}), 403
    with get_db() as conn:
        conn.execute("UPDATE users SET status=? WHERE id=?", (status, uid))
    return jsonify({"message": f"User {status}"})

@app.route("/api/super-admin/users/<int:uid>", methods=["DELETE"])
def sa_delete_user(uid):
    payload, err = require_role("super_admin")
    if err: return err
    user = get_user_by_id(uid)
    if not user: return jsonify({"error": "Not found"}), 404
    if user["email"] == SUPER_ADMIN_EMAIL:
        return jsonify({"error": "Cannot delete Super Admin"}), 403
    with get_db() as conn:
        conn.execute("DELETE FROM logs  WHERE user_id=?", (uid,))
        conn.execute("DELETE FROM users WHERE id=?",      (uid,))
    return jsonify({"message": "User deleted"})

@app.route("/api/super-admin/logs")
def sa_logs():
    payload, err = require_role("super_admin")
    if err: return err
    limit = int(request.args.get("limit", 200))
    with get_db() as conn:
        logs = [dict(r) for r in conn.execute(
            "SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()]
    return jsonify({"logs": logs})

@app.route("/api/super-admin/security")
def sa_security():
    payload, err = require_role("super_admin")
    if err: return err
    with get_db() as conn:
        alerts = [dict(r) for r in conn.execute(
            "SELECT * FROM logs WHERE risk_label='high' ORDER BY timestamp DESC"
        ).fetchall()]
    return jsonify({"alerts": alerts})

@app.route("/api/super-admin/analytics")
def sa_analytics():
    payload, err = require_role("super_admin")
    if err: return err
    trend = []
    with get_db() as conn:
        for i in range(6, -1, -1):
            d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
            row = conn.execute("""
                SELECT
                  SUM(CASE WHEN status='success'    THEN 1 ELSE 0 END),
                  SUM(CASE WHEN status='failed'     THEN 1 ELSE 0 END),
                  SUM(CASE WHEN risk_label='high'   THEN 1 ELSE 0 END)
                FROM logs WHERE DATE(timestamp)=?""", (d,)).fetchone()
            trend.append({"date": d, "success": row[0] or 0, "failed": row[1] or 0, "high_risk": row[2] or 0})
        logs = conn.execute("SELECT risk_label FROM logs").fetchall()
    dist = {"low": 0, "high": 0}
    for l in logs:
        if l[0] == "high": dist["high"] += 1
        else: dist["low"] += 1
    return jsonify({"trend": trend, "risk_distribution": dist})

# ══════════════════════════════════════════════════════════════════════════
#  ADMIN API
# ══════════════════════════════════════════════════════════════════════════

@app.route("/api/admin/stats")
def admin_stats():
    payload, err = require_role("super_admin","admin")
    if err: return err
    with get_db() as conn:
        users = [dict(r) for r in conn.execute("SELECT * FROM users WHERE role != 'super_admin'").fetchall()]
        logs  = [dict(r) for r in conn.execute("SELECT * FROM logs").fetchall()]
    return jsonify({
        "total_users":   len(users),
        "active_users":  sum(1 for u in users if u["status"]=="active"),
        "blocked_users": sum(1 for u in users if u["status"]=="blocked"),
        "success_logins":sum(1 for l in logs if l["status"]=="success"),
        "failed_logins": sum(1 for l in logs if l["status"]=="failed"),
        "high_risk":     sum(1 for l in logs if l["risk_label"]=="high"),
    })

@app.route("/api/admin/users")
def admin_users():
    payload, err = require_role("super_admin","admin")
    if err: return err
    with get_db() as conn:
        users = [dict(r) for r in conn.execute(
            "SELECT * FROM users WHERE role != 'super_admin' ORDER BY created_at DESC"
        ).fetchall()]
    for u in users: u.pop("password_hash", None)
    return jsonify({"users": users})

@app.route("/api/admin/users/<int:uid>/status", methods=["PUT"])
def admin_set_status(uid):
    payload, err = require_role("admin")
    if err: return err
    status = (request.get_json() or {}).get("status")
    if status not in ("active","blocked"):
        return jsonify({"error": "Invalid status"}), 400
    user = get_user_by_id(uid)
    if user and user["role"] == "super_admin":
        return jsonify({"error": "Cannot modify Super Admin"}), 403
    with get_db() as conn:
        conn.execute("UPDATE users SET status=? WHERE id=?", (status, uid))
    return jsonify({"message": f"User {status}"})

@app.route("/api/admin/logs")
def admin_logs():
    payload, err = require_role("super_admin","admin")
    if err: return err
    limit = int(request.args.get("limit", 200))
    with get_db() as conn:
        logs = [dict(r) for r in conn.execute(
            "SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()]
    return jsonify({"logs": logs})

@app.route("/api/admin/analytics")
def admin_analytics():
    payload, err = require_role("super_admin","admin")
    if err: return err
    trend = []
    with get_db() as conn:
        for i in range(6, -1, -1):
            d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
            row = conn.execute("""
                SELECT
                  SUM(CASE WHEN status='success'  THEN 1 ELSE 0 END),
                  SUM(CASE WHEN status='failed'   THEN 1 ELSE 0 END),
                  SUM(CASE WHEN risk_label='high' THEN 1 ELSE 0 END)
                FROM logs WHERE DATE(timestamp)=?""", (d,)).fetchone()
            trend.append({"date": d, "success": row[0] or 0, "failed": row[1] or 0, "high_risk": row[2] or 0})
        logs = conn.execute("SELECT risk_label FROM logs").fetchall()
    dist = {"low": 0, "high": 0}
    for l in logs:
        if l[0] == "high": dist["high"] += 1
        else: dist["low"] += 1
    return jsonify({"trend": trend, "risk_distribution": dist})

# ══════════════════════════════════════════════════════════════════════════
#  USER API
# ══════════════════════════════════════════════════════════════════════════

@app.route("/api/user/profile")
def user_profile():
    token = get_token_from_request()
    if not token: return jsonify({"error": "Unauthorized"}), 401
    payload, err = decode_jwt(token)
    if err: return jsonify({"error": err}), 401
    user = get_user_by_id(payload["user_id"])
    if not user: return jsonify({"error": "Not found"}), 404
    user.pop("password_hash", None)
    return jsonify({"profile": user})

@app.route("/api/user/profile", methods=["PUT"])
def update_profile():
    token = get_token_from_request()
    if not token: return jsonify({"error": "Unauthorized"}), 401
    payload, err = decode_jwt(token)
    if err: return jsonify({"error": err}), 401
    name = ((request.get_json() or {}).get("name") or "").strip()
    if len(name) < 2: return jsonify({"error": "Name too short"}), 400
    with get_db() as conn:
        conn.execute("UPDATE users SET name=? WHERE id=?", (name, payload["user_id"]))
    return jsonify({"message": "Profile updated"})

@app.route("/api/user/logs")
def user_logs():
    token = get_token_from_request()
    if not token: return jsonify({"error": "Unauthorized"}), 401
    payload, err = decode_jwt(token)
    if err: return jsonify({"error": err}), 401
    with get_db() as conn:
        logs = [dict(r) for r in conn.execute(
            "SELECT * FROM logs WHERE user_id=? ORDER BY timestamp DESC LIMIT 50",
            (payload["user_id"],)
        ).fetchall()]
    return jsonify({"logs": logs})

# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\nRBACMatrix AI running")
    print(f"Super Admin: {SUPER_ADMIN_EMAIL} / {SUPER_ADMIN_PASSWORD}")
    print(f"Visit: http://localhost:5000\n")
    app.run(debug=True, host="0.0.0.0", port=5000)

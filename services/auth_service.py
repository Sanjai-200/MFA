"""
services/auth_service.py
JWT auth + OTP via email (same as smart MFA project)
Roles: super_admin, admin, user
"""
import jwt, time, random, string, hashlib, smtplib
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from config import (SECRET_KEY, JWT_EXPIRY_HRS, OTP_EXPIRY_SECS,
                    SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD, SUPER_ADMIN_NAME,
                    EMAIL_SENDER, EMAIL_PASSWORD)
from repository.factory import get_repository
from ml.risk_engine import predict_risk

_otp_store = {}  # { user_id: {otp, expires} }

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _ensure_super_admin():
    """Create hardcoded super admin if not in DB."""
    db = get_repository()
    existing = db.get_user_by_email(SUPER_ADMIN_EMAIL)
    if not existing:
        db.create_user(SUPER_ADMIN_EMAIL, hash_password(SUPER_ADMIN_PASSWORD), SUPER_ADMIN_NAME, "super_admin")
        print(f"[INIT] Super Admin created: {SUPER_ADMIN_EMAIL}")

def signup(email, password, name):
    _ensure_super_admin()
    db = get_repository()
    if db.get_user_by_email(email):
        return None, "Email already registered"
    if len(password) < 6:
        return None, "Password must be at least 6 characters"
    user = db.create_user(email, hash_password(password), name, "user")
    if not user:
        return None, "Signup failed"
    db.save_log(user["id"], email, "signup", 0.0, "success", "", "low")
    return user, None

def login(email, password, context):
    _ensure_super_admin()
    db   = get_repository()
    user = db.get_user_by_email(email)

    if not user or user["password_hash"] != hash_password(password):
        # log failed attempt
        if user:
            db.save_log(user["id"], email, "login_failed", 0.0, "failed", str(context), "low")
        return None, None, "Invalid email or password", 0.0, None

    if user["status"] == "blocked":
        return None, None, "Account blocked. Contact Super Admin.", 0.0, None

    # ── Risk prediction using YOUR model ──────────────────────────────────
    pred, label, score = predict_risk(context)
    db.save_log(user["id"], email, "login_attempt", score, "pending", str(context), label)

    if pred == 1:  # risky → OTP
        otp = _generate_otp(user["id"])
        _send_otp_email(email, otp)
        return user, "otp_required", None, score, otp

    # safe → direct login
    db.save_log(user["id"], email, "login_success", score, "success", str(context), label)
    token = _make_jwt(user)
    return user, "success", None, score, token

def verify_otp(user_id, otp_input):
    record = _otp_store.get(user_id)
    if not record:
        return None, "OTP not found or expired"
    if time.time() > record["expires"]:
        del _otp_store[user_id]; return None, "OTP expired (60 seconds)"
    if record["otp"] != otp_input:
        db = get_repository(); u = db.get_user_by_id(user_id)
        db.save_log(user_id, u["email"] if u else "", "otp_failed", 1.0, "failed", "", "high")
        return None, "Invalid OTP"
    del _otp_store[user_id]
    db = get_repository(); user = db.get_user_by_id(user_id)
    db.save_log(user_id, user["email"], "otp_verified", 1.0, "success", "", "high")
    return _make_jwt(user), None

def decode_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"]), None
    except jwt.ExpiredSignatureError:
        return None, "Token expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"

def _make_jwt(user):
    payload = {
        "user_id": user["id"],
        "email":   user["email"],
        "role":    user["role"],
        "name":    user["name"],
        "exp":     datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HRS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def _generate_otp(user_id):
    otp = "".join(random.choices(string.digits, k=6))
    _otp_store[user_id] = {"otp": otp, "expires": time.time() + OTP_EXPIRY_SECS}
    print(f"[OTP] user_id={user_id} → {otp}")
    return otp

def _send_otp_email(receiver, otp):
    """Exact same email sender as your smart MFA project."""
    if not receiver or not otp:
        print("❌ Email Error: Missing receiver or OTP"); return False
    try:
        msg            = MIMEText(f"Your RBACMatrix OTP is: {otp}\n\nThis OTP is valid for 60 seconds.\nDo not share it with anyone.")
        msg["Subject"] = "Your RBACMatrix OTP Code"
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = receiver
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo(); server.starttls(); server.ehlo()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg); server.quit()
        print(f"✅ OTP sent to {receiver}"); return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Email: Auth failed"); return False
    except Exception as e:
        print(f"❌ Email error: {e}"); return False

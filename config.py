"""
config.py — Central configuration
"""
import os

# ── App ────────────────────────────────────────────────────────────────────
SECRET_KEY     = os.getenv("SECRET_KEY", "rbacmatrix-secret-change-in-prod")
JWT_EXPIRY_HRS = 8

# ── Super Admin (hardcoded — change here to update) ────────────────────────
SUPER_ADMIN_EMAIL    = "sanjay22522g@gmail.com"
SUPER_ADMIN_PASSWORD = "rbac@2006"
SUPER_ADMIN_NAME     = "Super Admin"

# ── Roles ──────────────────────────────────────────────────────────────────
# super_admin → full god-mode access
# admin       → manage users, view logs/analytics
# user        → own profile/activity only
VALID_ROLES = {"super_admin", "admin", "user"}

# ── Database ───────────────────────────────────────────────────────────────
DB_TYPE     = os.getenv("DB_TYPE", "sqlite")
SQLITE_PATH = os.getenv("SQLITE_PATH", "rbacmatrix.db")
POSTGRES_CONFIG = {
    "host":     os.getenv("PG_HOST",     "localhost"),
    "port":     int(os.getenv("PG_PORT", "5432")),
    "database": os.getenv("PG_DB",       "rbacmatrix"),
    "user":     os.getenv("PG_USER",     "postgres"),
    "password": os.getenv("PG_PASSWORD", "password"),
}

# ── ML Model (your model.pkl — device,location,loginCount,hour,failedAttempts) ──
MODEL_PATH     = "model.pkl"
RISK_THRESHOLD = 0.5   # model returns 0=safe 1=risky; treat prediction==1 as high risk

# ── OTP ────────────────────────────────────────────────────────────────────
OTP_EXPIRY_SECS = 60   # 60 seconds like your original project

# ── Email (your Gmail config from smart MFA project) ──────────────────────
EMAIL_SENDER   = "smart7mfa@gmail.com"
EMAIL_PASSWORD = "qbfq ujgg pnpo ikrc"

"""services/admin_service.py — Super Admin + Admin business logic"""
from repository.factory import get_repository
from config import VALID_ROLES, SUPER_ADMIN_EMAIL

def get_all_users():
    users = get_repository().get_all_users()
    for u in users: u.pop("password_hash", None)
    return users

def change_role(user_id, new_role):
    if new_role not in VALID_ROLES:
        return False, f"Invalid role. Must be one of: {VALID_ROLES}"
    # Protect super admin — role cannot be changed
    user = get_repository().get_user_by_id(user_id)
    if user and user["email"] == SUPER_ADMIN_EMAIL:
        return False, "Super Admin role cannot be changed"
    get_repository().update_user_role(user_id, new_role)
    return True, "Role updated"

def change_status(user_id, status):
    if status not in {"active", "blocked"}:
        return False, "Invalid status"
    user = get_repository().get_user_by_id(user_id)
    if user and user["email"] == SUPER_ADMIN_EMAIL:
        return False, "Super Admin cannot be blocked"
    get_repository().update_user_status(user_id, status)
    return True, f"User {status}"

def delete_user(user_id):
    db   = get_repository()
    user = db.get_user_by_id(user_id)
    if not user: return False, "User not found"
    if user["email"] == SUPER_ADMIN_EMAIL:
        return False, "Super Admin cannot be deleted"
    db.delete_user(user_id)
    return True, "User deleted"

def get_stats():
    db    = get_repository()
    users = db.get_all_users()
    return {
        "total_users":    len(users),
        "active_users":   sum(1 for u in users if u["status"] == "active"),
        "blocked_users":  sum(1 for u in users if u["status"] == "blocked"),
        "super_admin_count": sum(1 for u in users if u["role"] == "super_admin"),
        "admin_count":    sum(1 for u in users if u["role"] == "admin"),
        "user_count":     sum(1 for u in users if u["role"] == "user"),
        "success_logins": db.count_logs_by_status("success"),
        "failed_logins":  db.count_logs_by_status("failed"),
        "high_risk":      len(db.get_high_risk_logs()),
        "total_events":   len(db.get_all_logs(limit=9999)),
    }

def get_analytics():
    db    = get_repository()
    trend = db.get_daily_trend(7)
    logs  = db.get_all_logs(9999)
    dist  = {"low": 0, "high": 0}
    for l in logs:
        if l.get("risk_label") == "high": dist["high"] += 1
        else: dist["low"] += 1
    return {"trend": trend, "risk_distribution": dist}

def get_security_alerts():
    return get_repository().get_high_risk_logs()

def get_audit_logs(limit=200):
    return get_repository().get_all_logs(limit)

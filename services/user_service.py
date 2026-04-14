from repository.factory import get_repository

def get_profile(user_id):
    user = get_repository().get_user_by_id(user_id)
    if not user: return None
    user.pop("password_hash", None)
    return user

def get_my_logs(user_id):
    return get_repository().get_logs_by_user(user_id, limit=50)

def update_name(user_id, name):
    if not name or len(name.strip()) < 2:
        return False, "Name too short"
    get_repository().update_user_profile(user_id, name.strip())
    return True, "Profile updated"

from abc import ABC, abstractmethod

class BaseRepository(ABC):
    @abstractmethod
    def create_user(self, email, password_hash, name, role="user"): pass
    @abstractmethod
    def get_user_by_email(self, email): pass
    @abstractmethod
    def get_user_by_id(self, user_id): pass
    @abstractmethod
    def get_all_users(self): pass
    @abstractmethod
    def update_user_role(self, user_id, role): pass
    @abstractmethod
    def update_user_status(self, user_id, status): pass
    @abstractmethod
    def update_user_profile(self, user_id, name): pass
    @abstractmethod
    def delete_user(self, user_id): pass
    @abstractmethod
    def save_log(self, user_id, email, action, risk_score, status, context=""): pass
    @abstractmethod
    def get_all_logs(self, limit=200): pass
    @abstractmethod
    def get_logs_by_user(self, user_id, limit=50): pass
    @abstractmethod
    def get_high_risk_logs(self): pass
    @abstractmethod
    def count_logs_by_status(self, status): pass
    @abstractmethod
    def get_daily_trend(self, days=7): pass

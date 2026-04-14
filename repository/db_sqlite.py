import sqlite3, datetime
from .base import BaseRepository

class SQLiteRepository(BaseRepository):
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._conn() as conn:
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
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER,
                    email       TEXT,
                    action      TEXT,
                    risk_score  REAL DEFAULT 0.0,
                    risk_label  TEXT DEFAULT 'low',
                    status      TEXT,
                    context     TEXT DEFAULT '',
                    timestamp   TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user_id);
                CREATE INDEX IF NOT EXISTS idx_logs_ts   ON logs(timestamp);
            """)

    def create_user(self, email, password_hash, name, role="user"):
        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO users (email,password_hash,name,role) VALUES (?,?,?,?)",
                    (email, password_hash, name, role)
                )
            return self.get_user_by_email(email)
        except sqlite3.IntegrityError:
            return None

    def get_user_by_email(self, email):
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id):
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None

    def get_all_users(self):
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def update_user_role(self, user_id, role):
        with self._conn() as conn:
            conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))

    def update_user_status(self, user_id, status):
        with self._conn() as conn:
            conn.execute("UPDATE users SET status=? WHERE id=?", (status, user_id))

    def update_user_profile(self, user_id, name):
        with self._conn() as conn:
            conn.execute("UPDATE users SET name=? WHERE id=?", (name, user_id))

    def delete_user(self, user_id):
        with self._conn() as conn:
            conn.execute("DELETE FROM logs  WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM users WHERE id=?",      (user_id,))

    def save_log(self, user_id, email, action, risk_score, status, context="", risk_label="low"):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO logs (user_id,email,action,risk_score,risk_label,status,context) VALUES (?,?,?,?,?,?,?)",
                (user_id, email, action, risk_score, risk_label, status, context)
            )

    def get_all_logs(self, limit=200):
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_logs_by_user(self, user_id, limit=50):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM logs WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_high_risk_logs(self):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM logs WHERE risk_label='high' ORDER BY timestamp DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def count_logs_by_status(self, status):
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM logs WHERE status=?", (status,)).fetchone()[0]

    def get_daily_trend(self, days=7):
        result = []
        with self._conn() as conn:
            for i in range(days - 1, -1, -1):
                d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
                row = conn.execute("""
                    SELECT
                        SUM(CASE WHEN status='success'     THEN 1 ELSE 0 END),
                        SUM(CASE WHEN status='failed'      THEN 1 ELSE 0 END),
                        SUM(CASE WHEN risk_label='high'    THEN 1 ELSE 0 END)
                    FROM logs WHERE DATE(timestamp)=?
                """, (d,)).fetchone()
                result.append({"date": d, "success": row[0] or 0, "failed": row[1] or 0, "high_risk": row[2] or 0})
        return result

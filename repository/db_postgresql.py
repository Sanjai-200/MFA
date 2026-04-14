"""PostgreSQL implementation — drop-in replacement for SQLiteRepository"""
import datetime
from .base import BaseRepository

class PostgreSQLRepository(BaseRepository):
    def __init__(self, config):
        try:
            import psycopg2, psycopg2.extras
            self.pg = psycopg2; self.extras = psycopg2.extras
        except ImportError:
            raise ImportError("pip install psycopg2-binary")
        self.config = config
        self._init_db()

    def _conn(self):
        return self.pg.connect(**self.config)

    def _init_db(self):
        with self._conn() as conn:
            with conn.cursor() as c:
                c.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL, name TEXT DEFAULT '',
                        role TEXT DEFAULT 'user', status TEXT DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT NOW());
                    CREATE TABLE IF NOT EXISTS logs (
                        id SERIAL PRIMARY KEY, user_id INTEGER, email TEXT,
                        action TEXT, risk_score REAL DEFAULT 0.0,
                        risk_label TEXT DEFAULT 'low', status TEXT,
                        context TEXT DEFAULT '', timestamp TIMESTAMP DEFAULT NOW());
                """)
            conn.commit()

    def _row(self, c):
        cols = [d[0] for d in c.description]; row = c.fetchone()
        return dict(zip(cols,row)) if row else None

    def _rows(self, c):
        cols = [d[0] for d in c.description]
        return [dict(zip(cols,r)) for r in c.fetchall()]

    def create_user(self, email, password_hash, name, role="user"):
        with self._conn() as conn:
            with conn.cursor() as c:
                try:
                    c.execute("INSERT INTO users (email,password_hash,name,role) VALUES (%s,%s,%s,%s) RETURNING *",(email,password_hash,name,role))
                    r = self._row(c); conn.commit(); return r
                except self.pg.IntegrityError:
                    conn.rollback(); return None

    def get_user_by_email(self, email):
        with self._conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT * FROM users WHERE email=%s",(email,)); return self._row(c)

    def get_user_by_id(self, user_id):
        with self._conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT * FROM users WHERE id=%s",(user_id,)); return self._row(c)

    def get_all_users(self):
        with self._conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT * FROM users ORDER BY created_at DESC"); return self._rows(c)

    def update_user_role(self, user_id, role):
        with self._conn() as conn:
            with conn.cursor() as c: c.execute("UPDATE users SET role=%s WHERE id=%s",(role,user_id))
            conn.commit()

    def update_user_status(self, user_id, status):
        with self._conn() as conn:
            with conn.cursor() as c: c.execute("UPDATE users SET status=%s WHERE id=%s",(status,user_id))
            conn.commit()

    def update_user_profile(self, user_id, name):
        with self._conn() as conn:
            with conn.cursor() as c: c.execute("UPDATE users SET name=%s WHERE id=%s",(name,user_id))
            conn.commit()

    def delete_user(self, user_id):
        with self._conn() as conn:
            with conn.cursor() as c:
                c.execute("DELETE FROM logs WHERE user_id=%s",(user_id,))
                c.execute("DELETE FROM users WHERE id=%s",(user_id,))
            conn.commit()

    def save_log(self, user_id, email, action, risk_score, status, context="", risk_label="low"):
        with self._conn() as conn:
            with conn.cursor() as c:
                c.execute("INSERT INTO logs (user_id,email,action,risk_score,risk_label,status,context) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                          (user_id,email,action,risk_score,risk_label,status,context))
            conn.commit()

    def get_all_logs(self, limit=200):
        with self._conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT %s",(limit,)); return self._rows(c)

    def get_logs_by_user(self, user_id, limit=50):
        with self._conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT * FROM logs WHERE user_id=%s ORDER BY timestamp DESC LIMIT %s",(user_id,limit)); return self._rows(c)

    def get_high_risk_logs(self):
        with self._conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT * FROM logs WHERE risk_label='high' ORDER BY timestamp DESC"); return self._rows(c)

    def count_logs_by_status(self, status):
        with self._conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT COUNT(*) FROM logs WHERE status=%s",(status,)); return c.fetchone()[0]

    def get_daily_trend(self, days=7):
        result = []
        with self._conn() as conn:
            with conn.cursor() as c:
                for i in range(days-1,-1,-1):
                    d = (datetime.date.today()-datetime.timedelta(days=i)).isoformat()
                    c.execute("""SELECT SUM(CASE WHEN status='success' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN risk_label='high' THEN 1 ELSE 0 END)
                        FROM logs WHERE DATE(timestamp)=%s""",(d,))
                    row=c.fetchone()
                    result.append({"date":d,"success":row[0] or 0,"failed":row[1] or 0,"high_risk":row[2] or 0})
        return result

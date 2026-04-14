from config import DB_TYPE, SQLITE_PATH, POSTGRES_CONFIG
_instance = None

def get_repository():
    global _instance
    if _instance: return _instance
    if DB_TYPE == "postgresql":
        from .db_postgresql import PostgreSQLRepository
        _instance = PostgreSQLRepository(POSTGRES_CONFIG)
    else:
        from .db_sqlite import SQLiteRepository
        _instance = SQLiteRepository(SQLITE_PATH)
    return _instance

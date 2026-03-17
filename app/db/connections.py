import sqlite3
from app.db.schema import init_schema
 
DB_FILE = "emails.db"
 
 
def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    """
    Open (or create) the SQLite database.
    Enables WAL mode and row_factory so rows behave like dicts.
    Schema is auto-initialized on first call.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row          # rows accessible as row["column"]
    conn.execute("PRAGMA journal_mode=WAL") # safe concurrent access
    conn.execute("PRAGMA foreign_keys=ON")
    init_schema(conn)
    return conn
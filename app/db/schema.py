import sqlite3
 
CREATE_EMAILS_TABLE = """
    CREATE TABLE IF NOT EXISTS emails (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
 
        -- Agent 1(Monitor) fills these
        message_id      TEXT UNIQUE NOT NULL,
        thread_id       TEXT,
        subject         TEXT,
        sender          TEXT,
        recipient       TEXT,
        date            TEXT,
        body            TEXT,
        snippet         TEXT,
        fetched_at      TEXT NOT NULL,
 
        -- Agent 2 (Classifier) fills these
        category        TEXT,        -- spam | needs_response | ignore | urgent
        confidence      REAL,
        classified_at   TEXT,
 
        -- Agent 3 (Generator) fills these
        draft_reply     TEXT,
        generated_at    TEXT,
 
        -- Agent 4 (Validator) fills these
        validation      TEXT,        -- pass | fail
        validator_notes TEXT,
        validated_at    TEXT,
 
        -- Agent 5 (Draft Saver) fills these
        gmail_draft_id  TEXT,
        saved_at        TEXT
    )
"""
 
def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist. Safe to call multiple times."""
    conn.execute(CREATE_EMAILS_TABLE)
    conn.commit()
 
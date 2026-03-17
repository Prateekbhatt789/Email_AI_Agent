"""
app/db/operations.py
All SQL operations for the emails table.
Each agent imports only the functions it needs.
"""

import sqlite3
from datetime import datetime
from typing import Optional


# ── Agent 1 ───────────────────────────────────────────────────────────────────

def insert_email(conn: sqlite3.Connection, email: dict) -> bool:
    """
    Insert one email. Returns True if inserted, False if already exists.
    Deduplication is handled by UNIQUE constraint on message_id.
    """
    try:
        conn.execute("""
            INSERT INTO emails (
                message_id, thread_id, subject, sender,
                recipient, date, body, snippet, fetched_at
            ) VALUES (
                :message_id, :thread_id, :subject, :sender,
                :recipient, :date, :body, :snippet, :fetched_at
            )
        """, {**email, "fetched_at": datetime.utcnow().isoformat()})
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # duplicate message_id, skip silently


def insert_emails_bulk(conn: sqlite3.Connection, emails: list[dict]) -> tuple[int, int]:
    """
    Insert multiple emails in one transaction.
    Returns (inserted_count, skipped_count).
    """
    inserted, skipped = 0, 0
    fetched_at = datetime.utcnow().isoformat()

    for email in emails:
        try:
            conn.execute("""
                INSERT INTO emails (
                    message_id, thread_id, subject, sender,
                    recipient, date, body, snippet, fetched_at
                ) VALUES (
                    :message_id, :thread_id, :subject, :sender,
                    :recipient, :date, :body, :snippet, :fetched_at
                )
            """, {**email, "fetched_at": fetched_at})
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()
    return inserted, skipped


# ── Agent 2 ───────────────────────────────────────────────────────────────────

def update_classification(
    conn: sqlite3.Connection,
    message_id: str,
    category: str,
    confidence: float,
) -> None:
    """Write classifier results back to the row."""
    conn.execute("""
        UPDATE emails
        SET category       = ?,
            confidence     = ?,
            classified_at  = ?
        WHERE message_id = ?
    """, (category, confidence, datetime.utcnow().isoformat(), message_id))
    conn.commit()


def get_unclassified(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Fetch emails that Agent 2 hasn't processed yet."""
    return conn.execute("""
        SELECT * FROM emails
        WHERE category IS NULL
        ORDER BY id ASC
    """).fetchall()


# ── Agent 3 ───────────────────────────────────────────────────────────────────

def update_draft_reply(
    conn: sqlite3.Connection,
    message_id: str,
    draft_reply: str,
) -> None:
    """Write generated draft reply back to the row."""
    conn.execute("""
        UPDATE emails
        SET draft_reply   = ?,
            generated_at  = ?
        WHERE message_id = ?
    """, (draft_reply, datetime.utcnow().isoformat(), message_id))
    conn.commit()


def get_needs_response(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Fetch emails classified as needs_response but not yet drafted."""
    return conn.execute("""
        SELECT * FROM emails
        WHERE category    = 'needs_response'
          AND draft_reply IS NULL
        ORDER BY id ASC
    """).fetchall()


# ── Agent 4 ───────────────────────────────────────────────────────────────────

def update_validation(
    conn: sqlite3.Connection,
    message_id: str,
    validation: str,
    notes: str,
) -> None:
    """Write validator result back to the row."""
    conn.execute("""
        UPDATE emails
        SET validation      = ?,
            validator_notes = ?,
            validated_at    = ?
        WHERE message_id = ?
    """, (validation, notes, datetime.utcnow().isoformat(), message_id))
    conn.commit()


def get_unvalidated_drafts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Fetch emails with a draft reply that hasn't been validated yet."""
    return conn.execute("""
        SELECT * FROM emails
        WHERE draft_reply IS NOT NULL
          AND validation  IS NULL
        ORDER BY id ASC
    """).fetchall()


# ── Agent 5 ───────────────────────────────────────────────────────────────────

def update_draft_saved(
    conn: sqlite3.Connection,
    message_id: str,
    gmail_draft_id: str,
) -> None:
    """Record the Gmail draft ID after saving."""
    conn.execute("""
        UPDATE emails
        SET gmail_draft_id = ?,
            saved_at       = ?
        WHERE message_id = ?
    """, (gmail_draft_id, datetime.utcnow().isoformat(), message_id))
    conn.commit()


def get_validated_drafts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Fetch emails that passed validation but haven't been saved as drafts yet."""
    return conn.execute("""
        SELECT * FROM emails
        WHERE validation   = 'pass'
          AND gmail_draft_id IS NULL
        ORDER BY id ASC
    """).fetchall()


# ── Shared helpers ─────────────────────────────────────────────────────────────

def get_by_message_id(
    conn: sqlite3.Connection,
    message_id: str,
) -> Optional[sqlite3.Row]:
    """Fetch a single email row by Gmail message ID."""
    return conn.execute(
        "SELECT * FROM emails WHERE message_id = ?", (message_id,)
    ).fetchone()


def read_n_records(
    conn: sqlite3.Connection,
    n: int = 10,
    order: str = "DESC",
) -> list[sqlite3.Row]:
    """Read the latest N records. Used for previews and debugging."""
    return conn.execute(
        f"SELECT * FROM emails ORDER BY id {order} LIMIT ?", (n,)
    ).fetchall()
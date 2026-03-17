"""
app/agents/monitor.py
Agent 1 — Email Monitor

Fetches all unread emails since the last AI-Processed email,
stores new ones in SQLite, then labels them AI-Processed.
"""

import sqlite3
from app.db.operations import insert_emails_bulk, read_n_records
from app.utils.logger import get_logger

log = get_logger(__name__)


def _normalize(email: dict) -> dict:
    return {
        "message_id": email["id"],
        "thread_id":  email.get("thread_id", ""),
        "subject":    email.get("subject", ""),
        "sender":     email.get("sender", ""),
        "recipient":  email.get("recipient", ""),
        "date":       email.get("date", ""),
        "body":       email.get("body", ""),
        "snippet":    email.get("snippet", ""),
    }


def run(service, conn: sqlite3.Connection) -> dict:
    """
    Fetch all new unread emails → store in SQLite → label AI-Processed.

    No max_results cap — fetches every unread email that doesn't yet
    have the AI-Processed label, paginating until Gmail has no more.
    On the next run, those labelled emails are excluded by the Gmail
    query itself, so we naturally pick up only what arrived since last run.

    Returns:
        Summary dict: fetched / inserted / skipped / labelled counts.
    """
    from app.utils.gmail_client import fetch_emails_since_last_processed, ensure_label, apply_label

    log.info("Agent 1 — fetching all emails since last AI-Processed label")

    # ── 1. Fetch (paginated, stops at AI-Processed boundary) ─────────────────
    raw_emails = fetch_emails_since_last_processed(service)

    if not raw_emails:
        log.info("No new emails since last run.")
        return {"fetched": 0, "inserted": 0, "skipped": 0, "labelled": 0}

    log.info(f"Fetched {len(raw_emails)} new emails")

    # ── 2. Normalize ──────────────────────────────────────────────────────────
    emails = [_normalize(e) for e in raw_emails]

    # ── 3. Find truly new IDs (not yet in DB) BEFORE inserting ───────────────
    all_ids = [e["message_id"] for e in emails]
    placeholders = ",".join("?" * len(all_ids))
    existing_rows = conn.execute(
        f"SELECT message_id FROM emails WHERE message_id IN ({placeholders})",
        all_ids
    ).fetchall()
    existing_ids  = {row["message_id"] for row in existing_rows}
    new_ids = [e["message_id"] for e in emails if e["message_id"] not in existing_ids]

    # ── 4. Store ──────────────────────────────────────────────────────────────
    inserted, skipped = insert_emails_bulk(conn, emails)
    log.info(f"Stored {inserted} new | Skipped {skipped} duplicates")

    # ── 5. Label only newly inserted emails — single bulk API call ───────────
    labelled = 0
    if new_ids:
        from app.utils.gmail_client import apply_label_bulk
        label_id = ensure_label(service)
        log.info(f"Labelling {len(new_ids)} emails in one batchModify call")
        try:
            apply_label_bulk(service, new_ids, label_id)
            labelled = len(new_ids)
        except Exception as e:
            log.warning(f"Bulk label failed: {e}")

    return {
        "fetched":  len(raw_emails),
        "inserted": inserted,
        "skipped":  skipped,
        "labelled": labelled,
    }


def preview(conn: sqlite3.Connection, n: int = 10) -> None:
    rows = read_n_records(conn, n=n)
    if not rows:
        print("  (no emails in DB yet)")
        return

    print(f"\n  {'ID':<22} {'From':<32} {'Subject'}")
    print("  " + "─" * 75)
    for row in rows:
        print(
            f"  {row['message_id']:<22} "
            f"{(row['sender'] or '')[:30]:<32} "
            f"{(row['subject'] or '')[:40]}"
        )
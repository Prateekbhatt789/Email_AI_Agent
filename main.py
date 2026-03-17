"""
main.py — project entry point.

    python main.py           # run pipeline once and exit
    python main.py --poll    # run pipeline every 5 minutes (background loop)
"""

import sys
from app.utils.gmail_client import get_gmail_service
from app.db import get_connection
from app.pipeline import run_cycle
from app.agents import monitor
from app.poller import start
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def main():
    poll_mode = "--poll" in sys.argv

    print("=" * 55)
    print("  Email AI Agent")
    print(f"  Mode: {'polling loop (5 min)' if poll_mode else 'one-shot'}")
    print("=" * 55 + "\n")

    conn    = get_connection()
    service = get_gmail_service()

    if poll_mode:
        # ── Continuous polling loop ───────────────────────────
        start(service, conn)

    else:
        # ── Single run ────────────────────────────────────────
        results = run_cycle(service, conn)

        m = results.get("monitor", {})
        print(f"\n  Fetched  : {m.get('fetched', 0)}")
        print(f"  Stored   : {m.get('inserted', 0)} new emails")
        print(f"  Skipped  : {m.get('skipped', 0)} duplicates")
        print(f"  Labelled : {m.get('labelled', 0)} → 'AI-Processed'")

        print("\nLatest emails in DB:")
        monitor.preview(conn, n=10)

    conn.close()


if __name__ == "__main__":
    main()
"""
app/poller.py
Background polling loop — runs the full pipeline every POLL_INTERVAL seconds.

Usage:
    python main.py            # one-shot run
    python main.py --poll     # continuous background loop

Stop with Ctrl+C.
"""

import time
import signal
import sqlite3
from datetime import datetime

from app.pipeline import run_cycle
from app.utils import settings
from app.utils.logger import get_logger

log = get_logger(__name__)

POLL_INTERVAL_MINUTES = settings.POLL_INTERVAL_MINUTES
POLL_INTERVAL = POLL_INTERVAL_MINUTES * 60   # Convert minutes to seconds
_running = True


def _handle_sigint(sig, frame):
    """Graceful shutdown on Ctrl+C."""
    global _running
    log.info("Shutdown signal received — finishing current cycle then stopping...")
    _running = False


def start(service, conn: sqlite3.Connection, interval: int = POLL_INTERVAL) -> None:
    """
    Start the polling loop.

    Args:
        service:  Authenticated Gmail API service
        conn:     Active SQLite connection
        interval: Seconds between each poll cycle (default: 300 = 5 min)
    """
    signal.signal(signal.SIGINT, _handle_sigint)

    log.info(f"Polling loop started — interval: {interval}s ({interval//60}m)")
    log.info("Press Ctrl+C to stop gracefully.\n")

    cycle = 0

    while _running:
        cycle += 1
        now = datetime.now().strftime("%H:%M:%S")
        log.info(f"{'='*45}")
        log.info(f"Cycle #{cycle} at {now}")
        log.info(f"{'='*45}")

        try:
            run_cycle(service, conn)
        except Exception as e:
            # Don't crash the loop on transient errors (network blip, API rate limit)
            log.error(f"Cycle #{cycle} failed: {e}")
            log.info("Continuing — will retry next cycle.")

        if not _running:
            break

        _next = datetime.fromtimestamp(
            time.time() + interval
        ).strftime("%H:%M:%S")
        log.info(f"Cycle #{cycle} done. Next cycle at {_next}\n")

        # Sleep in small chunks so Ctrl+C is responsive
        _interruptible_sleep(interval)

    log.info("Polling loop stopped.")


def _interruptible_sleep(seconds: int) -> None:
    """Sleep in 1-second ticks so Ctrl+C wakes up quickly."""
    for _ in range(seconds):
        if not _running:
            break
        time.sleep(1)
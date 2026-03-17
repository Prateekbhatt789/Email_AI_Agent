"""
app/pipeline.py
Runs one full cycle of the email AI pipeline.

Current state:
    Agent 1 — monitor    LIVE
    Agent 2 — classifier STUB (plug in when ready)
    Agent 3 — generator  STUB
    Agent 4 — validator  STUB
    Agent 5 — draft saver STUB

Each STUB logs a clear message so you know exactly where to add code.
Uncomment the relevant import + call as you build each agent.
"""

import sqlite3
from app.utils.logger import get_logger
from app.agents import monitor

log = get_logger(__name__)


def run_cycle(service, conn: sqlite3.Connection) -> dict:
    """
    Execute one full pipeline cycle.
    Returns a summary dict from each agent that ran.
    """
    results = {}

    # ── Agent 1: Monitor ──────────────────────────────────────────────────────
    log.info("── Agent 1: Monitor ─────────────────────")
    results["monitor"] = monitor.run(service, conn)
    _log_summary("Agent 1", results["monitor"])

    # ── Agent 2: Classifier ───────────────────────────────────────────────────
    # TODO: uncomment when Agent 2 is ready
    # from app.agents import classifier
    # log.info("── Agent 2: Classifier ──────────────────")
    # results["classifier"] = classifier.run(conn)
    # _log_summary("Agent 2", results["classifier"])
    log.info("── Agent 2: Classifier — STUB (not built yet)")

    # ── Agent 3: Generator ────────────────────────────────────────────────────
    # TODO: uncomment when Agent 3 is ready
    # from app.agents import generator
    # log.info("── Agent 3: Generator ───────────────────")
    # results["generator"] = generator.run(conn)
    # _log_summary("Agent 3", results["generator"])
    log.info("── Agent 3: Generator  — STUB (not built yet)")

    # ── Agent 4: Validator ────────────────────────────────────────────────────
    # TODO: uncomment when Agent 4 is ready
    # from app.agents import validator
    # log.info("── Agent 4: Validator ───────────────────")
    # results["validator"] = validator.run(conn)
    # _log_summary("Agent 4", results["validator"])
    log.info("── Agent 4: Validator  — STUB (not built yet)")

    # ── Agent 5: Draft Saver ──────────────────────────────────────────────────
    # TODO: uncomment when Agent 5 is ready
    # from app.agents import draft_saver
    # log.info("── Agent 5: Draft Saver ─────────────────")
    # results["draft_saver"] = draft_saver.run(service, conn)
    # _log_summary("Agent 5", results["draft_saver"])
    log.info("── Agent 5: Draft Saver — STUB (not built yet)")

    return results


def _log_summary(agent: str, summary: dict) -> None:
    for key, val in summary.items():
        log.info(f"   {key}: {val}")
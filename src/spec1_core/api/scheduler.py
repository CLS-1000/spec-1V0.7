# @domain:   machine
# @module:   api_scheduler
# @loc:      gh_main
# @status:   stable
# @depends:  NONE

"""APScheduler setup for SPEC-1.

Schedules run_cycle() on a daily cron at 06:00 America/Los_Angeles.
Checks for .cls_kill file before every run. Optionally runs immediately on
startup when SPEC1_RUN_ON_START=true.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

KILL_FILE = Path(".cls_kill")


def _parse_env_int(env_var: str, default: int) -> int:
    """Read an integer from an environment variable with a descriptive error on bad input."""
    value = os.environ.get(env_var, str(default))
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Invalid value for {env_var}: expected integer, got {value!r}")


def _guarded_cycle() -> None:
    """Run one OSINT cycle unless the kill file is present."""
    if KILL_FILE.exists():
        logger.warning("Kill file present — skipping scheduled cycle run.")
        return

    # Import here to avoid circular imports at module load time
    from spec1_core.app.cycle import run_cycle

    logger.info("Scheduled cycle starting.")
    try:
        stats = run_cycle(verbose=False)
        logger.info(
            "Scheduled cycle complete — signals=%d records=%d",
            stats.get("signals_harvested", 0),
            stats.get("records_stored", 0),
        )
    except Exception as exc:
        logger.error("Scheduled cycle failed: %s", exc)


def _guarded_congressional_cycle() -> None:
    """Run one congressional trade cycle unless the kill file is present."""
    if KILL_FILE.exists():
        logger.warning("Kill file present — skipping congressional cycle run.")
        return

    from spec1_core.congressional.cycle import run_congressional_cycle

    logger.info("Congressional scheduled cycle starting.")
    try:
        stats = run_congressional_cycle(verbose=False)
        logger.info(
            "Congressional cycle complete — trades=%d records=%d",
            stats.get("trades_fetched", 0),
            stats.get("records_stored", 0),
        )
    except Exception as exc:
        logger.error("Congressional cycle failed: %s", exc)


def build_scheduler() -> "BackgroundScheduler":
    """Create and configure the BackgroundScheduler (not yet started)."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    timezone = os.environ.get("SPEC1_TIMEZONE", "America/Los_Angeles")
    hour = _parse_env_int("SPEC1_CRON_HOUR", 6)
    minute = _parse_env_int("SPEC1_CRON_MINUTE", 0)
    congressional_hour = _parse_env_int("SPEC1_CONGRESSIONAL_CRON_HOUR", 7)

    scheduler = BackgroundScheduler(timezone=timezone)
    scheduler.add_job(
        _guarded_cycle,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=timezone),
        id="daily_cycle",
        name="SPEC-1 Daily Intelligence Cycle",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _guarded_congressional_cycle,
        trigger=CronTrigger(hour=congressional_hour, minute=minute, timezone=timezone),
        id="congressional_cycle",
        name="SPEC-1 Congressional Trade Cycle",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    return scheduler


def maybe_run_on_start() -> None:
    """Fire an immediate cycle in a daemon thread if SPEC1_RUN_ON_START=true."""
    if os.environ.get("SPEC1_RUN_ON_START", "").lower() == "true":
        logger.info("SPEC1_RUN_ON_START=true — triggering immediate cycle.")
        t = threading.Thread(target=_guarded_cycle, daemon=True, name="spec1-startup-cycle")
        t.start()

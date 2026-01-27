"""
Scheduler safety helpers: remove-before-add semantics, timezone-aware daily/repeating job wrappers,
and persistent scheduled-job metadata to a local JSON store for restart visibility.
"""
import json
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo
from typing import Optional
import os

logger = logging.getLogger(__name__)

SCHEDULED_JOBS_FILE = os.path.join('data', 'scheduled_jobs.json')


def _ensure_data_dir():
    os.makedirs('data', exist_ok=True)


def _persist_job_meta(name: str, when: time, tz: Optional[ZoneInfo], callback_name: str):
    try:
        _ensure_data_dir()
        meta = {}
        if os.path.exists(SCHEDULED_JOBS_FILE):
            try:
                with open(SCHEDULED_JOBS_FILE, 'r', encoding='utf-8') as f:
                    meta = json.load(f) or {}
            except Exception:
                meta = {}

        meta[name] = {
            'name': name,
            'time': when.strftime('%H:%M:%S'),
            'tz': tz.key if tz else None,
            'callback': callback_name,
            'updated_at': datetime.now().isoformat()
        }

        with open(SCHEDULED_JOBS_FILE, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)
    except Exception as e:
        logger.debug(f"Could not persist scheduled job metadata for {name}: {e}")


def _remove_existing_jobs(application, name: str):
    try:
        existing = application.job_queue.get_jobs_by_name(name)
        if existing:
            for j in existing:
                try:
                    j.schedule_removal()
                except Exception:
                    pass
            logger.info(f"[SCHEDULER] removed existing job(s) with name={name}")
    except Exception as e:
        logger.debug(f"Error removing existing jobs for {name}: {e}")


def run_daily_safe(application, callback, when: time, name: str, tz_name: Optional[str] = None):
    """Schedule a daily job after removing any existing jobs with the same name.

    when: datetime.time (may include tzinfo)
    tz_name: optional timezone string, e.g. 'Asia/Kolkata'
    """
    try:
        tz = ZoneInfo(tz_name) if tz_name else None
        # attach tz to time object if provided
        when_tz = when if when.tzinfo else (when.replace(tzinfo=tz) if tz else when)

        _remove_existing_jobs(application, name)
        application.job_queue.run_daily(callback, time=when_tz, name=name)
        _persist_job_meta(name, when_tz, tz, getattr(callback, '__name__', str(callback)))
        logger.info(f"[SCHEDULER] run_daily_safe scheduled name={name} time={when_tz} tz={tz_name}")
    except Exception as e:
        logger.error(f"run_daily_safe failed for {name}: {e}")


def run_repeating_safe(application, callback, interval_seconds: int, first: Optional[int], name: str):
    try:
        _remove_existing_jobs(application, name)
        application.job_queue.run_repeating(callback, interval=interval_seconds, first=first, name=name)
        _persist_job_meta(name, datetime.now().time(), None, getattr(callback, '__name__', str(callback)))
        logger.info(f"[SCHEDULER] run_repeating_safe scheduled name={name} interval={interval_seconds}s")
    except Exception as e:
        logger.error(f"run_repeating_safe failed for {name}: {e}")


def run_once_safe(application, callback, when_seconds: int, name: str):
    try:
        _remove_existing_jobs(application, name)
        application.job_queue.run_once(callback, when=when_seconds, name=name)
        _persist_job_meta(name, datetime.now().time(), None, getattr(callback, '__name__', str(callback)))
        logger.info(f"[SCHEDULER] run_once_safe scheduled name={name} in={when_seconds}s")
    except Exception as e:
        logger.error(f"run_once_safe failed for {name}: {e}")

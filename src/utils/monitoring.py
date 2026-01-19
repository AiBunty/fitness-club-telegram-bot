"""
Monitoring utilities for ownership-scope checks and alerts.

Provides lightweight checks:
- overdue_reminder_spike: detect many reminders sent recently
- bulk_expiry_candidates: detect large candidate counts for expiry job

Sends alert to `SUPER_ADMIN_USER_ID` when thresholds exceeded.
"""
import logging
from datetime import datetime, timedelta
from src.database.connection import execute_query
from src.config import SUPER_ADMIN_USER_ID

logger = logging.getLogger(__name__)


def check_overdue_reminder_spike(minutes_window: int = 10, threshold: int = 50) -> dict:
    """
    Detects spike in shake reminder activity by counting shake_requests
    updated within the last `minutes_window` that are on credit terms.

    Returns a dict with `count` and `candidates`.
    """
    try:
        since = datetime.utcnow() - timedelta(minutes=minutes_window)
        # Detect available timestamp column (updated_at or created_at)
        col_check_sql = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'shake_requests'
              AND column_name IN ('updated_at','created_at')
        """
        try:
            cols = execute_query(col_check_sql)
            cols = [c.get('column_name') for c in (cols or [])]
        except Exception:
            cols = []

        date_col = 'updated_at' if 'updated_at' in cols else ('created_at' if 'created_at' in cols else None)

        if date_col:
            sql = f"""
                SELECT COUNT(*) AS cnt
                FROM shake_requests
                WHERE payment_terms = 'credit'
                  AND payment_status IN ('pending','user_confirmed')
                  AND {date_col} >= %s
            """
            row = execute_query(sql, (since,), fetch_one=True)
        else:
            # No timestamp column available; count all matching credit shake_requests
            sql = """
                SELECT COUNT(*) AS cnt
                FROM shake_requests
                WHERE payment_terms = 'credit'
                  AND payment_status IN ('pending','user_confirmed')
            """
            row = execute_query(sql, (), fetch_one=True)
        cnt = int(row.get('cnt') if row else 0)
        result = {"count": cnt}
        if cnt >= threshold:
            # Retrieve a small sample for debugging
            if date_col:
                sample = execute_query(
                    f"SELECT shake_request_id, user_id, overdue_reminder_count, {date_col} FROM shake_requests WHERE payment_terms='credit' AND {date_col} >= %s ORDER BY {date_col} DESC LIMIT 50",
                    (since,)
                )
            else:
                sample = execute_query(
                    "SELECT shake_request_id, user_id, overdue_reminder_count FROM shake_requests WHERE payment_terms='credit' ORDER BY shake_request_id DESC LIMIT 50",
                    ()
                )
            result['candidates'] = sample
        return result
    except Exception as e:
        logger.error(f"Error checking overdue reminder spike: {e}")
        return {"count": 0}


def check_bulk_expiry_candidates(grace_period_date, threshold: int = 500) -> dict:
    """
    Counts candidate users that would be affected by expiry logic using given date.

    Returns dict with `count` and sample `candidates` when above threshold.
    """
    try:
        sql = """
            SELECT COUNT(*) AS cnt
            FROM users
            WHERE fee_status IN ('paid', 'active')
              AND fee_expiry_date IS NOT NULL
              AND fee_expiry_date < %s
        """
        row = execute_query(sql, (grace_period_date,), fetch_one=True)
        cnt = int(row.get('cnt') if row else 0)
        result = {"count": cnt}
        if cnt >= threshold:
            sample = execute_query(
                "SELECT user_id, telegram_id, full_name, fee_expiry_date FROM users WHERE fee_status IN ('paid','active') AND fee_expiry_date < %s ORDER BY fee_expiry_date ASC LIMIT 50",
                (grace_period_date,)
            )
            result['candidates'] = sample
        return result
    except Exception as e:
        logger.error(f"Error checking bulk expiry candidates: {e}")
        return {"count": 0}


def send_alert_to_admin(bot, text: str):
    try:
        if SUPER_ADMIN_USER_ID:
            bot.send_message(chat_id=int(SUPER_ADMIN_USER_ID), text=text)
            logger.info("Monitoring alert sent to super admin")
    except Exception as e:
        logger.error(f"Failed to send monitoring alert: {e}")

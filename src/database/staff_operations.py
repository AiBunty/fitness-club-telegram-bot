import logging
from typing import List, Dict
from src.database.connection import execute_query
import os

logger = logging.getLogger(__name__)


def _ensure_table():
    try:
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS staff_members (
                staff_id BIGINT PRIMARY KEY,
                added_by BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    except Exception as e:
        logger.error(f"Failed to ensure staff_members table: {e}")


# Create table only when not explicitly skipping DB migrations (useful for local debugging)
if os.environ.get('SKIP_DB_MIGRATIONS') != '1':
    _ensure_table()


def add_staff(staff_id: int, added_by: int) -> bool:
    try:
        execute_query(
            """
            INSERT INTO staff_members (staff_id, added_by)
            VALUES (%s, %s)
            ON CONFLICT (staff_id) DO NOTHING
            """,
            (staff_id, added_by),
        )
        return True
    except Exception as e:
        logger.error(f"add_staff failed: {e}")
        return False


def remove_staff(staff_id: int) -> bool:
    try:
        count = execute_query(
            "DELETE FROM staff_members WHERE staff_id = %s",
            (staff_id,),
        )
        return count > 0
    except Exception as e:
        logger.error(f"remove_staff failed: {e}")
        return False


def is_staff_id(staff_id: int) -> bool:
    try:
        row = execute_query(
            "SELECT staff_id FROM staff_members WHERE staff_id = %s",
            (staff_id,),
            fetch_one=True,
        )
        return bool(row)
    except Exception as e:
        logger.error(f"is_staff_id failed: {e}")
        return False


def list_staff() -> List[Dict]:
    try:
        rows = execute_query(
            "SELECT staff_id, added_by, created_at FROM staff_members ORDER BY created_at DESC"
        )
        return rows or []
    except Exception as e:
        logger.error(f"list_staff failed: {e}")
        return []

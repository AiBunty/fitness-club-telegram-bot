import logging
from typing import List, Dict
from src.database.connection import execute_query

logger = logging.getLogger(__name__)


def _ensure_table():
    try:
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS admin_members (
                admin_id BIGINT PRIMARY KEY,
                added_by BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    except Exception as e:
        logger.error(f"Failed to ensure admin_members table: {e}")


_ensure_table()


def add_admin(admin_id: int, added_by: int) -> bool:
    try:
        execute_query(
            """
            INSERT IGNORE INTO admin_members (admin_id, added_by)
            VALUES (%s, %s)
            """,
            (admin_id, added_by),
        )
        return True
    except Exception as e:
        logger.error(f"add_admin failed: {e}")
        return False


def remove_admin(admin_id: int) -> bool:
    try:
        count = execute_query(
            "DELETE FROM admin_members WHERE admin_id = %s",
            (admin_id,),
        )
        return count > 0
    except Exception as e:
        logger.error(f"remove_admin failed: {e}")
        return False


def is_admin_id(admin_id: int) -> bool:
    try:
        row = execute_query(
            "SELECT admin_id FROM admin_members WHERE admin_id = %s",
            (admin_id,),
            fetch_one=True,
        )
        return bool(row)
    except Exception as e:
        logger.error(f"is_admin_id failed: {e}")
        return False


def list_admins() -> List[Dict]:
    try:
        rows = execute_query(
            "SELECT admin_id, added_by, created_at FROM admin_members ORDER BY created_at DESC"
        )
        return rows or []
    except Exception as e:
        logger.error(f"list_admins failed: {e}")
        return []
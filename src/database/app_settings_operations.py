"""Database operations for application-wide settings.

Stores arbitrary key/value pairs in the `app_settings` table. Used for
admin-editable welcome message.
"""

import logging
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def _ensure_table():
    try:
        execute_query(TABLE_SQL)
    except Exception as e:
        logger.warning(f"[SETTINGS] Failed to ensure app_settings table: {e}")


def get_app_setting(key: str, default: str = None) -> str:
    """Fetch a setting by key with optional default."""
    _ensure_table()
    try:
        row = execute_query(
            "SELECT value FROM app_settings WHERE key = %s",
            (key,),
            fetch_one=True,
        )
        if row and 'value' in row:
            return row['value']
    except Exception as e:
        logger.warning(f"[SETTINGS] get_app_setting failed for {key}: {e}")
    return default


def set_app_setting(key: str, value: str) -> None:
    """Upsert a setting value."""
    _ensure_table()
    try:
        execute_query(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE
            SET value = EXCLUDED.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )
    except Exception as e:
        logger.warning(f"[SETTINGS] set_app_setting failed for {key}: {e}")
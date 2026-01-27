"""
Reminder Profile Operations (DB is source of truth)
- Get/update user reminder settings (weight, water, meals)
- Enable/disable per reminder
- Set times/intervals
"""

import logging
from datetime import datetime
from src.database.connection import execute_query, USE_LOCAL_DB

logger = logging.getLogger(__name__)


def _row_to_profile(row: dict) -> dict:
    return {
        "user_id": row.get("user_id"),
        "weight_enabled": row.get("weight_enabled", 1),
        "weight_time": row.get("weight_time", "06:00"),
        "water_enabled": row.get("water_enabled", 1),
        "water_interval_minutes": row.get("water_interval_minutes", 60),
        "lunch_enabled": row.get("lunch_enabled", 0),
        "lunch_time": row.get("lunch_time", "13:00"),
        "dinner_enabled": row.get("dinner_enabled", 0),
        "dinner_time": row.get("dinner_time", "20:00"),
        "updated_at": row.get("updated_at"),
        # Legacy compatibility keys for existing handlers
        "water_reminder_enabled": row.get("water_enabled", 1),
        "water_reminder_interval_minutes": row.get("water_interval_minutes", 60),
        "weight_reminder_enabled": row.get("weight_enabled", 1),
        "weight_reminder_time": row.get("weight_time", "06:00"),
        "habits_reminder_enabled": 0,
        "habits_reminder_time": "20:00",
    }


def get_reminder_profile(user_id: int) -> dict:
    """Get reminder profile for user; create defaults if missing."""
    try:
        result = execute_query(
            """
            SELECT user_id, weight_enabled, weight_time, water_enabled, water_interval_minutes,
                   lunch_enabled, lunch_time, dinner_enabled, dinner_time, updated_at
            FROM reminder_profile
            WHERE user_id = %s
            """,
            (user_id,),
            fetch_one=True,
        )
        if result:
            return _row_to_profile(result)

        # Insert default row if not exists
        create_default_profile(user_id)
        result = execute_query(
            """
            SELECT user_id, weight_enabled, weight_time, water_enabled, water_interval_minutes,
                   lunch_enabled, lunch_time, dinner_enabled, dinner_time, updated_at
            FROM reminder_profile
            WHERE user_id = %s
            """,
            (user_id,),
            fetch_one=True,
        )
        if result:
            return _row_to_profile(result)
    except Exception as e:
        logger.error(f"Error getting reminder profile for user {user_id}: {e}")
    return None


def create_default_profile(user_id: int) -> dict:
    try:
        execute_query(
            """
            INSERT INTO reminder_profile (user_id)
            VALUES (%s)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id,),
        )
    except Exception as e:
        logger.error(f"Error creating default reminder_profile for user {user_id}: {e}")
    return None


def toggle_water_reminder(user_id: int, enabled: bool) -> bool:
    try:
        execute_query(
            """
            INSERT INTO reminder_profile (user_id, water_enabled)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                water_enabled = %s,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, enabled, enabled),
        )
        logger.info(f"Water reminder {'enabled' if enabled else 'disabled'} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error toggling water reminder: {e}")
    return False


def set_water_reminder_interval(user_id: int, interval_minutes: int) -> bool:
    try:
        valid_intervals = [15, 30, 60, 120, 180]
        if interval_minutes not in valid_intervals:
            logger.error(f"Invalid interval: {interval_minutes}. Use one of {valid_intervals}")
            return False
        execute_query(
            """
            INSERT INTO reminder_profile (user_id, water_interval_minutes)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                water_interval_minutes = %s,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, interval_minutes, interval_minutes),
        )
        logger.info(f"Water reminder interval set to {interval_minutes}m for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error setting water reminder interval: {e}")
    return False


def toggle_weight_reminder(user_id: int, enabled: bool) -> bool:
    try:
        execute_query(
            """
            INSERT INTO reminder_profile (user_id, weight_enabled)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                weight_enabled = %s,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, enabled, enabled),
        )
        logger.info(f"Weight reminder {'enabled' if enabled else 'disabled'} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error toggling weight reminder: {e}")
    return False


def set_weight_reminder_time(user_id: int, time_str: str) -> bool:
    try:
        try:
            datetime.strptime(time_str, '%H:%M')
        except ValueError:
            logger.error(f"Invalid time format: {time_str}. Use HH:MM format")
            return False
        execute_query(
            """
            INSERT INTO reminder_profile (user_id, weight_time)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                weight_time = %s,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, time_str, time_str),
        )
        logger.info(f"Weight reminder time set to {time_str} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error setting weight reminder time: {e}")
    return False


def toggle_meal_reminder(user_id: int, meal: str, enabled: bool) -> bool:
    if meal not in {"lunch", "dinner"}:
        return False
    col = f"{meal}_enabled"
    try:
        execute_query(
            f"""
            INSERT INTO reminder_profile (user_id, {col})
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                {col} = %s,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, enabled, enabled),
        )
        logger.info(f"{meal.title()} reminder {'enabled' if enabled else 'disabled'} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error toggling {meal} reminder: {e}")
    return False


def set_meal_reminder_time(user_id: int, meal: str, time_str: str) -> bool:
    if meal not in {"lunch", "dinner"}:
        return False
    try:
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            logger.error(f"Invalid time format: {time_str}. Use HH:MM format")
            return False
        col = f"{meal}_time"
        execute_query(
            f"""
            INSERT INTO reminder_profile (user_id, {col})
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                {col} = %s,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, time_str, time_str),
        )
        logger.info(f"{meal.title()} reminder time set to {time_str} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error setting {meal} reminder time: {e}")
    return False


def get_all_profiles() -> list:
    try:
        rows = execute_query(
            """
            SELECT user_id, weight_enabled, weight_time, water_enabled, water_interval_minutes,
                   lunch_enabled, lunch_time, dinner_enabled, dinner_time
            FROM reminder_profile
            """,
            fetch_one=False,
        )
        return [_row_to_profile(row) for row in rows] if rows else []
    except Exception as e:
        logger.error(f"Error getting reminder profiles: {e}")
    return []


def get_users_with_weight_reminders_enabled() -> list:
    try:
        rows = execute_query(
            """
            SELECT user_id, weight_time
            FROM reminder_profile
            WHERE weight_enabled = 1
            """,
            fetch_one=False,
        )
        if rows:
            return [{"user_id": row[0], "reminder_time": row[1]} for row in rows]
    except Exception as e:
        logger.error(f"Error getting weight reminder users: {e}")
    return []


def get_users_with_water_reminders_enabled() -> list:
    try:
        rows = execute_query(
            """
            SELECT user_id, water_interval_minutes
            FROM reminder_profile
            WHERE water_enabled = 1
            """,
            fetch_one=False,
        )
        if rows:
            return [{"user_id": row[0], "interval_minutes": row[1]} for row in rows]
    except Exception as e:
        logger.error(f"Error getting water reminder users: {e}")
    return []


def get_users_with_meal_reminders_enabled(meal: str) -> list:
    if meal not in {"lunch", "dinner"}:
        return []
    try:
        rows = execute_query(
            f"""
            SELECT user_id, {meal}_time
            FROM reminder_profile
            WHERE {meal}_enabled = 1
            """,
            fetch_one=False,
        )
        if rows:
            return [{"user_id": row[0], "reminder_time": row[1]} for row in rows]
    except Exception as e:
        logger.error(f"Error getting {meal} reminder users: {e}")
    return []


# Backward compatibility alias
get_reminder_preferences = get_reminder_profile

"""
Reminder Preferences Operations
- Get/update user reminder settings
- Enable/disable reminders
- Set custom intervals
"""

import logging
from datetime import datetime
from src.database.connection import execute_query

logger = logging.getLogger(__name__)


def get_reminder_preferences(user_id: int) -> dict:
    """Get reminder preferences for a user"""
    try:
        result = execute_query(
            """
            SELECT id, user_id, water_reminder_enabled, water_reminder_interval_minutes,
                   weight_reminder_enabled, weight_reminder_time,
                   habits_reminder_enabled, habits_reminder_time,
                   created_at, updated_at
            FROM reminder_preferences
            WHERE user_id = %s
            """,
            (user_id,),
            fetch_one=True
        )
        
        logger.info(f"Query result for user {user_id}: {result}")
        
        if result:
            # execute_query returns a dict, not a tuple
            return {
                "id": result['id'],
                "user_id": result['user_id'],
                "water_reminder_enabled": result['water_reminder_enabled'],
                "water_reminder_interval_minutes": result['water_reminder_interval_minutes'],
                "weight_reminder_enabled": result['weight_reminder_enabled'],
                "weight_reminder_time": result['weight_reminder_time'],
                "habits_reminder_enabled": result['habits_reminder_enabled'],
                "habits_reminder_time": result['habits_reminder_time'],
                "created_at": result['created_at'],
                "updated_at": result['updated_at'],
            }
        else:
            # Create default preferences for new user
            logger.info(f"No preferences found for user {user_id}, creating defaults")
            return create_default_preferences(user_id)
    except Exception as e:
        logger.error(f"Error getting reminder preferences for user {user_id}: {e}", exc_info=True)
    
    return None


def create_default_preferences(user_id: int) -> dict:
    """Create default reminder preferences for a user"""
    try:
        execute_query(
            """
            INSERT INTO reminder_preferences (user_id)
            VALUES (%s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (user_id,)
        )
        
        # Return the preferences
        return get_reminder_preferences(user_id)
    except Exception as e:
        logger.error(f"Error creating default preferences: {e}")
    
    return None


def toggle_water_reminder(user_id: int, enabled: bool) -> bool:
    """Enable/disable water reminders for user"""
    try:
        execute_query(
            """
            INSERT INTO reminder_preferences (user_id, water_reminder_enabled)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET 
                water_reminder_enabled = %s,
                updated_at = NOW()
            """,
            (user_id, enabled, enabled)
        )
        logger.info(f"Water reminder {'enabled' if enabled else 'disabled'} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error toggling water reminder: {e}")
    
    return False


def set_water_reminder_interval(user_id: int, interval_minutes: int) -> bool:
    """Set custom interval for water reminders (15, 30, 60, 120 minutes)"""
    try:
        # Validate interval
        valid_intervals = [15, 30, 60, 120, 180]
        if interval_minutes not in valid_intervals:
            logger.error(f"Invalid interval: {interval_minutes}. Use one of {valid_intervals}")
            return False
        
        execute_query(
            """
            INSERT INTO reminder_preferences (user_id, water_reminder_interval_minutes)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET 
                water_reminder_interval_minutes = %s,
                updated_at = NOW()
            """,
            (user_id, interval_minutes, interval_minutes)
        )
        logger.info(f"Water reminder interval set to {interval_minutes}m for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error setting water reminder interval: {e}")
    
    return False


def toggle_weight_reminder(user_id: int, enabled: bool) -> bool:
    """Enable/disable weight reminders for user"""
    try:
        execute_query(
            """
            INSERT INTO reminder_preferences (user_id, weight_reminder_enabled)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET 
                weight_reminder_enabled = %s,
                updated_at = NOW()
            """,
            (user_id, enabled, enabled)
        )
        logger.info(f"Weight reminder {'enabled' if enabled else 'disabled'} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error toggling weight reminder: {e}")
    
    return False


def set_weight_reminder_time(user_id: int, time_str: str) -> bool:
    """Set custom time for weight reminders (format: HH:MM, e.g., 06:00)"""
    try:
        # Validate time format
        try:
            datetime.strptime(time_str, '%H:%M')
        except ValueError:
            logger.error(f"Invalid time format: {time_str}. Use HH:MM format")
            return False
        
        execute_query(
            """
            INSERT INTO reminder_preferences (user_id, weight_reminder_time)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET 
                weight_reminder_time = %s,
                updated_at = NOW()
            """,
            (user_id, time_str, time_str)
        )
        logger.info(f"Weight reminder time set to {time_str} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error setting weight reminder time: {e}")
    
    return False


def toggle_habits_reminder(user_id: int, enabled: bool) -> bool:
    """Enable/disable habits reminders for user"""
    try:
        execute_query(
            """
            INSERT INTO reminder_preferences (user_id, habits_reminder_enabled)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET 
                habits_reminder_enabled = %s,
                updated_at = NOW()
            """,
            (user_id, enabled, enabled)
        )
        logger.info(f"Habits reminder {'enabled' if enabled else 'disabled'} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error toggling habits reminder: {e}")
    
    return False


def set_habits_reminder_time(user_id: int, time_str: str) -> bool:
    """Set custom time for habits reminders (format: HH:MM, e.g., 20:00)"""
    try:
        # Validate time format
        try:
            datetime.strptime(time_str, '%H:%M')
        except ValueError:
            logger.error(f"Invalid time format: {time_str}. Use HH:MM format")
            return False
        
        execute_query(
            """
            INSERT INTO reminder_preferences (user_id, habits_reminder_time)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET 
                habits_reminder_time = %s,
                updated_at = NOW()
            """,
            (user_id, time_str, time_str)
        )
        logger.info(f"Habits reminder time set to {time_str} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error setting habits reminder time: {e}")
    
    return False


def get_users_with_water_reminders_enabled() -> list:
    """Get all users who have water reminders enabled"""
    try:
        rows = execute_query(
            """
            SELECT rp.user_id, rp.water_reminder_interval_minutes
            FROM reminder_preferences rp
            JOIN subscriptions s ON rp.user_id = s.user_id
            WHERE rp.water_reminder_enabled = TRUE
            AND s.status = 'active'
            """,
            fetch_one=False
        )
        
        if rows:
            return [
                {
                    "user_id": row[0],
                    "interval_minutes": row[1]
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Error getting water reminder users: {e}")
    
    return []


def get_users_with_weight_reminders_enabled() -> list:
    """Get all users who have weight reminders enabled"""
    try:
        rows = execute_query(
            """
            SELECT rp.user_id, rp.weight_reminder_time
            FROM reminder_preferences rp
            JOIN subscriptions s ON rp.user_id = s.user_id
            WHERE rp.weight_reminder_enabled = TRUE
            AND s.status = 'active'
            """,
            fetch_one=False
        )
        
        if rows:
            return [
                {
                    "user_id": row[0],
                    "reminder_time": row[1]
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Error getting weight reminder users: {e}")
    
    return []


def get_users_with_habits_reminders_enabled() -> list:
    """Get all users who have habits reminders enabled"""
    try:
        rows = execute_query(
            """
            SELECT rp.user_id, rp.habits_reminder_time
            FROM reminder_preferences rp
            JOIN subscriptions s ON rp.user_id = s.user_id
            WHERE rp.habits_reminder_enabled = TRUE
            AND s.status = 'active'
            """,
            fetch_one=False
        )
        
        if rows:
            return [
                {
                    "user_id": row[0],
                    "reminder_time": row[1]
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Error getting habits reminder users: {e}")
    
    return []

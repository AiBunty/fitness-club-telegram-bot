import logging
from src.database.connection import get_db_connection

logger = logging.getLogger(__name__)

# Notification channel types
CHANNEL_TYPES = {
    'telegram': 'Telegram',
    'email': 'Email',
    'sms': 'SMS'
}

def add_notification_channel(user_id, channel_type, channel_address):
    """Add a notification channel for user"""
    try:
        if channel_type not in CHANNEL_TYPES:
            logger.warning(f"Invalid channel type: {channel_type}")
            return False
        
        if not user_id or not channel_address:
            logger.warning(f"Invalid user_id or address")
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if channel already exists
        cursor.execute(
            """
            SELECT channel_id FROM notification_channels 
            WHERE user_id = %s AND channel_type = %s AND channel_address = %s
            """,
            (user_id, channel_type, channel_address)
        )
        
        if cursor.fetchone():
            logger.info(f"Channel already exists for user {user_id}")
            cursor.close()
            conn.close()
            return False
        
        # Insert new channel
        cursor.execute(
            """
            INSERT INTO notification_channels 
            (user_id, channel_type, channel_address, is_active, verified)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, channel_type, channel_address, True, False)
        )
        
        conn.commit()
        logger.info(f"Channel added for user {user_id}: {channel_type}")
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error adding notification channel: {str(e)}")
        return False

def get_user_channels(user_id):
    """Get all notification channels for a user"""
    try:
        if not user_id:
            return []
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT channel_id, user_id, channel_type, channel_address, is_active, verified, created_at
            FROM notification_channels
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,)
        )
        
        columns = ['channel_id', 'user_id', 'channel_type', 'channel_address', 'is_active', 'verified', 'created_at']
        channels = []
        
        for row in cursor.fetchall():
            channels.append(dict(zip(columns, row)))
        
        cursor.close()
        conn.close()
        return channels
        
    except Exception as e:
        logger.error(f"Error fetching channels: {str(e)}")
        return []

def get_active_channels(user_id, channel_type=None):
    """Get active notification channels for a user (optionally filtered by type)"""
    try:
        if not user_id:
            return []
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if channel_type:
            cursor.execute(
                """
                SELECT channel_id, user_id, channel_type, channel_address, is_active, verified, created_at
                FROM notification_channels
                WHERE user_id = %s AND channel_type = %s AND is_active = TRUE
                ORDER BY created_at DESC
                """,
                (user_id, channel_type)
            )
        else:
            cursor.execute(
                """
                SELECT channel_id, user_id, channel_type, channel_address, is_active, verified, created_at
                FROM notification_channels
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
        
        columns = ['channel_id', 'user_id', 'channel_type', 'channel_address', 'is_active', 'verified', 'created_at']
        channels = []
        
        for row in cursor.fetchall():
            channels.append(dict(zip(columns, row)))
        
        cursor.close()
        conn.close()
        return channels
        
    except Exception as e:
        logger.error(f"Error fetching active channels: {str(e)}")
        return []

def verify_channel(channel_id, verification_code):
    """Verify a notification channel with verification code"""
    try:
        if not channel_id or not verification_code:
            logger.warning("Invalid channel_id or verification_code")
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # In production, compare with actual verification code sent to channel
        # For now, mark as verified if code matches simple pattern
        if verification_code == "verify":  # Simplified for demo
            cursor.execute(
                """
                UPDATE notification_channels
                SET verified = TRUE
                WHERE channel_id = %s
                """,
                (channel_id,)
            )
            
            conn.commit()
            logger.info(f"Channel {channel_id} verified")
            cursor.close()
            conn.close()
            return True
        
        cursor.close()
        conn.close()
        return False
        
    except Exception as e:
        logger.error(f"Error verifying channel: {str(e)}")
        return False

def toggle_channel(channel_id, is_active):
    """Enable or disable a notification channel"""
    try:
        if not channel_id or is_active is None:
            logger.warning("Invalid channel_id or is_active")
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            UPDATE notification_channels
            SET is_active = %s
            WHERE channel_id = %s
            """,
            (is_active, channel_id)
        )
        
        conn.commit()
        logger.info(f"Channel {channel_id} toggled to {is_active}")
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error toggling channel: {str(e)}")
        return False

def delete_channel(channel_id):
    """Delete a notification channel"""
    try:
        if not channel_id:
            logger.warning("Invalid channel_id")
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            DELETE FROM notification_channels
            WHERE channel_id = %s
            """,
            (channel_id,)
        )
        
        conn.commit()
        logger.info(f"Channel {channel_id} deleted")
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error deleting channel: {str(e)}")
        return False

def get_notification_preferences(user_id):
    """Get user's notification preferences"""
    try:
        if not user_id:
            return None
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT notification_preferences
            FROM users
            WHERE user_id = %s
            """,
            (user_id,)
        )
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result and result[0]:
            return result[0]  # Should be JSON
        
        # Return default preferences
        return {
            'points_awarded': True,
            'attendance_approved': True,
            'payment_due': True,
            'membership_expired': True,
            'achievement_unlocked': True,
            'challenge_reminder': True,
            'leaderboard_update': True,
            'daily_reminder': False
        }
        
    except Exception as e:
        logger.error(f"Error getting preferences: {str(e)}")
        return None

def update_notification_preferences(user_id, preferences):
    """Update user's notification preferences"""
    try:
        if not user_id or not preferences:
            logger.warning("Invalid user_id or preferences")
            return False
        
        import json
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            UPDATE users
            SET notification_preferences = %s
            WHERE user_id = %s
            """,
            (json.dumps(preferences), user_id)
        )
        
        conn.commit()
        logger.info(f"Preferences updated for user {user_id}")
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        return False

def get_channel_statistics():
    """Get statistics about notification channels"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT 
                channel_type,
                COUNT(*) as total_channels,
                COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_channels,
                COUNT(CASE WHEN verified = TRUE THEN 1 END) as verified_channels
            FROM notification_channels
            GROUP BY channel_type
            """
        )
        
        columns = ['channel_type', 'total_channels', 'active_channels', 'verified_channels']
        stats = {}
        
        for row in cursor.fetchall():
            data = dict(zip(columns, row))
            stats[data['channel_type']] = {
                'total': data['total_channels'],
                'active': data['active_channels'],
                'verified': data['verified_channels']
            }
        
        cursor.close()
        conn.close()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting channel statistics: {str(e)}")
        return {}

def cleanup_inactive_channels(days=30):
    """Delete channels inactive for X days (optional maintenance)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            DELETE FROM notification_channels
            WHERE is_active = FALSE 
            AND created_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
            """,
            (days,)
        )
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        logger.info(f"Deleted {deleted_count} inactive channels older than {days} days")
        cursor.close()
        conn.close()
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error cleaning up channels: {str(e)}")
        return 0

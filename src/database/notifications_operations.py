import logging
from datetime import datetime, timedelta
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

NOTIFICATION_TYPES = {
    'points_awarded': 'Points awarded for activity',
    'attendance_approved': 'Your gym check-in was approved',
    'payment_due': 'Your membership is expiring soon',
    'membership_expired': 'Your membership has expired',
    'achievement_unlocked': 'Achievement unlocked',
    'challenge_reminder': 'Reminder: Challenge in progress',
    'leaderboard_update': 'You moved up in leaderboard',
    'shake_ready': 'Your shake is ready',
    'daily_reminder': 'Daily activity reminder',
}

def create_notification(user_id: int, notification_type: str, title: str = "", 
                       description: str = "", link_data: str = ""):
    """Create a notification for user"""
    try:
        if notification_type not in NOTIFICATION_TYPES:
            notification_type = 'daily_reminder'
        
        if not title:
            title = NOTIFICATION_TYPES.get(notification_type, 'Notification')
        
        query = """
            INSERT INTO notifications (user_id, notification_type, title, description, 
                                     link_data, status, created_at)
            VALUES (%s, %s, %s, %s, %s, 'unread', CURRENT_TIMESTAMP)
            RETURNING *
        """
        result = execute_query(query, (user_id, notification_type, title, description, link_data), 
                              fetch_one=True)
        logger.info(f"Notification created for user {user_id}: {notification_type}")
        return result
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        return None

def get_user_notifications(user_id: int, unread_only: bool = True, limit: int = 20):
    """Get notifications for user"""
    if unread_only:
        query = """
            SELECT * FROM notifications
            WHERE user_id = %s AND status = 'unread'
            ORDER BY created_at DESC
            LIMIT %s
        """
    else:
        query = """
            SELECT * FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
    return execute_query(query, (user_id, limit))

def mark_notification_read(notification_id: int):
    """Mark notification as read"""
    try:
        query = """
            UPDATE notifications
            SET status = 'read', read_at = CURRENT_TIMESTAMP
            WHERE notification_id = %s
        """
        execute_query(query, (notification_id,))
        return True
    except Exception as e:
        logger.error(f"Failed to mark notification as read: {e}")
        return False

def mark_all_notifications_read(user_id: int):
    """Mark all user notifications as read"""
    try:
        query = """
            UPDATE notifications
            SET status = 'read', read_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND status = 'unread'
        """
        execute_query(query, (user_id,))
        return True
    except Exception as e:
        logger.error(f"Failed to mark notifications as read: {e}")
        return False

def delete_notification(notification_id: int):
    """Delete a notification"""
    try:
        query = "DELETE FROM notifications WHERE notification_id = %s"
        execute_query(query, (notification_id,))
        return True
    except Exception as e:
        logger.error(f"Failed to delete notification: {e}")
        return False

def get_unread_count(user_id: int):
    """Get count of unread notifications"""
    query = """
        SELECT COUNT(*) as unread_count
        FROM notifications
        WHERE user_id = %s AND status = 'unread'
    """
    result = execute_query(query, (user_id,), fetch_one=True)
    return result['unread_count'] if result else 0

def send_points_notification(user_id: int, points: int, activity: str):
    """Send points awarded notification"""
    return create_notification(
        user_id,
        'points_awarded',
        title=f"Points awarded! +{points}",
        description=f"You earned {points} points for {activity}",
        link_data="stats"
    )

def send_attendance_approved_notification(user_id: int):
    """Send attendance approval notification"""
    return create_notification(
        user_id,
        'attendance_approved',
        title="Check-in Approved! +50 points",
        description="Your gym attendance was approved by admin",
        link_data="stats"
    )

def send_payment_due_notification(user_id: int, days_remaining: int):
    """Send payment due reminder"""
    return create_notification(
        user_id,
        'payment_due',
        title="Membership expiring soon!",
        description=f"Your membership expires in {days_remaining} days. Please renew.",
        link_data="payment"
    )

def send_membership_expired_notification(user_id: int):
    """Send membership expired notification"""
    return create_notification(
        user_id,
        'membership_expired',
        title="Membership Expired",
        description="Your membership has expired. Please renew to continue.",
        link_data="payment"
    )

def send_achievement_notification(user_id: int, achievement: str, reward_points: int = 0):
    """Send achievement unlocked notification"""
    description = f"Achievement unlocked: {achievement}"
    if reward_points > 0:
        description += f" (+{reward_points} bonus points)"
    
    return create_notification(
        user_id,
        'achievement_unlocked',
        title=f"Achievement: {achievement}",
        description=description,
        link_data="leaderboard"
    )

def send_challenge_reminder(user_id: int, challenge_name: str, days_left: int):
    """Send challenge reminder notification"""
    return create_notification(
        user_id,
        'challenge_reminder',
        title=f"Challenge reminder: {challenge_name}",
        description=f"{challenge_name} ends in {days_left} days",
        link_data="challenges"
    )

def send_leaderboard_notification(user_id: int, new_rank: int, old_rank: int):
    """Send leaderboard movement notification"""
    if new_rank < old_rank:
        description = f"You moved up to rank #{new_rank}!"
    else:
        description = f"You moved to rank #{new_rank}"
    
    return create_notification(
        user_id,
        'leaderboard_update',
        title="Leaderboard Update",
        description=description,
        link_data="leaderboard"
    )

def send_daily_reminder(user_id: int):
    """Send daily activity reminder"""
    return create_notification(
        user_id,
        'daily_reminder',
        title="Daily Activity Reminder",
        description="Log your daily activities to earn points!",
        link_data="menu"
    )

def send_shake_ready_notification(user_id: int, flavor: str):
    """Send shake ready notification"""
    return create_notification(
        user_id,
        'shake_ready',
        title=f"Your shake is ready!",
        description=f"Your {flavor} shake is ready to pick up",
        link_data="shake"
    )

def get_notification_stats():
    """Get notification statistics"""
    query = """
        SELECT 
            COUNT(*) as total_notifications,
            COUNT(CASE WHEN status = 'unread' THEN 1 END) as unread_count,
            COUNT(CASE WHEN status = 'read' THEN 1 END) as read_count,
            COUNT(DISTINCT user_id) as notified_users
        FROM notifications
        WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
    """
    return execute_query(query, fetch_one=True)

def cleanup_old_notifications(days: int = 30):
    """Delete notifications older than specified days"""
    try:
        query = """
            DELETE FROM notifications
            WHERE created_at < CURRENT_TIMESTAMP - %s * INTERVAL '1 day'
            AND status = 'read'
        """
        execute_query(query, (days,))
        logger.info(f"Cleaned up notifications older than {days} days")
        return True
    except Exception as e:
        logger.error(f"Failed to cleanup notifications: {e}")
        return False

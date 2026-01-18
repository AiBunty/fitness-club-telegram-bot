"""
Admin notifications for QR attendance
Queues real-time notifications to all admin members
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Store reference to Telegram Application (set by bot.py)
_telegram_app = None


def set_telegram_app(app):
    """Set the Telegram Application reference (called from bot.py)"""
    global _telegram_app
    _telegram_app = app
    logger.info("Telegram app reference set for admin notifications")


def queue_admin_notification(notification_type: str, **kwargs):
    """
    Queue async notification to all admin members
    
    Args:
        notification_type: Type of notification ('attendance_marked', etc)
        **kwargs: Notification-specific parameters
            - user_id: User who marked attendance
            - distance_m: Distance from gym in meters
            - timestamp: ISO format timestamp
            - reason: Optional failure reason (for overrides)
    """
    if not _telegram_app:
        logger.warning("Telegram app not set, cannot send admin notifications")
        return
    
    try:
        if notification_type == 'attendance_marked':
            _queue_attendance_notification(**kwargs)
        elif notification_type == 'admin_override':
            _queue_override_notification(**kwargs)
        else:
            logger.warning(f"Unknown notification type: {notification_type}")
            
    except Exception as e:
        logger.error(f"Error queuing admin notification: {e}")
        # Never fail the main request due to notification error


def _queue_attendance_notification(user_id: int, distance_m: float, timestamp: str, **kwargs):
    """Queue attendance notification to admins"""
    try:
        from src.database.admin_operations import get_all_admin_ids
        from src.database.user_operations import get_user
        
        # Get user and admin info
        user = get_user(user_id)
        admins = get_all_admin_ids()
        
        if not user or not admins:
            logger.debug("No user or admins found for notification")
            return
        
        user_name = user.get('first_name', 'Unknown')
        
        # Format notification message
        message = (
            f"✅ <b>Attendance Marked</b>\n\n"
            f"👤 User: {user_name}\n"
            f"📍 Distance: {distance_m:.1f}m from gym\n"
            f"⏰ Time: {timestamp}\n\n"
            f"<i>QR-based attendance via geofence</i>"
        )
        
        # Send to each admin asynchronously
        for admin_id in admins:
            try:
                _telegram_app.job_queue.run_once(
                    _send_notification_to_admin,
                    when=0,
                    context={'admin_id': admin_id, 'message': message, 'user_id': user_id}
                )
                logger.debug(f"Queued attendance notification for admin {admin_id}")
            except Exception as e:
                logger.error(f"Error queuing notification to admin {admin_id}: {e}")
                # Continue with other admins
        
    except Exception as e:
        logger.error(f"Error in _queue_attendance_notification: {e}")


def _queue_override_notification(user_id: int, admin_id: int, reason: str, **kwargs):
    """Queue admin override notification to other admins"""
    try:
        from src.database.user_operations import get_user
        from src.database.admin_operations import get_all_admin_ids
        
        # Get user info
        user = get_user(user_id)
        if not user:
            return
        
        user_name = user.get('first_name', 'Unknown')
        admin_name = user.get('first_name', 'Admin')  # TODO: Get admin name from admin_id
        
        message = (
            f"🔓 <b>Attendance Override</b>\n\n"
            f"👤 Member: {user_name}\n"
            f"👨‍💼 Override by: {admin_name}\n"
            f"📝 Reason: {reason}\n\n"
            f"<i>Manual override via /override_attendance</i>"
        )
        
        # Send to all admins except the one who did the override
        admins = get_all_admin_ids()
        for other_admin_id in admins:
            if other_admin_id != admin_id:
                try:
                    _telegram_app.job_queue.run_once(
                        _send_notification_to_admin,
                        when=0,
                        context={'admin_id': other_admin_id, 'message': message, 'user_id': user_id}
                    )
                except Exception as e:
                    logger.error(f"Error queuing override notification to admin {other_admin_id}: {e}")
        
    except Exception as e:
        logger.error(f"Error in _queue_override_notification: {e}")


async def _send_notification_to_admin(context):
    """Send notification message to admin (async callback)"""
    try:
        admin_id = context.job.context['admin_id']
        message = context.job.context['message']
        user_id = context.job.context['user_id']
        
        # Send message with optional override button
        keyboard = []
        if context.job.context.get('show_override'):
            keyboard = [[
                {'text': '🔓 Override', 'callback_data': f'override_attend:{user_id}'}
            ]]
        
        from telegram import InlineKeyboardMarkup
        
        reply_markup = None
        if keyboard:
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=admin_id,
            text=message,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
        logger.debug(f"Notification sent to admin {admin_id}")
        
    except Exception as e:
        logger.error(f"Error sending notification to admin: {e}")

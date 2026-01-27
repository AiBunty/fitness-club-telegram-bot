"""
Notification Operations - Create and retrieve notifications for users
"""
import logging
import json
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

NOTIFICATIONS_FILE = "data/notifications.json"


def ensure_notifications_file():
    """Ensure notifications file exists"""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(NOTIFICATIONS_FILE):
        with open(NOTIFICATIONS_FILE, "w") as f:
            json.dump([], f, indent=2)


def load_notifications():
    """Load all notifications"""
    ensure_notifications_file()
    try:
        with open(NOTIFICATIONS_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_notifications(notifications):
    """Save notifications"""
    ensure_notifications_file()
    with open(NOTIFICATIONS_FILE, "w") as f:
        json.dump(notifications, f, indent=2)


def create_notification(user_id: int, title: str, message: str, 
                       notification_type: str = "general",
                       related_entity_type: str = None,
                       related_entity_id: str = None) -> dict:
    """
    Create a notification record for a user
    
    Args:
        user_id: Telegram user ID
        title: Notification title
        message: Notification message
        notification_type: Type of notification (invoice_generated, payment_received, etc)
        related_entity_type: Type of related entity (invoice, payment, etc)
        related_entity_id: ID of related entity
    
    Returns:
        Notification dict or None
    """
    try:
        notifications = load_notifications()
        
        notification = {
            "id": f"notif_{datetime.now().timestamp()}",
            "user_id": user_id,
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "related_entity_type": related_entity_type,
            "related_entity_id": related_entity_id,
            "is_read": False,
            "created_at": datetime.now().isoformat(),
            "read_at": None
        }
        
        notifications.append(notification)
        save_notifications(notifications)
        
        logger.info(f"[NOTIFICATIONS] created notification_id={notification['id']} user_id={user_id} type={notification_type}")
        
        return notification
    except Exception as e:
        logger.error(f"[NOTIFICATIONS] Error creating notification: {e}")
        return None


def get_user_notifications(user_id: int, limit: int = 50, unread_only: bool = False) -> list:
    """
    Get notifications for a user
    
    Args:
        user_id: Telegram user ID
        limit: Max number of notifications to return
        unread_only: Return only unread notifications
    
    Returns:
        List of notification dicts
    """
    try:
        notifications = load_notifications()
        user_notifs = [n for n in notifications if n.get("user_id") == user_id]
        
        if unread_only:
            user_notifs = [n for n in user_notifs if not n.get("is_read")]
        
        # Sort by most recent first
        user_notifs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return user_notifs[:limit]
    except Exception as e:
        logger.error(f"[NOTIFICATIONS] Error getting user notifications: {e}")
        return []


def mark_notification_read(notification_id: str) -> bool:
    """Mark a notification as read"""
    try:
        notifications = load_notifications()
        
        for notif in notifications:
            if notif.get("id") == notification_id:
                notif["is_read"] = True
                notif["read_at"] = datetime.now().isoformat()
                save_notifications(notifications)
                logger.info(f"[NOTIFICATIONS] marked_read notification_id={notification_id}")
                return True
        
        return False
    except Exception as e:
        logger.error(f"[NOTIFICATIONS] Error marking notification read: {e}")
        return False


def mark_all_notifications_read(user_id: int) -> int:
    """Mark all user notifications as read"""
    try:
        notifications = load_notifications()
        count = 0
        
        for notif in notifications:
            if notif.get("user_id") == user_id and not notif.get("is_read"):
                notif["is_read"] = True
                notif["read_at"] = datetime.now().isoformat()
                count += 1
        
        if count > 0:
            save_notifications(notifications)
            logger.info(f"[NOTIFICATIONS] marked_all_read user_id={user_id} count={count}")
        
        return count
    except Exception as e:
        logger.error(f"[NOTIFICATIONS] Error marking all notifications read: {e}")
        return 0

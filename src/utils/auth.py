import logging
import os
from typing import Set
from src.config import SUPER_ADMIN_PASSWORD, SUPER_ADMIN_USER_ID
from src.database.connection import execute_query
from src.database.role_operations import get_user_role, is_admin as is_admin_db, is_staff as is_staff_db
from src.database.payment_operations import get_user_fee_status
from src.database.user_operations import is_user_approved

logger = logging.getLogger(__name__)

# Admin session management
admin_sessions = {}

# Role IDs via environment (deprecated - kept for backward compatibility)
_raw_admin = os.getenv("ADMIN_IDS", "")
_raw_staff = os.getenv("STAFF_IDS", "")
ADMIN_IDS: Set[int] = {int(x.strip()) for x in _raw_admin.split(",") if x.strip().isdigit()}
STAFF_IDS: Set[int] = {int(x.strip()) for x in _raw_staff.split(",") if x.strip().isdigit()}

def authenticate_admin(user_id: int, password: str) -> bool:
    """Authenticate a user as admin with password."""
    if password != SUPER_ADMIN_PASSWORD:
        logger.warning(f"Failed admin login attempt for user {user_id}")
        return False
    
    admin_sessions[user_id] = True
    logger.info(f"Admin authenticated: {user_id}")
    return True

def is_admin(user_id: int) -> bool:
    """Check if user is an admin by role in database or super admin
    Falls back to ADMIN_IDS environment variable if database is unavailable"""
    try:
        return is_admin_db(user_id) or is_super_admin(user_id)
    except Exception as e:
        # Fall back to environment variable in local/offline mode
        logger.debug(f"Database role check failed ({e}), falling back to ADMIN_IDS env var")
        return user_id in ADMIN_IDS or is_super_admin(user_id)

def is_admin_id(user_id: int) -> bool:
    """Alias for is_admin() for backward compatibility"""
    return is_admin(user_id)

def is_staff(user_id: int) -> bool:
    """Check if user is staff or admin
    Falls back to STAFF_IDS environment variable if database is unavailable"""
    try:
        return is_staff_db(user_id) or is_admin(user_id)
    except Exception as e:
        # Fall back to environment variable in local/offline mode
        logger.debug(f"Database staff check failed ({e}), falling back to STAFF_IDS env var")
        return user_id in STAFF_IDS or is_admin(user_id)

def logout_admin(user_id: int) -> None:
    """Logout admin session."""
    if user_id in admin_sessions:
        del admin_sessions[user_id]
        logger.info(f"Admin logged out: {user_id}")

def is_super_admin(user_id: int) -> bool:
    """Check if user is the super admin."""
    return str(user_id) == str(SUPER_ADMIN_USER_ID)

def whoami_text(user_id: int) -> str:
    """Get user info text with role and name"""
    # Get user details from database
    query = """
        SELECT full_name, telegram_username, role 
        FROM users 
        WHERE user_id = %s
    """
    user_data = execute_query(query, (user_id,), fetch_one=True)
    
    if user_data:
        name = user_data['full_name'] or "Not set"
        username = user_data['telegram_username']
        role_name = user_data['role'] or 'user'
    else:
        name = "Not registered"
        username = None
        role_name = 'user'

    # Ensure super admin is always shown as admin even if not in DB yet
    if is_super_admin(user_id):
        role_name = 'admin'

    role_emoji = {
        'admin': '🛡️ Admin',
        'staff': '🧑‍🍳 Staff',
        'user': '🙋 User'
    }
    role_display = role_emoji.get(role_name, '🙋 User')
    
    # Format message with copyable ID
    message = f"👤 *Your Profile*\n\n"
    message += f"📝 Name: *{name}*\n"
    if username:
        message += f"📱 Username: @{username}\n"
    message += f"🆔 Telegram ID: `{user_id}`\n"
    message += f"👔 Role: {role_display}\n\n"
    message += f"_Tap the ID to copy it_"
    
    return message


def is_fee_paid(user_id: int) -> bool:
    """Check if user has paid membership fee."""
    # Membership fee gating disabled; always allow.
    return True

def check_user_approved(user_id: int) -> bool:
    """Check if user registration is approved. Admins/staff are always approved."""
    # Admins and staff bypass approval check
    if is_admin(user_id) or is_staff(user_id):
        return True
    return is_user_approved(user_id)

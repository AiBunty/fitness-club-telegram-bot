"""
Unified role management using database
Single source of truth for user roles (admin, staff, user)
"""

import logging
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

def get_user_role(user_id: int) -> str:
    """Get user's role from database. Returns 'user', 'staff', or 'admin'"""
    result = execute_query(
        "SELECT role FROM users WHERE user_id = %s",
        (user_id,),
        fetch_one=True
    )
    return result['role'].lower() if result and result.get('role') else 'user'

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return get_user_role(user_id) == 'admin'

def is_staff(user_id: int) -> bool:
    """Check if user is staff or admin"""
    role = get_user_role(user_id)
    return role in ('staff', 'admin')

def is_user(user_id: int) -> bool:
    """Check if user is regular user"""
    return get_user_role(user_id) == 'user'

def set_user_role(user_id: int, role: str) -> bool:
    """Set user role (admin, staff, user)"""
    role = role.lower()
    if role not in ('admin', 'staff', 'user'):
        logger.error(f"Invalid role: {role}")
        return False
    
    try:
        execute_query(
            "UPDATE users SET role = %s WHERE user_id = %s",
            (role, user_id)
        )
        logger.info(f"User {user_id} role set to {role}")
        return True
    except Exception as e:
        logger.error(f"Failed to set role for {user_id}: {e}")
        return False

def add_admin(user_id: int) -> bool:
    """Make user an admin"""
    return set_user_role(user_id, 'admin')

def add_staff(user_id: int) -> bool:
    """Make user staff"""
    return set_user_role(user_id, 'staff')

def remove_admin(user_id: int) -> bool:
    """Remove admin status (set to user)"""
    return set_user_role(user_id, 'user')

def remove_staff(user_id: int) -> bool:
    """Remove staff status (set to user)"""
    return set_user_role(user_id, 'user')

def list_admins() -> list:
    """Get all admins"""
    results = execute_query(
        "SELECT user_id, full_name FROM users WHERE role = 'admin' ORDER BY user_id"
    )
    return results if results else []

def list_staff() -> list:
    """Get all staff members"""
    results = execute_query(
        "SELECT user_id, full_name FROM users WHERE role = 'staff' ORDER BY user_id"
    )
    return results if results else []

def get_role_emoji(role: str) -> str:
    """Get emoji for role"""
    emoji_map = {
        'admin': '🛡️',
        'staff': '🧑‍🍳',
        'user': '🙋'
    }
    return emoji_map.get(role, '🙋')

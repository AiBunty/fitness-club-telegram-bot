import logging
import secrets
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

def user_exists(user_id: int) -> bool:
    result = execute_query(
        "SELECT COUNT(*) as count FROM users WHERE user_id = %s",
        (user_id,),
        fetch_one=True
    )
    return result['count'] > 0 if result else False

def create_user(user_id: int, username: str, full_name: str, 
                phone: str, age: int, initial_weight: float, gender: str = None, profile_pic_url: str = None):
    referral_code = secrets.token_urlsafe(6)[:8].upper()
    query = """
        INSERT INTO users (
            user_id, telegram_username, full_name, phone, age,
            initial_weight, current_weight, gender, profile_pic_url, referral_code, approval_status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'approved')
        RETURNING user_id, full_name, referral_code, profile_pic_url
    """
    result = execute_query(
        query,
        (user_id, username, full_name, phone, age, 
         initial_weight, initial_weight, gender, profile_pic_url, referral_code),
        fetch_one=True
    )
    logger.info(f"User created (auto-approved): {user_id} - {full_name}")
    return result

def get_user(user_id: int):
    query = "SELECT * FROM users WHERE user_id = %s"
    return execute_query(query, (user_id,), fetch_one=True)

# Alias for compatibility
get_user_by_id = get_user

def get_all_users():
    """Get all registered users"""
    query = """
        SELECT user_id, telegram_username, full_name, phone, age, 
               role, created_at, fee_status, is_banned
        FROM users 
        ORDER BY created_at DESC
    """
    return execute_query(query)

def get_all_paid_users():
    """Get all users with paid membership fee status"""
    query = """
        SELECT user_id, telegram_username, full_name, phone, age, 
               role, created_at, fee_status, is_banned
        FROM users 
        WHERE fee_status = 'paid' AND is_banned = FALSE
        ORDER BY created_at DESC
    """
    return execute_query(query)

def get_total_users_count():
    """Get total count of registered users"""
    result = execute_query(
        "SELECT COUNT(*) as count FROM users",
        fetch_one=True
    )
    return result['count'] if result else 0

def delete_user(user_id: int):
    """Delete a user completely from the database"""
    # Delete all related records first to avoid foreign key violations
    # Each delete is independent - if a table doesn't exist, we skip it
    
    tables_to_clean = [
        "subscription_payments",
        "subscription_requests", 
        "subscriptions",
        "attendance",
        "payment_requests",
        "activities",
        "reminder_preferences"
    ]
    
    for table in tables_to_clean:
        try:
            execute_query(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
            logger.debug(f"Deleted records from {table} for user {user_id}")
        except Exception as e:
            # Table might not exist or other issue - log and continue
            logger.debug(f"Skipping {table} for user {user_id}: {e}")
    
    # Finally delete the user
    try:
        query = "DELETE FROM users WHERE user_id = %s RETURNING full_name"
        result = execute_query(query, (user_id,), fetch_one=True)
        if result:
            logger.info(f"User deleted (with all related records): {user_id} - {result['full_name']}")
        return result
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return None

def ban_user(user_id: int, reason: str = None):
    """Ban a user from using the bot"""
    query = """
        UPDATE users 
        SET is_banned = TRUE, ban_reason = %s, banned_at = CURRENT_TIMESTAMP
        WHERE user_id = %s 
        RETURNING full_name
    """
    result = execute_query(query, (reason, user_id), fetch_one=True)
    if result:
        logger.info(f"User banned: {user_id} - {result['full_name']}")
    return result

def unban_user(user_id: int):
    """Unban a user"""
    query = """
        UPDATE users 
        SET is_banned = FALSE, ban_reason = NULL, banned_at = NULL
        WHERE user_id = %s 
        RETURNING full_name
    """
    result = execute_query(query, (user_id,), fetch_one=True)
    if result:
        logger.info(f"User unbanned: {user_id} - {result['full_name']}")
    return result

def is_user_banned(user_id: int) -> bool:
    """Check if a user is banned"""
    result = execute_query(
        "SELECT is_banned FROM users WHERE user_id = %s",
        (user_id,),
        fetch_one=True
    )
    return result['is_banned'] if result else False

def get_user_approval_status(user_id: int) -> str:
    """Get user's approval status"""
    result = execute_query(
        "SELECT approval_status FROM users WHERE user_id = %s",
        (user_id,),
        fetch_one=True
    )
    return result['approval_status'] if result else 'pending'

def is_user_approved(user_id: int) -> bool:
    """Check if a user is approved"""
    status = get_user_approval_status(user_id)
    return status == 'approved'

def approve_user(user_id: int, approved_by: int):
    """Approve a user's registration"""
    query = """
        UPDATE users 
        SET approval_status = 'approved'
        WHERE user_id = %s 
        RETURNING full_name, telegram_username
    """
    result = execute_query(query, (user_id,), fetch_one=True)
    if result:
        logger.info(f"User approved: {user_id} - {result['full_name']} (by admin {approved_by})")
    return result

def reject_user(user_id: int, rejected_by: int, reason: str = None):
    """Reject a user's registration"""
    query = """
        UPDATE users 
        SET approval_status = 'rejected'
        WHERE user_id = %s 
        RETURNING full_name, telegram_username
    """
    result = execute_query(query, (user_id,), fetch_one=True)
    if result:
        logger.info(f"User rejected: {user_id} - {result['full_name']} (by admin {rejected_by})")
    return result

def get_pending_users():
    """Get all users pending approval"""
    query = """
        SELECT user_id, telegram_username, full_name, phone, age, 
               initial_weight, created_at, profile_pic_url
        FROM users 
        WHERE approval_status = 'pending'
        ORDER BY created_at ASC
    """
    return execute_query(query)


def search_users(term: str, limit: int = 10, offset: int = 0):
    """Search users by full_name, telegram_username, or user_id using ILIKE for partial matches.
    
    Returns users with their approval_status so callers can filter or display status.
    Supports fuzzy search with wildcards for names/usernames and exact match for numeric IDs.
    """
    try:
        # Check if term is numeric (user_id search)
        if term.strip().isdigit():
            user_id = int(term.strip())
            query = """
                SELECT user_id, telegram_username, full_name, approval_status
                FROM users
                WHERE user_id = %s
                LIMIT %s OFFSET %s
            """
            rows = execute_query(query, (user_id, limit, offset))
        else:
            # Fuzzy text search with ILIKE and wildcards
            like = f"%{term}%"
            query = """
                SELECT user_id, telegram_username, full_name, approval_status
                FROM users
                WHERE (full_name ILIKE %s OR telegram_username ILIKE %s)
                ORDER BY 
                    CASE 
                        WHEN approval_status = 'approved' THEN 1
                        WHEN approval_status = 'pending' THEN 2
                        ELSE 3
                    END,
                    full_name ASC
                LIMIT %s OFFSET %s
            """
            rows = execute_query(query, (like, like, limit, offset))
        
        logger.info(f"[USER_SEARCH] query='{term}' results={len(rows) if rows else 0}")
        return rows or []
    except Exception as e:
        logger.error(f"Error searching users for term '{term}': {e}")
        return []

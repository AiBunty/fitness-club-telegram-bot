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
    """Create user - MySQL compatible version (no RETURNING clause)
    
    Args:
        user_id: Telegram user ID (64-bit)
        username: Telegram username (for display)
        full_name: User's full name
        phone: Phone number
        age: Age in years
        initial_weight: Initial weight in kg
        gender: Gender (optional)
        profile_pic_url: Telegram file_id for profile picture (optional)
    
    Returns:
        dict: Created user record with user_id, full_name, referral_code, profile_pic_url
    """
    referral_code = secrets.token_urlsafe(6)[:8].upper()
    
    # INSERT query - MySQL compatible (no RETURNING clause - removed for MySQL)
    insert_query = """
        INSERT INTO users (
            user_id, telegram_username, full_name, phone, age,
            initial_weight, current_weight, gender, profile_pic_url, referral_code, approval_status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'approved')
    """
    
    try:
        # Execute INSERT
        execute_query(
            insert_query,
            (user_id, username, full_name, phone, age, 
             initial_weight, initial_weight, gender, profile_pic_url, referral_code),
            fetch_one=False
        )
        
        # Retrieve the created user - MySQL compatible (separate SELECT instead of RETURNING)
        result = execute_query(
            "SELECT user_id, full_name, referral_code, profile_pic_url FROM users WHERE user_id = %s",
            (user_id,),
            fetch_one=True
        )
        
        logger.info(f"User created (auto-approved): {user_id} - {full_name}")
        return result
    except Exception as e:
        logger.error(f"Failed to create user {user_id} ({full_name}): {e}")
        raise

def get_user(user_id: int):
    """Get user by Telegram user ID (64-bit BigInt)
    
    Args:
        user_id: Telegram user ID (can be up to 64-bit integer)
        
    Returns:
        dict: User record or None if not found
    """
    # PostgreSQL BIGINT column handles 64-bit integers natively
    # psycopg2 automatically handles Python int -> PostgreSQL BIGINT conversion
    query = "SELECT * FROM users WHERE user_id = %s"
    return execute_query(query, (user_id,), fetch_one=True)

# Alias for compatibility
get_user_by_id = get_user

def get_all_users():
    """Get all registered users"""
    query = """
        SELECT user_id, telegram_username, full_name, phone, age, 
               role, created_at, fee_status
        FROM users 
        ORDER BY created_at DESC
    """
    return execute_query(query)

def get_all_paid_users():
    """Get all users with paid membership fee status"""
    query = """
        SELECT user_id, telegram_username, full_name, phone, age, 
               role, created_at, fee_status
        FROM users 
        WHERE fee_status = 'paid'
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
    """Delete a user completely from the database with connection pool management
    
    Args:
        user_id: Telegram user ID (64-bit BigInt)
        
    Returns:
        dict: Deleted user record with full_name, or None if not found
    """
    from src.database.connection import get_connection, release_connection

    # Validate user_id is a positive integer
    if not isinstance(user_id, int) or user_id <= 0:
        logger.error(f"Invalid user_id for deletion: {user_id} (type: {type(user_id)})")
        return None
    
    logger.info(f"[DELETE_USER] Starting deletion for user_id={user_id}")
    
    # Delete all related records first to avoid foreign key violations
    tables_to_clean = [
        "subscription_payments",
        "subscription_requests", 
        "subscriptions",
        "attendance",
        "payment_requests",
        "activities",
        "reminder_preferences"
    ]
    
    deleted_counts = {}
    for table in tables_to_clean:
        try:
            # CRITICAL: Use BIGINT casting for 64-bit Telegram IDs
            result = execute_query(f"DELETE FROM {table} WHERE user_id = %s::BIGINT", (user_id,))
            deleted_counts[table] = result if isinstance(result, int) else 0
            logger.debug(f"[DELETE_USER] Deleted {deleted_counts[table]} records from {table} for user {user_id}")
        except Exception as e:
            logger.debug(f"[DELETE_USER] Skipping {table} for user {user_id}: {e}")
    
    # Finally delete the user with connection pool management
    conn = None
    try:
        conn = get_connection()
        if not conn:
            logger.info(f"[DELETE_USER] No DB connection available (local mode); skipping deletion for user {user_id}")
            return None

        with conn.cursor() as cursor:
            # CRITICAL: Use BIGINT casting to ensure proper type matching
            cursor.execute("DELETE FROM users WHERE user_id = %s::BIGINT RETURNING full_name", (user_id,))
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                logger.info(f"[DELETE_USER] User deleted: {user_id} - {result[0]} (cleaned {sum(deleted_counts.values())} related records)")
                return {'full_name': result[0]}
            else:
                logger.warning(f"[DELETE_USER] User {user_id} not found in database")
                return None
                
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        logger.error(f"[DELETE_USER] Error deleting user {user_id}: {e}")
        return None
    finally:
        # Always return connection to pool safely (no-op in local mode)
        if conn:
            try:
                release_connection(conn)
                logger.debug(f"[DELETE_USER] Connection released for user {user_id}")
            except Exception as e:
                logger.error(f"[DELETE_USER] Error releasing connection: {e}")

def ban_user(user_id: int, reason: str = None):
    """Ban a user from using the bot with connection pool management"""
    from src.database.connection import get_connection, release_connection

    conn = None
    try:
        conn = get_connection()
        if not conn:
            logger.info(f"[BAN_USER] No DB connection available (local mode); skipping ban for user {user_id}")
            return None

        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET is_banned = TRUE, ban_reason = %s, banned_at = CURRENT_TIMESTAMP "
                "WHERE user_id = %s::BIGINT RETURNING full_name",
                (reason, user_id)
            )
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                logger.info(f"User banned: {user_id} - {result[0]}")
                return {'full_name': result[0]}
            return None
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        logger.error(f"Error banning user {user_id}: {e}")
        return None
    finally:
        if conn:
            try:
                release_connection(conn)
            except Exception as e:
                logger.error(f"Error releasing connection to pool: {e}")

def unban_user(user_id: int):
    """Unban a user with connection pool management"""
    from src.database.connection import get_connection, release_connection

    conn = None
    try:
        conn = get_connection()
        if not conn:
            logger.info(f"[UNBAN_USER] No DB connection available (local mode); skipping unban for user {user_id}")
            return None

        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET is_banned = FALSE, ban_reason = NULL, banned_at = NULL "
                "WHERE user_id = %s::BIGINT RETURNING full_name",
                (user_id,)
            )
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                logger.info(f"User unbanned: {user_id} - {result[0]}")
                return {'full_name': result[0]}
            return None
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        logger.error(f"Error unbanning user {user_id}: {e}")
        return None
    finally:
        if conn:
            try:
                release_connection(conn)
            except Exception as e:
                logger.error(f"Error releasing connection to pool: {e}")

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
    """Search users by full_name, telegram_username, or user_id using LIKE for partial matches.
    
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
            # Fuzzy text search with LIKE and wildcards (MySQL LIKE is case-insensitive by default)
            like = f"%{term}%"
            query = """
                SELECT user_id, telegram_username, full_name, approval_status
                FROM users
                WHERE (full_name LIKE %s OR telegram_username LIKE %s)
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

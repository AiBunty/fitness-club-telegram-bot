import logging
import secrets
from src.database.connection import execute_query

# Manage Users filters (MySQL is the single source of truth)
MANAGE_USERS_FILTERS = {
    'all',
    'paid',
    'unpaid',
    'active',
    'inactive'
}


def _last_activity_expr(alias: str = 'u') -> str:
    """SQL expression to compute last activity timestamp for a user.

    Uses MySQL-compatible functions and existing tables.
    """
    return (
        "GREATEST("
        "IFNULL({alias}.created_at, '1970-01-01 00:00:00'),"
        "IFNULL((SELECT MAX(created_at) FROM points_transactions pt WHERE pt.user_id = {alias}.user_id), '1970-01-01 00:00:00'),"
        "IFNULL((SELECT MAX(requested_at) FROM attendance_queue aq WHERE aq.user_id = {alias}.user_id), '1970-01-01 00:00:00'),"
        "IFNULL((SELECT MAX(created_at) FROM meal_photos mp WHERE mp.user_id = {alias}.user_id), '1970-01-01 00:00:00'),"
        "IFNULL((SELECT MAX(created_at) FROM daily_logs dl WHERE dl.user_id = {alias}.user_id), '1970-01-01 00:00:00')"
        ")"
    ).format(alias=alias)


def get_manage_users_count(filter_type: str = 'all', inactive_days: int = 90) -> int:
    """Get total count of users for Manage Users list with filters.

    active = paid users only.
    inactive = unpaid users with no activity for inactive_days.
    """
    filter_type = (filter_type or 'all').lower()
    if filter_type not in MANAGE_USERS_FILTERS:
        filter_type = 'all'

    where_clauses = []
    params = []

    paid_clause = "(u.fee_status IN ('paid', 'active'))"
    unpaid_clause = "(u.fee_status NOT IN ('paid', 'active') OR u.fee_status IS NULL)"
    last_activity = _last_activity_expr('u')

    if filter_type in ('paid', 'active'):
        where_clauses.append(paid_clause)
    elif filter_type == 'unpaid':
        where_clauses.append(unpaid_clause)
    elif filter_type == 'inactive':
        where_clauses.append(unpaid_clause)
        where_clauses.append(f"{last_activity} < DATE_SUB(NOW(), INTERVAL %s DAY)")
        params.append(inactive_days)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = f"SELECT COUNT(*) as count FROM users u {where_sql}"
    result = execute_query(query, tuple(params), fetch_one=True)
    return result['count'] if result else 0


def get_manage_users_page(
    filter_type: str = 'all',
    limit: int = 25,
    offset: int = 0,
    inactive_days: int = 90
):
    """Get paginated users for Manage Users list with filters and last activity.

    Returns fields needed for display/export without relying on local files.
    """
    filter_type = (filter_type or 'all').lower()
    if filter_type not in MANAGE_USERS_FILTERS:
        filter_type = 'all'

    where_clauses = []
    params = []

    paid_clause = "(u.fee_status IN ('paid', 'active'))"
    unpaid_clause = "(u.fee_status NOT IN ('paid', 'active') OR u.fee_status IS NULL)"
    last_activity = _last_activity_expr('u')

    if filter_type in ('paid', 'active'):
        where_clauses.append(paid_clause)
    elif filter_type == 'unpaid':
        where_clauses.append(unpaid_clause)
    elif filter_type == 'inactive':
        where_clauses.append(unpaid_clause)
        where_clauses.append(f"{last_activity} < DATE_SUB(NOW(), INTERVAL %s DAY)")
        params.append(inactive_days)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = f"""
        SELECT
            u.user_id,
            u.telegram_username,
            u.full_name,
            u.role,
            u.created_at,
            u.fee_status,
            {last_activity} as last_activity,
            CASE
                WHEN {unpaid_clause} AND {last_activity} < DATE_SUB(NOW(), INTERVAL %s DAY) THEN 1
                ELSE 0
            END as is_inactive
        FROM users u
        {where_sql}
        ORDER BY last_activity DESC, u.created_at DESC
        LIMIT %s OFFSET %s
    """

    params.append(inactive_days)
    params.extend([limit, offset])

    return execute_query(query, tuple(params))

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

    # Filter to only tables that exist in current MySQL schema
    try:
        existing = execute_query(
            "SELECT TABLE_NAME FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN (%s)" %
            ",".join(["%s"] * len(tables_to_clean)),
            tuple(tables_to_clean)
        ) or []
        existing_tables = {row.get('TABLE_NAME') for row in existing}
        tables_to_clean = [t for t in tables_to_clean if t in existing_tables]
    except Exception as e:
        logger.debug(f"[DELETE_USER] Could not validate table list: {e}")
    
    deleted_counts = {}
    for table in tables_to_clean:
        try:
            # MySQL: Remove ::BIGINT casting - MySQL handles auto-conversion
            result = execute_query(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
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
            # MySQL: Remove ::BIGINT casting and RETURNING clause
            cursor.execute("SELECT full_name FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            if result:
                cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
                conn.commit()
                full_name = result['full_name'] if isinstance(result, dict) else result[0]
                logger.info(f"[DELETE_USER] User deleted: {user_id} - {full_name} (cleaned {sum(deleted_counts.values())} related records)")
                return {'full_name': full_name}
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
            # MySQL: Remove ::BIGINT casting and RETURNING clause
            cursor.execute(
                "UPDATE users SET is_banned = TRUE, ban_reason = %s, banned_at = CURRENT_TIMESTAMP "
                "WHERE user_id = %s",
                (reason, user_id)
            )
            # Fetch updated record
            cursor.execute("SELECT full_name FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                full_name = result['full_name'] if isinstance(result, dict) else result[0]
                logger.info(f"User banned: {user_id} - {full_name}")
                return {'full_name': full_name}
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
            # MySQL: Remove ::BIGINT casting and RETURNING clause
            cursor.execute(
                "UPDATE users SET is_banned = FALSE, ban_reason = NULL, banned_at = NULL "
                "WHERE user_id = %s",
                (user_id,)
            )
            # Fetch updated record
            cursor.execute("SELECT full_name FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                full_name = result['full_name'] if isinstance(result, dict) else result[0]
                logger.info(f"User unbanned: {user_id} - {full_name}")
                return {'full_name': full_name}
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
    # MySQL: Remove RETURNING clause, use separate SELECT
    execute_query(
        "UPDATE users SET approval_status = 'approved' WHERE user_id = %s",
        (user_id,)
    )
    result = execute_query(
        "SELECT full_name, telegram_username FROM users WHERE user_id = %s",
        (user_id,),
        fetch_one=True
    )
    if result:
        logger.info(f"User approved: {user_id} - {result['full_name']} (by admin {approved_by})")
    return result

def reject_user(user_id: int, rejected_by: int, reason: str = None):
    """Reject a user's registration"""
    # MySQL: Remove RETURNING clause, use separate SELECT
    execute_query(
        "UPDATE users SET approval_status = 'rejected' WHERE user_id = %s",
        (user_id,)
    )
    result = execute_query(
        "SELECT full_name, telegram_username FROM users WHERE user_id = %s",
        (user_id,),
        fetch_one=True
    )
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

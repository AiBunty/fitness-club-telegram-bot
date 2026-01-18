import logging
from datetime import datetime
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

def get_shake_flavors():
    """Get all available shake flavors"""
    query = "SELECT * FROM shake_flavors WHERE is_active = true ORDER BY flavor_name ASC"
    return execute_query(query)

def request_shake(user_id: int, flavor_id: int, notes: str = ""):
    """Create a shake request"""
    try:
        query = """
            INSERT INTO shake_requests (user_id, flavor_id, notes, status)
            VALUES (%s, %s, %s, 'pending')
            RETURNING *
        """
        result = execute_query(query, (user_id, flavor_id, notes), fetch_one=True)
        logger.info(f"Shake request created for user {user_id}, flavor_id {flavor_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to create shake request: {e}")
        return None

def get_pending_shakes(limit: int = 50):
    """Get all pending shake requests"""
    query = """
        SELECT sr.*, u.full_name, u.telegram_id, u.telegram_username, sf.flavor_name
        FROM shake_requests sr
        JOIN users u ON sr.user_id = u.user_id
        JOIN shake_flavors sf ON sr.flavor_id = sf.flavor_id
        WHERE sr.status = 'pending'
        ORDER BY sr.created_at ASC
        LIMIT %s
    """
    return execute_query(query, (limit,))

def get_today_pending_shakes():
    """Get shake requests pending from today"""
    query = """
        SELECT sr.*, u.full_name, u.telegram_id, u.telegram_username, sf.flavor_name
        FROM shake_requests sr
        JOIN users u ON sr.user_id = u.user_id
        JOIN shake_flavors sf ON sr.flavor_id = sf.flavor_id
        WHERE sr.status = 'pending'
        AND DATE(sr.created_at) = CURRENT_DATE
        ORDER BY sr.created_at ASC
    """
    return execute_query(query)

def approve_shake(shake_id: int, admin_user_id: int):
    """Approve and prepare a shake request"""
    try:
        existing = execute_query(
            "SELECT status, user_id, flavor_id FROM shake_requests WHERE shake_request_id = %s",
            (shake_id,),
            fetch_one=True,
        )

        if not existing:
            return None

        if existing.get('status') != 'pending':
            logger.info(f"Shake {shake_id} already {existing.get('status')}")
            existing['already_processed'] = True
            return existing

        query = """
            UPDATE shake_requests 
            SET status = 'ready', prepared_by = %s, prepared_at = CURRENT_TIMESTAMP
            WHERE shake_request_id = %s AND status = 'pending'
            RETURNING *, 
                (SELECT telegram_id FROM users WHERE user_id = shake_requests.user_id) as telegram_id,
                (SELECT flavor_name FROM shake_flavors WHERE flavor_id = shake_requests.flavor_id) as flavor_name
        """
        result = execute_query(query, (admin_user_id, shake_id), fetch_one=True)
        if result:
            result['already_processed'] = False
            logger.info(f"Shake {shake_id} approved and ready")
        return result
    except Exception as e:
        logger.error(f"Failed to approve shake: {e}")
        return None

def complete_shake(shake_id: int):
    """Mark shake as served/completed"""
    try:
        query = """
            UPDATE shake_requests 
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE shake_request_id = %s
            RETURNING *
        """
        result = execute_query(query, (shake_id,), fetch_one=True)
        logger.info(f"Shake {shake_id} completed")
        return result
    except Exception as e:
        logger.error(f"Failed to complete shake: {e}")
        return None

def cancel_shake(shake_id: int, reason: str = ""):
    """Cancel a shake request"""
    try:
        query = """
            UPDATE shake_requests 
            SET status = 'cancelled', notes = CONCAT(notes, ' | Cancelled: ', %s)
            WHERE shake_request_id = %s
            RETURNING *,
                (SELECT telegram_id FROM users WHERE user_id = shake_requests.user_id) as telegram_id,
                (SELECT flavor_name FROM shake_flavors WHERE flavor_id = shake_requests.flavor_id) as flavor_name
        """
        result = execute_query(query, (reason, shake_id), fetch_one=True)
        logger.info(f"Shake {shake_id} cancelled: {reason}")
        return result
    except Exception as e:
        logger.error(f"Failed to cancel shake: {e}")
        return None

def get_user_shake_count(user_id: int, days: int = 30):
    """Get number of shakes user got in last N days"""
    query = """
        SELECT COUNT(*) as shake_count
        FROM shake_requests
        WHERE user_id = %s
        AND status = 'completed'
        AND completed_at >= CURRENT_TIMESTAMP - %s * INTERVAL '1 day'
    """
    result = execute_query(query, (user_id, days), fetch_one=True)
    return result['shake_count'] if result else 0

def get_flavor_statistics():
    """Get statistics of shake requests by flavor"""
    query = """
        SELECT sf.flavor_name, COUNT(*) as request_count
        FROM shake_requests sr
        JOIN shake_flavors sf ON sr.flavor_id = sf.flavor_id
        WHERE sr.status = 'completed'
        AND sr.completed_at >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY sf.flavor_name
        ORDER BY request_count DESC
    """
    return execute_query(query)

def mark_shake_paid(shake_id: int, admin_id: int):
    """Mark shake order as PAID - approved for immediate preparation"""
    try:
        query = """
            UPDATE shake_requests 
            SET payment_status = 'paid',
                payment_terms = 'paid',
                payment_approved_by = %s,
                status = 'ready'
            WHERE shake_request_id = %s
            RETURNING *, 
                (SELECT flavor_name FROM shake_flavors WHERE flavor_id = shake_requests.flavor_id) as flavor_name
        """
        result = execute_query(query, (admin_id, shake_id), fetch_one=True)
        if result:
            logger.info(f"Shake {shake_id} marked as PAID by admin {admin_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to mark shake as paid: {e}")
        return None


def mark_shake_credit_terms(shake_id: int, admin_id: int):
    """Mark shake order as CREDIT TERMS - approved for preparation with payment follow-up"""
    try:
        from datetime import datetime, timedelta
        due_date = datetime.now() + timedelta(days=7)
        
        query = """
            UPDATE shake_requests 
            SET payment_status = 'pending',
                payment_terms = 'credit',
                payment_due_date = %s,
                payment_approved_by = %s,
                status = 'ready',
                follow_up_reminder_sent = FALSE
            WHERE shake_request_id = %s
            RETURNING *, 
                (SELECT flavor_name FROM shake_flavors WHERE flavor_id = shake_requests.flavor_id) as flavor_name
        """
        result = execute_query(query, (due_date.date(), admin_id, shake_id), fetch_one=True)
        if result:
            logger.info(f"Shake {shake_id} marked as CREDIT TERMS by admin {admin_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to mark shake as credit terms: {e}")
        return None


def mark_user_paid_for_shake(shake_id: int, user_id: int):
    """User confirms payment for credit-based shake order"""
    try:
        query = """
            UPDATE shake_requests 
            SET payment_status = 'user_confirmed',
                follow_up_reminder_sent = TRUE
            WHERE shake_request_id = %s AND user_id = %s
            RETURNING *
        """
        result = execute_query(query, (shake_id, user_id), fetch_one=True)
        if result:
            logger.info(f"User {user_id} confirmed payment for shake {shake_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to mark user paid: {e}")
        return None


def approve_user_payment(shake_id: int, admin_id: int):
    """Admin approves user's payment confirmation for credit-based shake"""
    try:
        query = """
            UPDATE shake_requests 
            SET payment_status = 'paid',
                payment_approved_by = %s
            WHERE shake_request_id = %s
            RETURNING *, user_id
        """
        result = execute_query(query, (admin_id, shake_id), fetch_one=True)
        if result:
            logger.info(f"Admin {admin_id} approved user payment for shake {shake_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to approve user payment: {e}")
        return None


def get_pending_credit_shake_orders():
    """Get all shake orders pending payment with credit terms"""
    try:
        query = """
            SELECT sr.*, u.full_name, u.user_id, sf.flavor_name
            FROM shake_requests sr
            JOIN users u ON sr.user_id = u.user_id
            JOIN shake_flavors sf ON sr.flavor_id = sr.flavor_id
            WHERE sr.payment_terms = 'credit'
            AND sr.payment_status IN ('pending', 'user_confirmed')
            AND sr.payment_due_date <= CURRENT_DATE + INTERVAL '1 day'
            ORDER BY sr.payment_due_date ASC
        """
        return execute_query(query)
    except Exception as e:
        logger.error(f"Failed to get pending credit shake orders: {e}")
        return []
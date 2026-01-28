import logging
from datetime import datetime, timedelta
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

def get_user_fee_status(user_id: int):
    """Get user's payment status"""
    query = "SELECT fee_status, fee_paid_date, fee_expiry_date FROM users WHERE user_id = %s"
    result = execute_query(query, (user_id,), fetch_one=True)
    return result

def is_member_active(user_id: int):
    """Check if user's membership is currently active"""
    status = get_user_fee_status(user_id)
    if not status:
        return False
    
    if status['fee_status'] != 'paid':
        return False
    
    if status['fee_expiry_date'] and status['fee_expiry_date'] < datetime.now().date():
        return False
    
    return True

def record_fee_payment(user_id: int, amount: float, payment_method: str = 'manual', 
                       duration_days: int = 30, notes: str = ""):
    """Record a fee payment for user"""
    try:
        fee_paid_date = datetime.now().date()
        fee_expiry_date = fee_paid_date + timedelta(days=duration_days)
        
        # Record payment transaction - MySQL: Remove RETURNING clause
        query1 = """
            INSERT INTO fee_payments (user_id, amount, payment_method, status, notes)
            VALUES (%s, %s, %s, 'completed', %s)
        """
        execute_query(query1, (user_id, amount, payment_method, notes))
        
        # Update user fee status
        query2 = """
            UPDATE users 
            SET fee_status = 'paid', 
                fee_paid_date = %s,
                fee_expiry_date = %s
            WHERE user_id = %s
        """
        execute_query(query2, (fee_paid_date, fee_expiry_date, user_id))
        
        logger.info(f"Fee payment recorded for user {user_id}: {amount} for {duration_days} days")
        return True
    except Exception as e:
        logger.error(f"Failed to record fee payment: {e}")
        return False

def get_pending_payments():
    """Get all users with unpaid/expired fees"""
    query = """
        SELECT user_id, full_name, telegram_username, fee_status, fee_expiry_date
        FROM users
        WHERE fee_status = 'unpaid' 
           OR (fee_status = 'paid' AND fee_expiry_date < CURRENT_DATE)
        ORDER BY fee_expiry_date ASC NULLS LAST
    """
    return execute_query(query)

def get_payment_history(user_id: int, limit: int = 10):
    """Get user's payment history"""
    query = """
        SELECT * FROM fee_payments
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    return execute_query(query, (user_id, limit))

def get_revenue_stats():
    """Get total revenue and payment statistics"""
    query = """
        SELECT 
            COUNT(*) as total_payments,
            SUM(amount) as total_revenue,
            AVG(amount) as avg_payment,
            COUNT(DISTINCT user_id) as unique_payers,
            MAX(created_at) as last_payment_date
        FROM fee_payments
        WHERE status = 'completed'
    """
    return execute_query(query, fetch_one=True)

def get_monthly_revenue(month: int = None, year: int = None):
    """Get revenue for specific month"""
    if not month:
        month = datetime.now().month
    if not year:
        year = datetime.now().year
    
    query = """
        SELECT 
            SUM(amount) as monthly_revenue,
            COUNT(*) as transaction_count,
            COUNT(DISTINCT user_id) as payers
        FROM fee_payments
        WHERE status = 'completed'
        AND EXTRACT(MONTH FROM created_at) = %s
        AND EXTRACT(YEAR FROM created_at) = %s
    """
    return execute_query(query, (month, year), fetch_one=True)

def get_active_members_count():
    """Get count of active (paid) members"""
    query = """
        SELECT COUNT(*) as active_count
        FROM users
        WHERE fee_status = 'paid'
        AND (fee_expiry_date IS NULL OR fee_expiry_date >= CURRENT_DATE)
    """
    result = execute_query(query, fetch_one=True)
    return result['active_count'] if result else 0

def get_expiring_memberships(days_ahead: int = 7):
    """Get memberships expiring soon"""
    query = """
        SELECT user_id, full_name, telegram_id, fee_expiry_date
        FROM users
        WHERE fee_status = 'paid'
        AND fee_expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + %s * INTERVAL '1 day'
        ORDER BY fee_expiry_date ASC
    """
    return execute_query(query, (days_ahead,))

def extend_membership(user_id: int, duration_days: int = 30, admin_id: int = None):
    """Extend user's membership"""
    try:
        current_expiry = get_user_fee_status(user_id)
        
        if not current_expiry or not current_expiry['fee_expiry_date']:
            new_expiry = datetime.now().date() + timedelta(days=duration_days)
        else:
            new_expiry = current_expiry['fee_expiry_date'] + timedelta(days=duration_days)
        
        query = """
            UPDATE users 
            SET fee_expiry_date = %s
            WHERE user_id = %s
        """
        execute_query(query, (new_expiry, user_id))
        
        logger.info(f"Membership extended for user {user_id} by admin {admin_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to extend membership: {e}")
        return False

def revoke_membership(user_id: int, reason: str = ""):
    """Revoke user's membership"""
    try:
        query = """
            UPDATE users 
            SET fee_status = 'unpaid', fee_expiry_date = NULL
            WHERE user_id = %s
        """
        execute_query(query, (user_id,))
        logger.info(f"Membership revoked for user {user_id}: {reason}")
        return True
    except Exception as e:
        logger.error(f"Failed to revoke membership: {e}")
        return False

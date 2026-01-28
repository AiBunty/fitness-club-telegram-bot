"""
Payment request operations for user subscription management
Handles the workflow: User Request → Admin Approval → Subscription Activation
"""

import logging
from datetime import datetime, timedelta
from src.database.connection import execute_query

logger = logging.getLogger(__name__)

def create_payment_request(user_id: int, amount: float = None, notes: str = "", proof_url: str = None):
    """User submits a payment request"""
    try:
        query1 = """
            INSERT INTO payment_requests (user_id, amount, notes, payment_proof_url, status, requested_at)
            VALUES (%s, %s, %s, %s, 'pending', NOW())
        """
        execute_query(query1, (user_id, amount, notes, proof_url))
        
        # Get the created request
        query2 = "SELECT request_id FROM payment_requests WHERE user_id = %s ORDER BY request_id DESC LIMIT 1"
        result = execute_query(query2, (user_id,), fetch_one=True)
        
        if result:
            logger.info(f"Payment request created for user {user_id}, request_id: {result['request_id']}")
            return result['request_id']
        return None
    except Exception as e:
        logger.error(f"Failed to create payment request: {e}")
        return None

def get_pending_payment_requests():
    """Get all pending payment requests for admin review"""
    query = """
        SELECT 
            pr.request_id,
            pr.user_id,
            u.full_name,
            u.telegram_username,
            pr.amount,
            pr.notes,
            pr.payment_proof_url,
            pr.requested_at,
            pr.status
        FROM payment_requests pr
        JOIN users u ON pr.user_id = u.user_id
        WHERE pr.status = 'pending'
        ORDER BY pr.requested_at ASC
    """
    return execute_query(query)

def get_payment_request_by_id(request_id: int):
    """Get specific payment request details"""
    query = """
        SELECT 
            pr.*,
            u.full_name,
            u.telegram_username
        FROM payment_requests pr
        JOIN users u ON pr.user_id = u.user_id
        WHERE pr.request_id = %s
    """
    return execute_query(query, (request_id,), fetch_one=True)

def approve_payment_request(request_id: int, admin_id: int, amount: float, duration_days: int = 30):
    """Admin approves payment request and activates subscription"""
    try:
        # Get request details
        request = get_payment_request_by_id(request_id)
        if not request:
            logger.error(f"Payment request {request_id} not found")
            return None

        if request['status'] != 'pending':
            request['already_processed'] = True
            return request
        
        user_id = request['user_id']
        fee_paid_date = datetime.now().date()
        fee_expiry_date = fee_paid_date + timedelta(days=duration_days)
        
        # Update payment request status
        query1 = """
            UPDATE payment_requests
            SET status = 'approved',
                reviewed_by = %s,
                reviewed_at = NOW()
            WHERE request_id = %s AND status = 'pending'
        """
        execute_query(query1, (admin_id, request_id))
        
        # Record payment in fee_payments table
        query2 = """
            INSERT INTO fee_payments (user_id, amount, payment_method, status, duration_days, 
                                     notes, approved_by, approved_at)
            VALUES (%s, %s, 'manual', 'completed', %s, %s, %s, NOW())
        """
        execute_query(query2, (user_id, amount, duration_days, 
                               f"Approved by admin (request #{request_id})", admin_id))
        
        # Update user subscription status
        query3 = """
            UPDATE users
            SET fee_status = 'paid',
                fee_paid_date = %s,
                fee_expiry_date = %s
            WHERE user_id = %s
        """
        execute_query(query3, (fee_paid_date, fee_expiry_date, user_id))
        
        logger.info(f"Payment request {request_id} approved by admin {admin_id}")
        logger.info(f"User {user_id} subscription activated until {fee_expiry_date}")
        request['already_processed'] = False
        request['fee_paid_date'] = fee_paid_date
        request['fee_expiry_date'] = fee_expiry_date
        return request
        
    except Exception as e:
        logger.error(f"Failed to approve payment request {request_id}: {e}")
        return None

def approve_payment_request_with_dates(request_id: int, admin_id: int, amount: float, 
                                      start_date, end_date):
    """Admin approves payment request with custom start and end dates"""
    try:
        # Get request details
        request = get_payment_request_by_id(request_id)
        if not request:
            logger.error(f"Payment request {request_id} not found")
            return None

        if request['status'] != 'pending':
            request['already_processed'] = True
            return request
        
        user_id = request['user_id']
        duration_days = (end_date - start_date).days
        
        # Update payment request status
        query1 = """
            UPDATE payment_requests
            SET status = 'approved',
                reviewed_by = %s,
                reviewed_at = NOW()
            WHERE request_id = %s AND status = 'pending'
        """
        execute_query(query1, (admin_id, request_id))
        
        # Record payment in fee_payments table
        query2 = """
            INSERT INTO fee_payments (user_id, amount, payment_method, status, duration_days, 
                                     notes, approved_by, approved_at)
            VALUES (%s, %s, 'manual', 'completed', %s, %s, %s, NOW())
        """
        execute_query(query2, (user_id, amount, duration_days, 
                               f"Approved by admin (request #{request_id}) - Custom dates: {start_date} to {end_date}", 
                               admin_id))
        
        # Update user subscription status with custom dates
        query3 = """
            UPDATE users
            SET fee_status = 'paid',
                fee_paid_date = %s,
                fee_expiry_date = %s
            WHERE user_id = %s
        """
        execute_query(query3, (start_date, end_date, user_id))
        
        logger.info(f"Payment request {request_id} approved by admin {admin_id}")
        logger.info(f"User {user_id} subscription activated: {start_date} to {end_date} ({duration_days} days)")
        request['already_processed'] = False
        request['fee_paid_date'] = start_date
        request['fee_expiry_date'] = end_date
        return request
        
    except Exception as e:
        logger.error(f"Failed to approve payment request {request_id} with custom dates: {e}")
        return None

def reject_payment_request(request_id: int, admin_id: int, reason: str = ""):
    """Admin rejects payment request"""
    try:
        existing = get_payment_request_by_id(request_id)
        if not existing:
            return None

        if existing['status'] != 'pending':
            existing['already_processed'] = True
            return existing

        query1 = """
            UPDATE payment_requests
            SET status = 'rejected',
                reviewed_by = %s,
                reviewed_at = NOW(),
                rejection_reason = %s
            WHERE request_id = %s AND status = 'pending'
        """
        execute_query(query1, (admin_id, reason, request_id))
        
        # Get the updated request
        query2 = "SELECT request_id, user_id, status FROM payment_requests WHERE request_id = %s"
        result = execute_query(query2, (request_id,), fetch_one=True)
        if result:
            result['already_processed'] = False
            logger.info(f"Payment request {request_id} rejected by admin {admin_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to reject payment request {request_id}: {e}")
        return None

def get_user_payment_requests(user_id: int, limit: int = 10):
    """Get user's payment request history"""
    query = """
        SELECT * FROM payment_requests
        WHERE user_id = %s
        ORDER BY requested_at DESC
        LIMIT %s
    """
    return execute_query(query, (user_id, limit))

def has_pending_payment_request(user_id: int):
    """Check if user already has a pending payment request"""
    query = """
        SELECT COUNT(*) as count FROM payment_requests
        WHERE user_id = %s AND status = 'pending'
    """
    result = execute_query(query, (user_id,), fetch_one=True)
    return result['count'] > 0 if result else False

"""
Subscription Management Operations
- Handle gym subscriptions and membership plans
- Track subscription status, expiry, and renewals
"""

import logging
from datetime import datetime, timedelta
from src.database.connection import execute_query
from src.database.ar_operations import (
    create_receivable,
    create_transactions,
    get_receivable_by_source,
    update_receivable_status,
)

def create_pending_payment(user_id: int, request_id: int, amount: float, payment_method: str, reference: str = None, screenshot_file_id: str = None) -> dict:
    """Create a pending payment record (evidence) without mirroring to AR ledger."""
    try:
        result = execute_query(
            """
            INSERT INTO subscription_payments (user_id, request_id, amount, payment_method, reference, screenshot_file_id, status, paid_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending', NULL)
            RETURNING id, user_id, amount, payment_method, status
            """,
            (user_id, request_id, amount, payment_method, reference, screenshot_file_id),
            fetch_one=True,
        )
        if result:
            logger.info(f"Pending payment created: User {user_id}, Request {request_id}, Amount {amount}, Method {payment_method}")
            return result
    except Exception as e:
        logger.error(f"Error creating pending payment: {e}")
    return None


def get_pending_payment(request_id: int, payment_method: str) -> dict:
    """Fetch a pending payment record for a request and payment method."""
    try:
        row = execute_query(
            "SELECT id, user_id, amount, payment_method, reference, screenshot_file_id FROM subscription_payments WHERE request_id = %s AND payment_method = %s AND status = 'pending' LIMIT 1",
            (request_id, payment_method),
            fetch_one=True,
        )
        return row
    except Exception as e:
        logger.error(f"Error fetching pending payment: {e}")
    return None


def finalize_pending_payment(payment_id: int, reference: str = None, screenshot_file_id: str = None) -> dict:
    """Mark a pending payment as completed and mirror into AR ledger."""
    try:
        # Update the pending payment to completed and set paid_at
        updated = execute_query(
            """
            UPDATE subscription_payments
            SET status = 'completed', reference = COALESCE(%s, reference), screenshot_file_id = COALESCE(%s, screenshot_file_id), paid_at = NOW()
            WHERE id = %s
            RETURNING id, user_id, request_id, amount, payment_method
            """,
            (reference, screenshot_file_id, payment_id),
            fetch_one=True,
        )

        if not updated:
            logger.error(f"Pending payment not found to finalize: {payment_id}")
            return None

        # Mirror into AR ledger
        receivable = get_receivable_by_source('subscription', updated['request_id'])
        if not receivable:
            receivable = create_receivable(
                user_id=updated['user_id'],
                receivable_type='subscription',
                source_id=updated['request_id'],
                bill_amount=updated.get('amount', 0),
                discount_amount=0,
                final_amount=updated.get('amount', 0),
            )

        rid = receivable.get('receivable_id') if receivable else None
        if rid:
            create_transactions(
                receivable_id=rid,
                lines=[{'method': updated['payment_method'], 'amount': updated['amount'], 'reference': reference}],
                admin_user_id=None,
            )
            update_receivable_status(rid)

        logger.info(f"Finalized pending payment {payment_id} and mirrored to AR")
        return updated
    except Exception as e:
        logger.error(f"Error finalizing pending payment: {e}")
    return None

logger = logging.getLogger(__name__)

# Subscription Plans
SUBSCRIPTION_PLANS = {
    "plan_30": {"name": "30 Days", "duration_days": 30, "amount": 2500},
    "plan_90": {"name": "90 Days", "duration_days": 90, "amount": 7000},
    "plan_180": {"name": "180 Days", "duration_days": 180, "amount": 13500},
}


def create_subscription_request(user_id: int, plan_id: str, amount: int, payment_method: str = 'pending') -> dict:
    """Create a new subscription request from user
    payment_method: 'cash', 'upi', or 'pending'
    """
    try:
        plan = SUBSCRIPTION_PLANS.get(plan_id)
        if not plan:
            logger.error(f"Invalid plan ID: {plan_id}")
            return None
        
        requested_date = datetime.now()
        
        result = execute_query(
            """
            INSERT INTO subscription_requests (user_id, plan_id, amount, payment_method, status, requested_at)
            VALUES (%s, %s, %s, %s, 'pending', %s)
            RETURNING id, user_id, plan_id, amount, payment_method, status, requested_at
            """,
            (user_id, plan_id, amount, payment_method, requested_date),
            fetch_one=True,
        )
        
        if result:
            logger.info(f"Subscription request created: User {user_id}, Plan {plan_id}, Payment: {payment_method}")
            return result
    except Exception as e:
        logger.error(f"Error creating subscription request for user {user_id}: {e}")
        # Check if it's a foreign key error (user doesn't exist in database yet)
        if "foreign key constraint" in str(e).lower():
            logger.error(f"Foreign key error: User {user_id} may not exist in database yet")
        return None
    
    return None


def get_pending_subscription_requests() -> list:
    """Get all pending subscription requests"""
    try:
        rows = execute_query(
            """
            SELECT sr.id, sr.user_id, sr.plan_id, sr.amount, sr.status, sr.requested_at,
                   u.full_name, u.phone
            FROM subscription_requests sr
            JOIN users u ON sr.user_id = u.user_id
            WHERE sr.status = 'pending'
            ORDER BY sr.requested_at DESC
            """,
            fetch_one=False,
        )
        
        if rows:
            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "plan_id": row[2],
                    "amount": row[3],
                    "status": row[4],
                    "requested_at": row[5],
                    "full_name": row[6],
                    "phone": row[7],
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Error fetching pending subscription requests: {e}")
    
    return []


def get_user_pending_subscription_request(user_id: int) -> dict:
    """Get pending subscription request for a specific user"""
    try:
        result = execute_query(
            """
            SELECT sr.id, sr.user_id, sr.plan_id, sr.amount, sr.status, sr.requested_at,
                   sr.payment_method
            FROM subscription_requests sr
            WHERE sr.user_id = %s AND sr.status = 'pending'
            LIMIT 1
            """,
            (user_id,),
            fetch_one=True,
        )
        
        if result:
            return {
                "id": result['id'],
                "user_id": result['user_id'],
                "plan_id": result['plan_id'],
                "amount": result['amount'],
                "status": result['status'],
                "requested_at": result['requested_at'],
                "payment_method": result.get('payment_method', 'unknown'),
            }
    except Exception as e:
        logger.error(f"Error fetching pending request for user {user_id}: {e}")
    
    return None


def get_subscription_request_details(request_id: int) -> dict:
    """Get subscription request details by request ID"""
    try:
        result = execute_query(
            """SELECT sr.id, sr.user_id, sr.plan_id, sr.amount, sr.status, sr.payment_method, sr.requested_at,
                      u.full_name as user_name
               FROM subscription_requests sr
               LEFT JOIN users u ON sr.user_id = u.user_id
               WHERE sr.id = %s""",
            (request_id,),
            fetch_one=True,
        )
        
        if result:
            return {
                "id": result['id'],
                "user_id": result['user_id'],
                "plan_id": result['plan_id'],
                "amount": result['amount'],
                "status": result['status'],
                "payment_method": result.get('payment_method', 'unknown'),
                "requested_at": result['requested_at'],
                "user_name": result.get('user_name', 'Unknown User'),
            }
    except Exception as e:
        logger.error(f"Error fetching subscription request {request_id}: {e}")
    
    return None


def approve_subscription(request_id: int, amount: int, end_date: datetime) -> bool:
    """Approve a subscription request and activate subscription"""
    try:
        # Get the request details
        request = execute_query(
            "SELECT user_id, plan_id FROM subscription_requests WHERE id = %s",
            (request_id,),
            fetch_one=True,
        )
        
        if not request:
            logger.error(f"Subscription request not found: {request_id}")
            return False
        
        user_id, plan_id = request['user_id'], request['plan_id']
        start_date = datetime.now()

        # Ensure AR receivable exists for this subscription request
        receivable = get_receivable_by_source('subscription', request_id)
        if not receivable:
            receivable = create_receivable(
                user_id=user_id,
                receivable_type='subscription',
                source_id=request_id,
                bill_amount=amount,
                discount_amount=0,
                final_amount=amount,
                due_date=end_date.date() if end_date else None,
            )
        
        # Update subscription_requests status
        execute_query(
            "UPDATE subscription_requests SET status = 'approved', approved_at = %s WHERE id = %s",
            (start_date, request_id),
        )
        
        # Check if user already has active subscription
        existing = execute_query(
            "SELECT id FROM subscriptions WHERE user_id = %s AND status = 'active'",
            (user_id,),
            fetch_one=True,
        )
        
        if existing:
            # Update existing subscription
            execute_query(
                """
                UPDATE subscriptions 
                SET plan_id = %s, amount = %s, start_date = %s, end_date = %s,
                    status = 'active', grace_period_end = %s, updated_at = %s
                WHERE user_id = %s AND status = 'active'
                """,
                (plan_id, amount, start_date, end_date, end_date + timedelta(days=7), start_date, user_id),
            )
        else:
            # Create new subscription
            execute_query(
                """
                INSERT INTO subscriptions (user_id, plan_id, amount, start_date, end_date, status, grace_period_end, created_at)
                VALUES (%s, %s, %s, %s, %s, 'active', %s, %s)
                """,
                (user_id, plan_id, amount, start_date, end_date, end_date + timedelta(days=7), start_date),
            )
        
        # Update user fee_status to 'paid' when subscription is approved
        execute_query(
            "UPDATE users SET fee_status = 'paid', fee_paid_date = CURRENT_TIMESTAMP WHERE user_id = %s",
            (user_id,),
        )
        logger.info(f"User {user_id} fee_status updated to 'paid' on subscription approval")
        
        logger.info(f"Subscription approved for user {user_id}: Amount {amount}, End Date {end_date}")
        return True
        
    except Exception as e:
        logger.error(f"Error approving subscription: {e}")
    
    return False


def reject_subscription(request_id: int, reason: str = "") -> bool:
    """Reject a subscription request"""
    try:
        execute_query(
            "UPDATE subscription_requests SET status = 'rejected', rejection_reason = %s WHERE id = %s",
            (reason, request_id),
        )
        logger.info(f"Subscription request rejected: {request_id}")
        return True
    except Exception as e:
        logger.error(f"Error rejecting subscription: {e}")
    
    return False


def get_user_subscription(user_id: int) -> dict:
    """Get active subscription for a user"""
    try:
        row = execute_query(
            """
            SELECT id, user_id, plan_id, amount, start_date, end_date, status, 
                   grace_period_end, created_at, updated_at
            FROM subscriptions
            WHERE user_id = %s AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,),
            fetch_one=True,
        )
        
        if row:
            # Row is already a dict from RealDictCursor
            return row
    except Exception as e:
        logger.error(f"Error fetching subscription: {e}")
    
    return None


def is_subscription_active(user_id: int) -> bool:
    """Check if user has an active subscription"""
    sub = get_user_subscription(user_id)
    if not sub:
        return False
    
    now = datetime.now()
    return sub["status"] == "active" and now <= sub["end_date"]


def is_in_grace_period(user_id: int) -> bool:
    """Check if user is in grace period (subscription expired but within 7 days)"""
    try:
        sub = get_user_subscription(user_id)
        if not sub:
            return False
        
        now = datetime.now()
        end_date = sub["end_date"]
        grace_period_end = sub["grace_period_end"]
        
        return end_date < now <= grace_period_end
    except Exception as e:
        logger.error(f"Error checking grace period: {e}")
    
    return False


def is_subscription_expired(user_id: int) -> bool:
    """Check if subscription is completely expired (past grace period)"""
    try:
        sub = get_user_subscription(user_id)
        if not sub:
            return True  # No subscription = expired
        
        now = datetime.now()
        grace_period_end = sub["grace_period_end"]
        
        return now > grace_period_end
    except Exception as e:
        logger.error(f"Error checking subscription expiry: {e}")
    
    return True


def get_expiring_subscriptions(days_ahead: int = 2) -> list:
    """Get subscriptions expiring in N days"""
    try:
        expiry_threshold = datetime.now() + timedelta(days=days_ahead)
        
        rows = execute_query(
            """
            SELECT s.id, s.user_id, s.end_date, u.full_name, u.phone
            FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.status = 'active'
            AND DATE(s.end_date) = DATE(%s)
            """,
            (expiry_threshold,),
            fetch_one=False,
        )
        
        if rows:
            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "end_date": row[2],
                    "full_name": row[3],
                    "phone": row[4],
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Error fetching expiring subscriptions: {e}")
    
    return []


def get_users_in_grace_period() -> list:
    """Get users in grace period (need daily reminders)"""
    try:
        rows = execute_query(
            """
            SELECT s.user_id, s.end_date, s.grace_period_end, u.full_name, u.phone
            FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.status = 'active'
            AND s.end_date < NOW()
            AND NOW() <= s.grace_period_end
            """,
            fetch_one=False,
        )
        
        if rows:
            return [
                {
                    "user_id": row[0],
                    "end_date": row[1],
                    "grace_period_end": row[2],
                    "full_name": row[3],
                    "phone": row[4],
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Error fetching users in grace period: {e}")
    
    return []


def get_expired_subscriptions() -> list:
    """Get completely expired subscriptions (past grace period)"""
    try:
        rows = execute_query(
            """
            SELECT s.user_id, s.grace_period_end, u.full_name, u.phone
            FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.status = 'active'
            AND NOW() > s.grace_period_end
            """,
            fetch_one=False,
        )
        
        if rows:
            return [
                {
                    "user_id": row[0],
                    "grace_period_end": row[1],
                    "full_name": row[2],
                    "phone": row[3],
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Error fetching expired subscriptions: {e}")
    
    return []


def mark_subscription_locked(user_id: int) -> bool:
    """Mark subscription as locked (expired past grace period)"""
    try:
        execute_query(
            """
            UPDATE subscriptions
            SET status = 'locked'
            WHERE user_id = %s AND NOW() > grace_period_end
            """,
            (user_id,),
        )
        logger.info(f"Subscription locked for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error locking subscription: {e}")
    
    return False


def record_payment(user_id: int, request_id: int, amount: float, payment_method: str, reference: str = None, screenshot_file_id: str = None) -> dict:
    """Record subscription payment in revenue log
    Args:
        user_id: User ID
        request_id: Subscription request ID
        amount: Payment amount
        payment_method: 'cash' or 'upi'
        reference: Transaction reference code
        screenshot_file_id: Telegram file_id for UPI payment screenshot (optional)
    """
    try:
        # Fetch request details for AR linkage
        req = execute_query(
            "SELECT user_id, amount FROM subscription_requests WHERE id = %s",
            (request_id,),
            fetch_one=True,
        )
        if not req:
            logger.error(f"Subscription request not found for payment: {request_id}")
            return None

        result = execute_query(
            """
            INSERT INTO subscription_payments (user_id, request_id, amount, payment_method, reference, screenshot_file_id, status, paid_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'completed', NOW())
            RETURNING id, user_id, amount, payment_method, paid_at
            """,
            (user_id, request_id, amount, payment_method, reference, screenshot_file_id),
            fetch_one=True,
        )
        
        if result:
            logger.info(
                f"Payment recorded: User {user_id}, Amount {amount}, Method {payment_method}, Screenshot: {'Yes' if screenshot_file_id else 'No'}"
            )

            # Mirror payment into AR ledger
            try:
                receivable = get_receivable_by_source('subscription', request_id)
                if not receivable:
                    receivable = create_receivable(
                        user_id=req['user_id'],
                        receivable_type='subscription',
                        source_id=request_id,
                        bill_amount=req.get('amount', amount),
                        discount_amount=0,
                        final_amount=req.get('amount', amount),
                    )
                rid = receivable.get('receivable_id')
                if rid:
                    create_transactions(
                        receivable_id=rid,
                        lines=[{'method': payment_method, 'amount': amount, 'reference': reference}],
                        admin_user_id=None,
                    )
                    update_receivable_status(rid)
            except Exception as ar_err:
                logger.error(f"Failed to mirror subscription payment into AR: {ar_err}")

            return {
                "payment_id": result.get("id"),
                "user_id": result.get("user_id"),
                "amount": result.get("amount"),
                "payment_method": result.get("payment_method"),
                "paid_at": result.get("paid_at"),
            }
    except Exception as e:
        logger.error(f"Error recording payment: {e}")
    
    return None


def get_revenue_report(start_date=None, end_date=None) -> list:
    """Get revenue report with payment details"""
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        rows = execute_query(
            """
            SELECT 
                sp.id, u.full_name, u.user_id, sp.amount, sp.payment_method, sp.paid_at,
                sr.plan_id
            FROM subscription_payments sp
            JOIN users u ON sp.user_id = u.user_id
            LEFT JOIN subscription_requests sr ON sp.request_id = sr.id
            WHERE sp.paid_at BETWEEN %s AND %s AND sp.status = 'completed'
            ORDER BY sp.paid_at DESC
            """,
            (start_date, end_date),
        )
        
        if rows:
            return [
                {
                    "payment_id": row[0],
                    "user_name": row[1],
                    "user_id": row[2],
                    "amount": row[3],
                    "payment_method": row[4],
                    "paid_at": row[5],
                    "plan_id": row[6],
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Error fetching revenue report: {e}")
    
    return []


def get_total_revenue(start_date=None, end_date=None) -> float:
    """Get total revenue for period"""
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        result = execute_query(
            """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM subscription_payments
            WHERE paid_at BETWEEN %s AND %s AND status = 'completed'
            """,
            (start_date, end_date),
            fetch_one=True,
        )
        
        if result:
            return result[0] if isinstance(result, tuple) else result.get('total', 0)
    except Exception as e:
        logger.error(f"Error calculating revenue: {e}")
    
    return 0


def create_split_payment_receivable(user_id: int, request_id: int, upi_amount: float, cash_amount: float) -> dict:
    """Create a split payment receivable with two transaction lines: UPI and CASH_PENDING"""
    try:
        total_amount = upi_amount + cash_amount
        
        # Create receivable for the total amount
        receivable = create_receivable(
            user_id=user_id,
            receivable_type='subscription',
            source_id=request_id,
            bill_amount=total_amount,
            discount_amount=0.0,
            final_amount=total_amount
        )
        
        if not receivable:
            logger.error(f"Failed to create receivable for split payment")
            return None
        
        receivable_id = receivable.get('receivable_id')
        
        # Create transaction lines for UPI (pending) and CASH (pending)
        lines = [
            {
                'method': 'upi',
                'amount': upi_amount,
                'reference': f"SPLIT_UPI_{request_id}",
            },
            {
                'method': 'cash',
                'amount': cash_amount,
                'reference': f"SPLIT_CASH_{request_id}",
            }
        ]
        
        create_transactions(receivable_id, lines, admin_user_id=None)
        
        # Update receivable status (will be 'partial' since lines are recorded but not marked as paid yet)
        updated = update_receivable_status(receivable_id)
        
        logger.info(f"Split payment receivable created: User {user_id}, Request {request_id}, UPI {upi_amount}, Cash {cash_amount}")
        
        return {
            'receivable_id': receivable_id,
            'receivable': updated,
            'upi_amount': upi_amount,
            'cash_amount': cash_amount
        }
        
    except Exception as e:
        logger.error(f"Error creating split payment receivable: {e}")
        return None


def record_split_upi_payment(user_id: int, request_id: int, upi_amount: float, transaction_ref: str) -> bool:
    """Record UPI payment for a split payment - updates AR ledger"""
    try:
        # Get the receivable for this request
        receivable = get_receivable_by_source('subscription', request_id)
        if not receivable:
            logger.error(f"Receivable not found for split payment request {request_id}")
            return False
        
        receivable_id = receivable.get('receivable_id')
        
        # Update the UPI transaction line with the reference
        execute_query(
            "UPDATE ar_transactions SET reference=%s WHERE receivable_id=%s AND method='upi'",
            (transaction_ref, receivable_id)
        )
        
        # Update receivable status
        update_receivable_status(receivable_id)
        
        logger.info(f"Split payment UPI recorded: User {user_id}, Request {request_id}, Amount {upi_amount}, Ref {transaction_ref}")
        return True
        
    except Exception as e:
        logger.error(f"Error recording split UPI payment: {e}")
        return False


def record_split_cash_payment(user_id: int, request_id: int) -> bool:
    """Record cash payment for a split payment - updates AR ledger"""
    try:
        # Get the receivable for this request
        receivable = get_receivable_by_source('subscription', request_id)
        if not receivable:
            logger.error(f"Receivable not found for split payment request {request_id}")
            return False
        
        receivable_id = receivable.get('receivable_id')
        
        # Mark the cash transaction as paid (update reference to confirmed)
        execute_query(
            "UPDATE ar_transactions SET reference=%s WHERE receivable_id=%s AND method='cash'",
            ('CASH_CONFIRMED', receivable_id)
        )
        
        # Update receivable status
        updated = update_receivable_status(receivable_id)
        
        logger.info(f"Split payment cash confirmed: User {user_id}, Request {request_id}, Status {updated.get('status')}")
        return True
        
    except Exception as e:
        logger.error(f"Error confirming split cash payment: {e}")
        return False


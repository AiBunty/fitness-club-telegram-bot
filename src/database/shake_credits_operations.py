"""
Shake Credit Operations
Handles all shake credit transactions, purchases, and consumption
"""

import logging
from datetime import datetime, date
from src.database.connection import execute_query, get_db_cursor
from src.database.ar_operations import (
    create_receivable, create_transactions, update_receivable_status, get_receivable_by_source
)

logger = logging.getLogger(__name__)

# Shake credit pricing: Rs 6000 for 25 credits
CREDIT_COST = 6000
CREDITS_PER_PURCHASE = 25
COST_PER_CREDIT = CREDIT_COST / CREDITS_PER_PURCHASE  # Rs 240 per credit
RECEIVABLE_TYPE = 'shake_credit'


def init_user_credits(user_id: int):
    """Initialize shake credits for new user"""
    try:
        query = """
            INSERT INTO shake_credits (user_id, total_credits, used_credits, available_credits)
            VALUES (%s, 0, 0, 0)
            ON CONFLICT (user_id) DO NOTHING
        """
        execute_query(query, (user_id,))
        logger.info(f"Shake credits initialized for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize credits for user {user_id}: {e}")
        return False


def get_user_credits(user_id: int) -> dict:
    """Get user's current shake credits balance"""
    try:
        query = """
            SELECT user_id, total_credits, used_credits, available_credits, last_updated
            FROM shake_credits
            WHERE user_id = %s
        """
        result = execute_query(query, (user_id,), fetch_one=True)
        
        if result:
            # Compute authoritative available credits from transaction ledger
            try:
                ledger = execute_query("SELECT COALESCE(SUM(credit_change),0) as avail FROM shake_transactions WHERE user_id = %s", (user_id,), fetch_one=True)
                avail = ledger.get('avail', 0) if ledger else 0
            except Exception:
                avail = result['available_credits']

            return {
                'user_id': result['user_id'],
                'total_credits': result['total_credits'],
                'used_credits': result['used_credits'],
                'available_credits': avail,
                'last_updated': result['last_updated']
            }
        else:
            # Initialize if doesn't exist
            init_user_credits(user_id)
            return {
                'user_id': user_id,
                'total_credits': 0,
                'used_credits': 0,
                'available_credits': 0,
                'last_updated': datetime.now()
            }
    except Exception as e:
        logger.error(f"Failed to get credits for user {user_id}: {e}")
        return None


def add_credits(user_id: int, credits: int, transaction_type: str, description: str = None) -> bool:
    """
    Add shake credits to user account
    
    Args:
        user_id: User's Telegram ID
        credits: Number of credits to add
        transaction_type: 'purchase', 'referral', 'admin_gift'
        description: Optional description
    """
    try:
        # Update credits
        query1 = """
            UPDATE shake_credits 
            SET total_credits = total_credits + %s,
                available_credits = available_credits + %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """
        execute_query(query1, (credits, credits, user_id))
        
        # Get the updated result
        query2 = "SELECT total_credits, available_credits FROM shake_credits WHERE user_id = %s"
        result = execute_query(query2, (user_id,), fetch_one=True)
        
        if result:
            # Log transaction
            query2 = """
                INSERT INTO shake_transactions 
                (user_id, credit_change, transaction_type, description, created_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            """
            execute_query(query2, (user_id, credits, transaction_type, description or f"{transaction_type}: +{credits} credits"))
            
            logger.info(f"Added {credits} credits to user {user_id}. Total: {result['total_credits']}, Available: {result['available_credits']}")
            return True
        else:
            logger.warning(f"User {user_id} credits record not found")
            init_user_credits(user_id)
            return add_credits(user_id, credits, transaction_type, description)
    except Exception as e:
        logger.error(f"Failed to add credits for user {user_id}: {e}")
        return False


def consume_credit(user_id: int, reason: str = "Shake consumed") -> bool:
    """Deduct 1 shake credit (when shake is consumed)"""
    try:
        # Perform an atomic, ledger-based consumption using DB transaction and row lock
        with get_db_cursor(commit=True) as cur:
            # Ensure shake_credits row exists and lock it to prevent race
            cur.execute("SELECT credit_id, total_credits, used_credits, available_credits FROM shake_credits WHERE user_id = %s FOR UPDATE", (user_id,))
            row = cur.fetchone()
            if not row:
                # initialize record if missing
                cur.execute("INSERT INTO shake_credits (user_id, total_credits, used_credits, available_credits, last_updated) VALUES (%s, 0, 0, 0, CURRENT_TIMESTAMP)", (user_id,))
                # re-select
                cur.execute("SELECT credit_id, total_credits, used_credits, available_credits FROM shake_credits WHERE user_id = %s FOR UPDATE", (user_id,))
                row = cur.fetchone()

            # Compute authoritative balance from transaction ledger
            cur.execute("SELECT COALESCE(SUM(credit_change),0) as avail FROM shake_transactions WHERE user_id = %s", (user_id,))
            ledger = cur.fetchone()
            avail = ledger.get('avail', 0) if ledger else 0

            if avail <= 0:
                logger.warning(f"User {user_id} has no available credits (ledger)")
                return False

            # Insert negative ledger entry for consumption
            cur.execute(
                "INSERT INTO shake_transactions (user_id, credit_change, transaction_type, description, created_at) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)",
                (user_id, -1, 'consume', reason)
            )

            # Update aggregate cache row to reflect counts (best-effort, within same transaction)
            cur.execute(
                "UPDATE shake_credits SET used_credits = COALESCE(used_credits,0) + 1, available_credits = GREATEST(COALESCE(available_credits,0) - 1, 0), last_updated = CURRENT_TIMESTAMP WHERE user_id = %s",
                (user_id,)
            )
            # Fetch updated values
            cur.execute("SELECT used_credits, available_credits FROM shake_credits WHERE user_id = %s", (user_id,))
            updated = cur.fetchone()

            logger.info(f"Deducted 1 credit from user {user_id}. Ledger available before deduction: {avail}")
            return True
    except Exception as e:
        logger.error(f"Failed to consume credit for user {user_id}: {e}")
        return False


def consume_credit_with_date(user_id: int, consumption_date: date, reason: str = "Manual admin deduction") -> bool:
    """
    Deduct 1 shake credit with specific consumption date
    Used when admin manually logs shake consumption without credit
    """
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("SELECT credit_id FROM shake_credits WHERE user_id = %s FOR UPDATE", (user_id,))
            row = cur.fetchone()
            if not row:
                cur.execute("INSERT INTO shake_credits (user_id, total_credits, used_credits, available_credits, last_updated) VALUES (%s, 0, 0, 0, CURRENT_TIMESTAMP)", (user_id,))
                cur.execute("SELECT credit_id FROM shake_credits WHERE user_id = %s FOR UPDATE", (user_id,))

            cur.execute("SELECT COALESCE(SUM(credit_change),0) as avail FROM shake_transactions WHERE user_id = %s", (user_id,))
            ledger = cur.fetchone()
            avail = ledger.get('avail', 0) if ledger else 0

            if avail <= 0:
                logger.warning(f"User {user_id} has no available credits (ledger)")
                return False

            cur.execute(
                "INSERT INTO shake_transactions (user_id, credit_change, transaction_type, description, reference_date, created_at) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)",
                (user_id, -1, 'admin_deduction', reason, consumption_date)
            )

            cur.execute(
                "UPDATE shake_credits SET used_credits = COALESCE(used_credits,0) + 1, available_credits = GREATEST(COALESCE(available_credits,0) - 1, 0), last_updated = CURRENT_TIMESTAMP WHERE user_id = %s RETURNING used_credits, available_credits",
                (user_id,)
            )
            updated = cur.fetchone()
            logger.info(f"Admin deducted 1 credit from user {user_id} for date {consumption_date}")
            return True
    except Exception as e:
        logger.error(f"Failed to consume credit with date for user {user_id}: {e}")
        return False


def create_purchase_request(user_id: int, credits: int, payment_method: str = 'unknown') -> dict:
    """
    Create a shake credit purchase request
    Admin must approve before credits are transferred
    
    Args:
        user_id: User's Telegram ID
        credits: Number of credits to purchase (default 25)
        payment_method: 'cash', 'upi', or 'unknown'
    
    Returns:
        Purchase request record with ID and status
    """
    try:
        amount = credits * COST_PER_CREDIT
        
        query1 = """
            INSERT INTO shake_purchases 
            (user_id, credits_requested, amount, payment_method, status)
            VALUES (%s, %s, %s, %s, 'pending')
        """
        execute_query(query1, (user_id, credits, amount, payment_method))
        
        # Get the created purchase request
        query2 = "SELECT purchase_id, user_id, credits_requested, amount, payment_method, status, created_at FROM shake_purchases WHERE user_id = %s ORDER BY purchase_id DESC LIMIT 1"
        result = execute_query(query2, (user_id,), fetch_one=True)
        
        if result:
            logger.info(f"Purchase request created for user {user_id}: {credits} credits (Rs {amount})")
            return result
        
        return None
    except Exception as e:
        logger.error(f"Failed to create purchase request for user {user_id}: {e}")
        return None


def get_pending_purchase_requests(limit: int = 20) -> list:
    """Get all pending shake credit purchase requests"""
    try:
        query = """
            SELECT sp.purchase_id, sp.user_id, u.full_name, u.telegram_username,
                   sp.credits_requested, sp.amount, sp.payment_method, sp.status, sp.created_at
            FROM shake_purchases sp
            JOIN users u ON sp.user_id = u.user_id
            WHERE sp.status = 'pending'
            ORDER BY sp.created_at ASC
            LIMIT %s
        """
        results = execute_query(query, (limit,))
        return results if results else []
    except Exception as e:
        logger.error(f"Failed to get pending purchase requests: {e}")
        return []


def approve_purchase(purchase_id: int, admin_user_id: int, amount_paid: float = None) -> dict:
    """
    Approve a shake credit purchase request
    This transfers the credits to user's account and creates AR receivable
    
    Args:
        purchase_id: Purchase request ID
        admin_user_id: Admin who approved
        amount_paid: Actual amount received (for partial payments)
    
    Returns:
        Updated purchase record with user info
    """
    try:
        # Get purchase details
        query_get = """
            SELECT purchase_id, user_id, credits_requested, amount, payment_method, status
            FROM shake_purchases
            WHERE purchase_id = %s
        """
        purchase = execute_query(query_get, (purchase_id,), fetch_one=True)
        
        if not purchase:
            logger.warning(f"Purchase {purchase_id} not found")
            return None

        if purchase['status'] != 'pending':
            purchase['already_processed'] = True
            logger.info(f"Purchase {purchase_id} already {purchase['status']}")
            return purchase
        
        user_id = purchase['user_id']
        credits = purchase['credits_requested']
        amount = purchase['amount']
        payment_method = purchase.get('payment_method', 'unknown')
        
        # Use provided amount_paid or fall back to full amount
        final_amount_paid = amount_paid if amount_paid is not None else amount
        
        # Update purchase status
        query_update = """
            UPDATE shake_purchases
            SET status = 'approved', approved_by = %s, approved_at = CURRENT_TIMESTAMP, amount_paid = %s
            WHERE purchase_id = %s
        """
        execute_query(query_update, (admin_user_id, final_amount_paid, purchase_id))
        
        # Update user fee_status to 'paid' when payment is approved
        # If amount_paid is 0 or not provided, it's a credit sale - still mark as paid but trigger follow-up
        query_update_user = """
            UPDATE users
            SET fee_status = 'paid', fee_paid_date = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """
        execute_query(query_update_user, (user_id,))
        logger.info(f"User {user_id} fee_status updated to 'paid' on shake credit approval")
        
        # Add credits to user
        add_credits(user_id, credits, 'purchase', f"Purchased {credits} credits for Rs {amount}")
        
        # Create or retrieve AR receivable for this purchase
        try:
            receivable = get_receivable_by_source(RECEIVABLE_TYPE, purchase_id)
            if not receivable:
                # Create new receivable with immediate due date (paid on approval)
                # Calculate discount if partial payment
                discount = amount - final_amount_paid
                
                receivable = create_receivable(
                    user_id=user_id,
                    receivable_type=RECEIVABLE_TYPE,
                    source_id=purchase_id,
                    bill_amount=amount,
                    discount_amount=discount,
                    final_amount=final_amount_paid,
                    due_date=date.today()
                )
            
            # Add AR transaction line with actual payment method and amount
            if receivable and receivable.get('receivable_id'):
                create_transactions(
                    receivable_id=receivable['receivable_id'],
                    lines=[{
                        'method': payment_method,
                        'amount': final_amount_paid,
                        'reference': f'Shake credit purchase {purchase_id}'
                    }],
                    admin_user_id=admin_user_id
                )
                # Recompute receivable status (should mark as paid since amount collected)
                update_receivable_status(receivable['receivable_id'])
                logger.info(f"AR receivable {receivable['receivable_id']} created for shake purchase {purchase_id}")
        except Exception as ar_err:
            logger.error(f"Failed to create AR receivable for shake purchase {purchase_id}: {ar_err}")
        
        # If amount_paid is 0 or less, it's a credit sale - create follow-up for payment collection
        if final_amount_paid <= 0:
            followup_result = create_credit_sale_followup(user_id, purchase_id, amount)
            logger.info(f"Credit sale follow-up: {followup_result}")
        
        logger.info(f"Purchase {purchase_id} approved by admin {admin_user_id}. {credits} credits transferred to user {user_id}")
        
        # Get updated record
        query_final = """
            SELECT sp.purchase_id, sp.user_id, u.full_name, sp.credits_requested, 
                   sp.amount, sp.status, sp.approved_at
            FROM shake_purchases sp
            JOIN users u ON sp.user_id = u.user_id
            WHERE sp.purchase_id = %s
        """
        return execute_query(query_final, (purchase_id,), fetch_one=True)
    except Exception as e:
        logger.error(f"Failed to approve purchase {purchase_id}: {e}")
        return None


def reject_purchase(purchase_id: int, admin_user_id: int, reason: str = "") -> bool:
    """Reject a shake credit purchase request"""
    try:
        purchase = execute_query(
            "SELECT status FROM shake_purchases WHERE purchase_id = %s",
            (purchase_id,),
            fetch_one=True,
        )

        if not purchase:
            logger.warning(f"Purchase {purchase_id} not found for rejection")
            return None

        if purchase['status'] != 'pending':
            purchase['already_processed'] = True
            return purchase

        query1 = """
            UPDATE shake_purchases
            SET status = 'rejected', approved_by = %s, approved_at = CURRENT_TIMESTAMP
            WHERE purchase_id = %s AND status = 'pending'
        """
        execute_query(query1, (admin_user_id, purchase_id))
        
        # Get the updated result
        query2 = "SELECT purchase_id, status FROM shake_purchases WHERE purchase_id = %s"
        result = execute_query(query2, (purchase_id,), fetch_one=True)
        if result:
            result['already_processed'] = False
            logger.info(f"Purchase {purchase_id} rejected by admin {admin_user_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to reject purchase {purchase_id}: {e}")
        return False


def get_shake_report(user_id: int) -> dict:
    """
    Get detailed shake credit report for user
    Shows: Total credits purchased, consumption history, current balance
    """
    try:
        # Get current balance
        balance = get_user_credits(user_id)
        
        # Get all transactions
        query = """
            SELECT transaction_id, credit_change, transaction_type, description, 
                   reference_date, created_at
            FROM shake_transactions
            WHERE user_id = %s
            ORDER BY created_at DESC
        """
        transactions = execute_query(query, (user_id,))
        
        return {
            'user_id': user_id,
            'current_balance': balance,
            'transactions': transactions if transactions else []
        }
    except Exception as e:
        logger.error(f"Failed to get shake report for user {user_id}: {e}")
        return None


def get_all_user_reports() -> list:
    """Get shake credit summary for all users"""
    try:
        query = """
            SELECT sc.user_id, u.full_name, u.telegram_username,
                   sc.total_credits, sc.used_credits, sc.available_credits,
                   sc.last_updated
            FROM shake_credits sc
            JOIN users u ON sc.user_id = u.user_id
            WHERE sc.total_credits > 0
            ORDER BY sc.available_credits DESC
        """
        results = execute_query(query)
        return results if results else []
    except Exception as e:
        logger.error(f"Failed to get all user reports: {e}")
        return []


def create_credit_sale_followup(user_id: int, purchase_id: int, original_amount: float) -> dict:
    """
    Create payment follow-up for credit sales (0 amount approved purchases)
    This is called when amount_paid is 0 to trigger payment collection reminder
    Logs the credit sale for admin follow-up
    
    Args:
        user_id: User ID
        purchase_id: Purchase request ID
        original_amount: Original amount due
    
    Returns:
        dict with followup status
    """
    try:
        # Log credit sale for admin follow-up
        logger.warning(f"[CREDIT SALE] User {user_id}: Purchase {purchase_id} approved for Rs {original_amount} with 0 payment")
        logger.warning(f"[PAYMENT FOLLOWUP REQUIRED] User {user_id} owes Rs {original_amount} for shake credit purchase #{purchase_id}")
        
        # Try to create notification if the column exists
        try:
            from src.database.notifications_operations import create_notification
            create_notification(
                user_id=user_id,
                notification_type='payment_followup',
                title=f'Payment Follow-up: Shake Credits',
                link_data=f'shake_purchase_{purchase_id}'
            )
        except Exception as notif_err:
            logger.debug(f"Could not create notification: {notif_err}")
        
        return {
            'success': True,
            'followup_type': 'credit_sale',
            'message': f'Payment follow-up created for credit sale: Rs {original_amount}'
        }
    except Exception as e:
        logger.error(f"Failed to create credit sale follow-up for user {user_id}: {e}")
        return {
            'success': False,
            'message': str(e)
        }

"""
Challenge Payment Operations
Handles AR integration for paid challenges
"""

from datetime import datetime, date
from src.database.connection import DatabaseConnection
from src.database.ar_operations import create_receivable, create_transactions, update_receivable_status

def create_challenge_receivable(user_id: int, challenge_id: int, challenge_name: str, 
                               amount: float, admin_id: int) -> dict:
    """
    Create AR receivable for challenge entry payment
    
    Args:
        user_id: User ID joining the challenge
        challenge_id: Challenge ID
        challenge_name: Name of challenge
        amount: Entry fee amount
        admin_id: Admin who approved the participation
    
    Returns:
        dict: {'success': bool, 'receivable_id': int, 'message': str}
    """
    try:
        # Create receivable using universal payment standard
        receivable_id = create_receivable(
            user_id=user_id,
            amount=amount,
            description=f"Challenge Entry: {challenge_name}",
            method='unknown',  # Universal default
            due_date=datetime.now().date()  # Approval date = due date
        )
        
        if receivable_id:
            # Update challenge_participants with receivable_id
            db = DatabaseConnection()
            update_query = """
                UPDATE challenge_participants 
                SET receivable_id = %s
                WHERE challenge_id = %s AND user_id = %s
            """
            db.execute_update(update_query, (receivable_id, challenge_id, user_id))
            
            return {
                'success': True,
                'receivable_id': receivable_id,
                'message': 'Challenge receivable created successfully'
            }
        else:
            return {
                'success': False,
                'receivable_id': None,
                'message': 'Failed to create receivable'
            }
            
    except Exception as e:
        print(f"❌ Error creating challenge receivable: {e}")
        return {
            'success': False,
            'receivable_id': None,
            'message': str(e)
        }

def process_challenge_payment(receivable_id: int, payment_amount: float, 
                             admin_id: int, payment_date: date = None) -> dict:
    """
    Process payment transaction for challenge entry
    
    Args:
        receivable_id: AR receivable ID
        payment_amount: Amount received
        admin_id: Admin processing the payment
        payment_date: Date of payment (defaults to today)
    
    Returns:
        dict: {'success': bool, 'status': str, 'message': str}
    """
    try:
        if payment_date is None:
            payment_date = datetime.now().date()
        
        # Create transaction
        transaction_id = create_transactions(
            receivable_id=receivable_id,
            amount=payment_amount,
            payment_date=payment_date,
            created_by=admin_id
        )
        
        if not transaction_id:
            return {
                'success': False,
                'status': 'unpaid',
                'message': 'Failed to create payment transaction'
            }
        
        # Update receivable status
        new_status = update_receivable_status(receivable_id)
        
        # Update challenge_participants payment_status
        db = DatabaseConnection()
        update_query = """
            UPDATE challenge_participants 
            SET payment_status = %s
            WHERE receivable_id = %s
        """
        db.execute_update(update_query, (new_status, receivable_id))
        
        return {
            'success': True,
            'status': new_status,
            'message': f'Payment processed successfully. Status: {new_status}'
        }
        
    except Exception as e:
        print(f"❌ Error processing challenge payment: {e}")
        return {
            'success': False,
            'status': 'error',
            'message': str(e)
        }

def get_participant_payment_status(user_id: int, challenge_id: int) -> dict:
    """
    Get payment status for a challenge participant
    
    Args:
        user_id: User ID
        challenge_id: Challenge ID
    
    Returns:
        dict: Payment status information
    """
    try:
        db = DatabaseConnection()
        query = """
            SELECT 
                cp.payment_status,
                cp.receivable_id,
                ar.amount as total_amount,
                ar.amount_due,
                ar.status as ar_status,
                ar.due_date
            FROM challenge_participants cp
            LEFT JOIN accounts_receivable ar ON cp.receivable_id = ar.receivable_id
            WHERE cp.user_id = %s AND cp.challenge_id = %s
        """
        
        result = db.execute_query(query, (user_id, challenge_id))
        
        if result:
            return {
                'success': True,
                'payment_status': result['payment_status'],
                'receivable_id': result['receivable_id'],
                'total_amount': float(result['total_amount']) if result['total_amount'] else 0,
                'amount_due': float(result['amount_due']) if result['amount_due'] else 0,
                'ar_status': result['ar_status'],
                'due_date': result['due_date']
            }
        else:
            return {
                'success': False,
                'message': 'Participant not found'
            }
            
    except Exception as e:
        print(f"❌ Error getting payment status: {e}")
        return {
            'success': False,
            'message': str(e)
        }

def get_unpaid_challenge_participants() -> list:
    """
    Get all participants with unpaid or partial payment status
    Used for sending payment reminders
    
    Returns:
        list: List of participants with payment due
    """
    try:
        db = DatabaseConnection()
        query = """
            SELECT 
                cp.user_id,
                cp.challenge_id,
                u.full_name,
                u.username,
                c.name as challenge_name,
                ar.amount_due,
                ar.due_date,
                cp.payment_status
            FROM challenge_participants cp
            JOIN users u ON cp.user_id = u.user_id
            JOIN challenges c ON cp.challenge_id = c.challenge_id
            JOIN accounts_receivable ar ON cp.receivable_id = ar.receivable_id
            WHERE cp.payment_status IN ('unpaid', 'partial')
            AND cp.approval_status = 'approved'
            AND c.status = 'active'
            ORDER BY ar.due_date ASC
        """
        
        results = db.execute_query(query, fetch_all=True)
        return results if results else []
        
    except Exception as e:
        print(f"❌ Error getting unpaid participants: {e}")
        return []

def approve_challenge_participation(user_id: int, challenge_id: int, admin_id: int) -> dict:
    """
    Approve user's participation in a paid challenge
    Creates AR receivable if challenge has entry fee
    
    Args:
        user_id: User ID
        challenge_id: Challenge ID
        admin_id: Admin approving the participation
    
    Returns:
        dict: {'success': bool, 'requires_payment': bool, 'receivable_id': int, 'message': str}
    """
    try:
        db = DatabaseConnection()
        
        # Get challenge details
        challenge_query = """
            SELECT name, price, is_free
            FROM challenges
            WHERE challenge_id = %s
        """
        challenge = db.execute_query(challenge_query, (challenge_id,))
        
        if not challenge:
            return {
                'success': False,
                'requires_payment': False,
                'message': 'Challenge not found'
            }
        
        # Update approval status
        update_query = """
            UPDATE challenge_participants
            SET approval_status = 'approved'
            WHERE user_id = %s AND challenge_id = %s
        """
        db.execute_update(update_query, (user_id, challenge_id))
        
        # If free challenge, set payment status to 'na' and return
        if challenge['is_free'] or challenge['price'] == 0:
            update_payment_query = """
                UPDATE challenge_participants
                SET payment_status = 'na'
                WHERE user_id = %s AND challenge_id = %s
            """
            db.execute_update(update_payment_query, (user_id, challenge_id))
            
            return {
                'success': True,
                'requires_payment': False,
                'message': 'Free challenge participation approved'
            }
        
        # For paid challenges, create AR receivable
        result = create_challenge_receivable(
            user_id=user_id,
            challenge_id=challenge_id,
            challenge_name=challenge['name'],
            amount=float(challenge['price']),
            admin_id=admin_id
        )
        
        if result['success']:
            return {
                'success': True,
                'requires_payment': True,
                'receivable_id': result['receivable_id'],
                'amount': float(challenge['price']),
                'message': 'Paid challenge participation approved. Payment pending.'
            }
        else:
            return {
                'success': False,
                'requires_payment': True,
                'message': result['message']
            }
            
    except Exception as e:
        print(f"❌ Error approving challenge participation: {e}")
        return {
            'success': False,
            'requires_payment': False,
            'message': str(e)
        }

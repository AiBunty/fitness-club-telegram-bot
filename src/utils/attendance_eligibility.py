"""
Attendance eligibility check - reuses existing subscription logic
Enforces grace period rules (3 days max, 3 attendances max if unpaid)
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def check_attendance_eligibility(user_id: int) -> dict:
    """
    Check if user is eligible to mark attendance
    Reuses existing subscription_operations functions
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        {
            'eligible': bool,
            'reason': str,
            'grace_days_left': int,
            'grace_attempts_left': int
        }
    """
    try:
        from src.database.subscription_operations import is_subscription_active, is_in_grace_period
        from src.database.user_operations import get_user
        
        # Get user data
        user = get_user(user_id)
        if not user:
            logger.warning(f"User not found: {user_id}")
            return {
                'eligible': False,
                'reason': 'USER_NOT_FOUND',
                'grace_days_left': 0,
                'grace_attempts_left': 0
            }
        
        # Check subscription status
        if is_subscription_active(user_id):
            logger.debug(f"User {user_id} has active subscription")
            return {
                'eligible': True,
                'reason': 'SUBSCRIPTION_ACTIVE',
                'grace_days_left': 0,
                'grace_attempts_left': 0
            }
        
        # Check if in grace period
        if is_in_grace_period(user_id):
            logger.debug(f"User {user_id} is in grace period")
            
            # Get subscription to check grace period end date
            from src.database.subscription_operations import get_user_subscription
            sub = get_user_subscription(user_id)
            
            if sub and sub.get('grace_period_end'):
                grace_period_end = sub['grace_period_end']
                days_left = max(0, (grace_period_end - datetime.now()).days + 1)
            else:
                days_left = 3  # Default 3 days
            
            # Count attendances in grace period (last 7 days)
            # CRITICAL: Use queue_date not request_date, count only approved attendances
            from src.database.connection import execute_query
            grace_count = execute_query(
                """
                SELECT COUNT(*) as count FROM attendance_queue
                WHERE user_id = %s 
                AND queue_date >= CURRENT_DATE - INTERVAL '7 days'
                AND status = 'approved'
                """,
                (user_id,),
                fetch_one=True
            )
            attendance_count = grace_count.get('count', 0) if grace_count else 0
            attempts_left = max(0, 3 - attendance_count)
            
            # FAIL SAFE: Return min(days_left, attempts_left) to enforce both constraints
            effective_grace_left = min(days_left, attempts_left) if attempts_left > 0 else 0
            
            logger.info(f"User {user_id} grace period: {days_left} days left, {attempts_left} attempts left, effective: {effective_grace_left}")
            
            return {
                'eligible': effective_grace_left > 0,
                'reason': 'GRACE_PERIOD_ACTIVE',
                'grace_days_left': days_left,
                'grace_attempts_left': attempts_left
            }
        
        # Not eligible
        logger.info(f"User {user_id} not eligible: subscription unpaid and grace expired")
        return {
            'eligible': False,
            'reason': 'SUBSCRIPTION_UNPAID',
            'grace_days_left': 0,
            'grace_attempts_left': 0
        }
        
    except Exception as e:
        logger.error(f"Error checking attendance eligibility for user {user_id}: {e}")
        return {
            'eligible': False,
            'reason': 'SERVER_ERROR',
            'grace_days_left': 0,
            'grace_attempts_left': 0
        }

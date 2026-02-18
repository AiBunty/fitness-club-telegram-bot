"""
Subscription Package

Comprehensive subscription management system with 48 handlers managing:
- User subscription flow (plan selection, payment methods)
- Admin approval flow (UPI, cash, credit, split payments)
- Payment verification and screenshots
- Calendar-based date selection
- Accounts receivable integration
"""

# Export conversation handler factories
from src.features.subscription.handlers import (
    get_subscription_conversation_handler,
    get_admin_approval_conversation_handler
)

# Export user commands
from src.features.subscription.payment.core import (
    cmd_subscribe,
    cmd_my_subscription,
    cmd_admin_subscriptions,
)

# Export admin callbacks (used in bot.py, callback_handlers.py)
from src.features.subscription.payment.core import (
    callback_admin_approve_sub,
    callback_approve_sub_standard,
    callback_custom_amount,
    callback_select_end_date,
    callback_reject_sub,
    callback_admin_reject_upi,
    callback_admin_reject_cash,
)

__all__ = [
    # Conversation handlers
    'get_subscription_conversation_handler',
    'get_admin_approval_conversation_handler',
    # User commands
    'cmd_subscribe',
    'cmd_my_subscription',
    'cmd_admin_subscriptions',
    # Admin callbacks
    'callback_admin_approve_sub',
    'callback_approve_sub_standard',
    'callback_custom_amount',
    'callback_select_end_date',
    'callback_reject_sub',
    'callback_admin_reject_upi',
    'callback_admin_reject_cash',
]

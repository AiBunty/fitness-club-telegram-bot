"""
Central wrappers for approving payments and credit across different order types.

Provides small wrappers to unify calling sites without changing existing DB APIs.
"""
import logging
from src.database.store_operations import apply_order_payment, apply_order_credit
from src.database.shake_operations import mark_shake_paid, mark_shake_credit_terms, approve_user_payment
from src.database.event_operations import confirm_registration

logger = logging.getLogger(__name__)


def approve_store_payment(order_id: int, amount: float, method: str, admin_id: int, reference: str = None):
    return apply_order_payment(order_id, amount, method, admin_id=admin_id, reference=reference)


def approve_store_credit(order_id: int, admin_id: int, due_days: int = 7):
    return apply_order_credit(order_id, admin_id, due_days=due_days)


def approve_shake_payment(shake_id: int, admin_id: int):
    return mark_shake_paid(shake_id, admin_id)


def approve_shake_credit(shake_id: int, admin_id: int, due_days: int = 7):
    return mark_shake_credit_terms(shake_id, admin_id)


def confirm_event_registration(registration_id: int, admin_id: int):
    return confirm_registration(registration_id, admin_id, record_revenue=True)

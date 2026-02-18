"""
Subscription Conversation Handlers

Factory functions that create ConversationHandler instances for:
- User subscription flow (subscribe, plan selection, payment)
- Admin approval flow (approve/reject subscriptions)
"""

from telegram.ext import ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from src.features.subscription.constants import (
    SELECT_PLAN, CONFIRM_PLAN, SELECT_PAYMENT, ENTER_UPI_VERIFICATION,
    ADMIN_APPROVE_SUB, ADMIN_ENTER_AMOUNT, ADMIN_SELECT_DATE,
    ENTER_SPLIT_UPI_AMOUNT, ENTER_SPLIT_CONFIRM, ADMIN_ENTER_BILL,
    ADMIN_ENTER_UPI_RECEIVED, ADMIN_ENTER_CASH_RECEIVED, ADMIN_FINAL_CONFIRM
)

# Import all handlers from core module
from src.features.subscription.payment.core import (
    cmd_subscribe, callback_start_subscribe, callback_select_plan,
    callback_confirm_subscription, callback_cancel_subscription,
    callback_select_payment_method, handle_split_upi_amount_input,
    callback_split_confirm_or_cancel, callback_split_upi_upload_screenshot,
    callback_split_upi_skip_screenshot, callback_upi_upload_screenshot,
    callback_upi_skip_screenshot, callback_upi_submit_with_screenshot,
    handle_upi_screenshot_upload, handle_custom_amount, callback_select_end_date,
    callback_admin_approve_upi, callback_admin_approve_cash,
    callback_admin_approve_split_upi, callback_admin_confirm_split_cash,
    callback_admin_reject_split, callback_admin_approve_credit,
    callback_admin_reject_credit, handle_approval_amount,
    handle_admin_enter_bill, handle_admin_enter_upi_received,
    handle_admin_enter_cash_received, callback_approve_with_date,
    callback_calendar_nav, callback_admin_final_confirm,
    callback_admin_cancel_approval
)


def get_subscription_conversation_handler():
    """Get conversation handler for subscriptions"""
    return ConversationHandler(
        entry_points=[
            CommandHandler('subscribe', cmd_subscribe),
            CallbackQueryHandler(callback_start_subscribe, pattern="^start_subscribe$")
        ],
        states={
            SELECT_PLAN: [
                CallbackQueryHandler(callback_select_plan, pattern="^sub_plan_"),
            ],
            CONFIRM_PLAN: [
                CallbackQueryHandler(callback_confirm_subscription, pattern="^sub_confirm_yes$"),
                CallbackQueryHandler(callback_cancel_subscription, pattern="^sub_cancel$"),
            ],
            SELECT_PAYMENT: [
                CallbackQueryHandler(callback_select_payment_method, pattern="^pay_method_"),
                CallbackQueryHandler(callback_cancel_subscription, pattern="^sub_cancel$"),
            ],
            ENTER_UPI_VERIFICATION: [
                CallbackQueryHandler(callback_split_upi_upload_screenshot, pattern="^split_upi_upload_screenshot$"),
                CallbackQueryHandler(callback_split_upi_skip_screenshot, pattern="^split_upi_skip_screenshot$"),
                CallbackQueryHandler(callback_upi_upload_screenshot, pattern="^upi_upload_screenshot$"),
                CallbackQueryHandler(callback_upi_skip_screenshot, pattern="^upi_skip_screenshot$"),
                CallbackQueryHandler(callback_upi_submit_with_screenshot, pattern="^upi_submit_with_screenshot$"),
                MessageHandler(filters.PHOTO, handle_upi_screenshot_upload),
                CallbackQueryHandler(callback_cancel_subscription, pattern="^sub_cancel$"),
            ],
            ADMIN_ENTER_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_amount),
            ],
            ADMIN_SELECT_DATE: [
                CallbackQueryHandler(callback_select_end_date, pattern="^sub_date_"),
            ],
            ENTER_SPLIT_UPI_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_split_upi_amount_input),
            ],
            ENTER_SPLIT_CONFIRM: [
                CallbackQueryHandler(callback_split_confirm_or_cancel, pattern="^split_(confirm|cancel)$"),
            ],
        },
        fallbacks=[],
        per_message=False,
        conversation_timeout=600,  # 10 minutes timeout to prevent stuck states
        per_chat=True,  # CRITICAL: Isolate conversations per chat for 200+ users
        per_user=True   # CRITICAL: Isolate conversations per user
    )


def get_admin_approval_conversation_handler():
    """Get conversation handler for admin subscription approval"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(callback_admin_approve_upi, pattern="^admin_approve_upi_"),
            CallbackQueryHandler(callback_admin_approve_cash, pattern="^admin_approve_cash_"),
            CallbackQueryHandler(callback_admin_approve_split_upi, pattern="^admin_approve_split_upi_"),
            CallbackQueryHandler(callback_admin_confirm_split_cash, pattern="^admin_confirm_split_cash_"),
            CallbackQueryHandler(callback_admin_reject_split, pattern="^admin_reject_split_"),
            CallbackQueryHandler(callback_admin_approve_credit, pattern="^admin_approve_credit_"),
            CallbackQueryHandler(callback_admin_reject_credit, pattern="^admin_reject_credit_"),
        ],
        states={
            ADMIN_ENTER_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_approval_amount),
            ],
            ADMIN_ENTER_BILL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_enter_bill),
            ],
            ADMIN_ENTER_UPI_RECEIVED: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_enter_upi_received),
            ],
            ADMIN_ENTER_CASH_RECEIVED: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_enter_cash_received),
            ],
            ADMIN_SELECT_DATE: [
                CallbackQueryHandler(callback_approve_with_date, pattern="^approve_date_"),
                CallbackQueryHandler(callback_calendar_nav, pattern="^cal_(prev|next)_"),
            ],
            ADMIN_FINAL_CONFIRM: [
                CallbackQueryHandler(callback_admin_final_confirm, pattern="^admin_final_confirm_"),
                CallbackQueryHandler(callback_admin_cancel_approval, pattern="^admin_cancel_approval_"),
            ],
        },
        fallbacks=[],
        per_message=False,
        per_chat=True,
        per_user=True
    )

"""
User Subscription Flow Handlers

Handles user-facing subscription commands:
- /subscribe - View and select subscription plans
- /my_subscription - View current subscription status
- Plan selection, confirmation, and payment method selection
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from src.database.subscription_operations import (
    SUBSCRIPTION_PLANS,
    create_subscription_request,
    get_user_pending_subscription_request,
    get_user_subscription,
    is_subscription_active,
    is_in_grace_period,
    is_subscription_expired
)
from src.database.user_operations import get_user
from src.features.subscription.constants import (
    SELECT_PLAN,
    CONFIRM_PLAN,
    SELECT_PAYMENT,
    ENTER_UPI_VERIFICATION,
    ENTER_SPLIT_UPI_AMOUNT,
    ENTER_SPLIT_CONFIRM
)

logger = logging.getLogger(__name__)


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start subscription selection (handles /subscribe command and start_subscribe button)"""
    user_id = update.effective_user.id
    logger.info(f"[SUB] cmd_subscribe triggered for user {user_id}")
    
    # Check if already subscribed
    current_sub = get_user_subscription(user_id)
    if current_sub and is_subscription_active(user_id):
        # Handle both callback query and message
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "✅ *You Already Have an Active Subscription*\n\n"
                f"End Date: {current_sub['end_date'].strftime('%d-%m-%Y')}\n"
                f"Amount: Rs. {current_sub['amount']}\n"
                f"Plan: {SUBSCRIPTION_PLANS[current_sub['plan_id']]['name']}\n\n"
                "Use /my_subscription to view details",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "✅ *You Already Have an Active Subscription*\n\n"
                f"End Date: {current_sub['end_date'].strftime('%d-%m-%Y')}\n"
                f"Amount: Rs. {current_sub['amount']}\n"
                f"Plan: {SUBSCRIPTION_PLANS[current_sub['plan_id']]['name']}\n\n"
                "Use /my_subscription to view details",
                parse_mode="Markdown"
            )
        return ConversationHandler.END
    
    # Check if there's a pending subscription request
    pending_request = get_user_pending_subscription_request(user_id)
    
    if pending_request:
        payment_method = pending_request['payment_method'].upper()
        message = (
            f"⏳ *{payment_method} Payment - Awaiting Admin Approval*\n\n"
            f"Plan: {SUBSCRIPTION_PLANS[pending_request['plan_id']]['name']}\n"
            f"Amount: Rs. {pending_request['amount']}\n\n"
            "Your payment request is being reviewed by our admin team.\n"
            "You'll receive a notification once it's approved.\n\n"
            "Please wait... do not submit another request."
        )
        
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(message, parse_mode="Markdown")
        else:
            await update.message.reply_text(message, parse_mode="Markdown")
        return ConversationHandler.END
    
    # Show subscription plans
    keyboard = [
        [InlineKeyboardButton("📅 30 Days - Rs.2,500", callback_data="sub_plan_30")],
        [InlineKeyboardButton("📅 90 Days - Rs.7,000", callback_data="sub_plan_90")],
        [InlineKeyboardButton("📅 180 Days - Rs.13,500", callback_data="sub_plan_180")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        "*💪 Gym Subscription Plans*\n\n"
        "Select a subscription plan to get full access to the app:\n\n"
        "🏋️ *Plan Benefits:*\n"
        "• Full app access\n"
        "• Activity tracking\n"
        "• Weight tracking\n"
        "• Challenge participation\n"
        "• Shake orders\n"
        "• Check-in tracking\n\n"
        "Choose your plan below:"
    )
    
    # Handle callback query vs message
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    
    return SELECT_PLAN


async def callback_start_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Subscribe Now' button from /start message"""
    return await cmd_subscribe(update, context)


async def callback_select_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plan selection"""
    query = update.callback_query
    user_id = query.from_user.id
    logger.info(f"[SUB] callback_select_plan triggered for user {user_id}, callback_data={query.data}")
    
    # Extract plan from callback data: "sub_plan_30" -> "plan_30"
    plan_id = "_".join(query.data.split("_")[1:])  # "plan_30"
    
    if not plan_id.startswith("plan_"):
        logger.error(f"Invalid plan callback data for user {user_id}: {query.data}")
        await query.answer("Invalid plan selected", show_alert=True)
        return SELECT_PLAN
    
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    if not plan:
        logger.error(f"Plan {plan_id} not found in SUBSCRIPTION_PLANS")
        await query.answer("Plan not found", show_alert=True)
        return SELECT_PLAN
    
    context.user_data['selected_plan_id'] = plan_id
    context.user_data['selected_plan'] = plan
    logger.info(f"User {user_id} selected plan {plan_id}: {plan['name']}")
    
    await query.answer()
    
    end_date = datetime.now() + timedelta(days=plan['duration_days'])
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm & Subscribe", callback_data="sub_confirm_yes")],
        [InlineKeyboardButton("❌ Cancel", callback_data="sub_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"*📋 Confirm Your Subscription*\n\n"
        f"Plan: {plan['name']}\n"
        f"Duration: {plan['duration_days']} days\n"
        f"Amount: Rs. {plan['amount']:,}\n\n"
        f"Please review and confirm your subscription."
    )
    
    try:
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
        logger.info(f"Confirmation message shown to user {user_id} for plan {plan_id}")
    except Exception as e:
        logger.error(f"Error editing message for user {user_id}: {e}")
        await query.answer("Error loading plan details. Please try again.", show_alert=True)
        return SELECT_PLAN
    
    return CONFIRM_PLAN


async def callback_cancel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel subscription"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("❌ Subscription cancelled.")
    return ConversationHandler.END

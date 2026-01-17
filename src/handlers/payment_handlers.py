import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from src.database.payment_operations import (
    record_fee_payment, get_user_fee_status, get_pending_payments
)
from src.database.challenges_operations import (
    get_active_challenges, join_challenge, get_challenge_progress,
    get_challenge_leaderboard
)
from src.database.notifications_operations import send_payment_due_notification
from src.utils.guards import check_approval

logger = logging.getLogger(__name__)

# Payment conversation states
PAYMENT_AMOUNT, PAYMENT_METHOD, PAYMENT_CONFIRM = range(3)

# Challenge states
CHALLENGE_SELECT = 1

async def cmd_payment_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's payment status"""
    # Check if approved first
    if not await check_approval(update, context):
        return
    
    user_id = update.effective_user.id
    
    status = get_user_fee_status(user_id)
    
    if not status:
        await update.message.reply_text("Please register first using /start")
        return
    
    message = "💳 *Payment Status*\n\n"
    
    if status['fee_status'] == 'paid':
        message += f"Status: ✅ PAID\n"
        if status['fee_expiry_date']:
            message += f"Valid Until: {status['fee_expiry_date']}\n"
    else:
        message += f"Status: ❌ UNPAID\n"
        message += "Your membership is inactive.\n"
    
    keyboard = [[InlineKeyboardButton("💰 Pay Membership Fee", callback_data="pay_fee")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

async def cmd_challenges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active challenges"""
    # Check if approved first
    if not await check_approval(update, context):
        return
    
    user_id = update.effective_user.id
    
    challenges = get_active_challenges()
    
    if not challenges:
        await update.message.reply_text("🏆 No active challenges at the moment.")
        return
    
    keyboard = []
    for challenge in challenges:
        keyboard.append([
            InlineKeyboardButton(
                f"🏆 {challenge['challenge_type']}",
                callback_data=f"join_challenge_{challenge['challenge_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ Close", callback_data="close")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "🏆 *Active Challenges*\n\n"
    for challenge in challenges:
        message += f"• {challenge['challenge_type']}\n"
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

async def callback_pay_fee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start payment process"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    keyboard = [["₹500 (30 days)", "₹1000 (60 days)"], ["₹1500 (90 days)", "❌ Cancel"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    await query.edit_message_text(
        text="💳 *Select Membership Duration*\n\n30 Days: ₹500\n60 Days: ₹1000\n90 Days: ₹1500",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return PAYMENT_AMOUNT

async def get_payment_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process payment amount selection"""
    text = update.message.text
    
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Payment cancelled.")
        return ConversationHandler.END
    
    payment_map = {
        "₹500 (30 days)": (500, 30),
        "₹1000 (60 days)": (1000, 60),
        "₹1500 (90 days)": (1500, 90),
    }
    
    if text not in payment_map:
        await update.message.reply_text("❌ Invalid selection. Please select again.")
        return PAYMENT_AMOUNT
    
    amount, days = payment_map[text]
    context.user_data['payment_amount'] = amount
    context.user_data['payment_days'] = days
    
    keyboard = [["💳 Card", "🏦 Bank Transfer", "❌ Cancel"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    await update.message.reply_text(
        f"💰 Amount: ₹{amount}\nDuration: {days} days\n\nSelect payment method:",
        reply_markup=reply_markup
    )
    
    return PAYMENT_METHOD

async def get_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process payment method and confirm"""
    text = update.message.text
    
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Payment cancelled.")
        return ConversationHandler.END
    
    if text not in ["💳 Card", "🏦 Bank Transfer"]:
        await update.message.reply_text("❌ Invalid selection.")
        return PAYMENT_METHOD
    
    context.user_data['payment_method'] = text
    
    keyboard = [["✅ Confirm", "❌ Cancel"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    message = f"💳 *Payment Summary*\n\n"
    message += f"Amount: ₹{context.user_data['payment_amount']}\n"
    message += f"Duration: {context.user_data['payment_days']} days\n"
    message += f"Method: {text}\n\n"
    message += "Confirm payment?"
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    
    return PAYMENT_CONFIRM

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and process payment"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "❌ Cancel":
        await update.message.reply_text("❌ Payment cancelled.")
        return ConversationHandler.END
    
    if text != "✅ Confirm":
        await update.message.reply_text("❌ Invalid selection.")
        return PAYMENT_CONFIRM
    
    # Record payment
    result = record_fee_payment(
        user_id,
        amount=context.user_data['payment_amount'],
        payment_method=context.user_data['payment_method'],
        duration_days=context.user_data['payment_days'],
        notes=f"Payment via {context.user_data['payment_method']}"
    )
    
    if result:
        await update.message.reply_text(
            f"✅ *Payment Successful!*\n\n"
            f"Amount: ₹{context.user_data['payment_amount']}\n"
            f"Duration: {context.user_data['payment_days']} days\n"
            f"Status: ACTIVE ✅\n\n"
            f"Your membership is now active!",
            reply_markup=None,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Payment failed. Please try again.")
    
    context.user_data.clear()
    return ConversationHandler.END

async def callback_join_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Join a challenge"""
    query = update.callback_query
    user_id = query.from_user.id
    
    challenge_id = int(query.data.split("_")[-1])
    
    result = join_challenge(user_id, challenge_id)
    
    if result:
        await query.answer("✅ Joined challenge!", show_alert=False)
        
        progress = get_challenge_progress(challenge_id, user_id)
        
        message = f"✅ *Challenge Joined!*\n\n"
        message += f"Challenge: {progress['challenge_type']}\n"
        message += f"Your Progress: {progress['progress'] or 0}\n"
        
        keyboard = [[InlineKeyboardButton("🏆 Leaderboard", 
                    callback_data=f"challenge_board_{challenge_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await query.answer("❌ Failed to join challenge.", show_alert=True)

async def callback_challenge_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show challenge leaderboard"""
    query = update.callback_query
    
    challenge_id = int(query.data.split("_")[-1])
    
    leaderboard = get_challenge_leaderboard(challenge_id)
    
    message = "🏆 *Challenge Leaderboard*\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    
    if leaderboard:
        for i, member in enumerate(leaderboard[:10], 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            message += f"{medal} {member['full_name']}: {member['progress_value']} pts\n"
    
    keyboard = [[InlineKeyboardButton("📱 Back", callback_data="challenges")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close dialog"""
    query = update.callback_query
    await query.answer()
    await query.delete_message()

async def cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel payment flow"""
    await update.message.reply_text("❌ Payment cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

"""
Shake Credit Handlers
Handles shake credit purchasing, checking balance, and ordering
"""

import logging
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from src.database.shake_credits_operations import (
    get_user_credits, create_purchase_request, consume_credit, get_shake_report,
    CREDIT_COST, CREDITS_PER_PURCHASE
)
from src.database.user_operations import user_exists, get_user
from src.database.shake_operations import get_shake_flavors, request_shake
from src.utils.auth import is_admin_id, check_user_approved
from src.config import POINTS_CONFIG

logger = logging.getLogger(__name__)

# Conversation states
BUY_CREDITS, CONFIRM_PURCHASE, ORDER_SHAKE_FLAVOR, ADMIN_SELECT_USER_DATE = range(4)


async def cmd_buy_shake_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start shake credit purchase"""
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    user_id = update.effective_user.id
    
    if not user_exists(user_id):
        await message.reply_text("❌ You must register first. Use /start")
        return ConversationHandler.END
    if not check_user_approved(user_id):
        await message.reply_text(
            "⏳ Registration pending approval. Please contact admin before buying credits."
        )
        return ConversationHandler.END
    
    # Show purchase options
    keyboard = [
        [InlineKeyboardButton("✅ 25 Credits", callback_data="confirm_buy_25")],
        [InlineKeyboardButton("ℹ️ View Options", callback_data="shake_credit_info")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
    ]
    
    await message.reply_text(
        f"🥤 *Buy Shake Credits*\n\n"
        f"💵 Price: Rs {CREDIT_COST} for {CREDITS_PER_PURCHASE} credits\n"
        f"💰 Cost per credit: Rs {CREDIT_COST // CREDITS_PER_PURCHASE}\n\n"
        f"Select an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return BUY_CREDITS


async def cmd_check_shake_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check user's shake credit balance"""
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    user_id = update.effective_user.id
    
    if not user_exists(user_id):
        await message.reply_text("❌ You must register first. Use /start")
        return
    if not check_user_approved(user_id):
        await message.reply_text(
            "⏳ Registration pending approval. Please contact admin to unlock shake credits."
        )
        return
    
    credits = get_user_credits(user_id)
    user = get_user(user_id)
    
    if credits:
        message_text = (
            f"🥤 *Shake Credits Balance*\n\n"
            f"👤 User: {user['full_name']}\n"
            f"💾 Total Credits Purchased: {credits['total_credits']}\n"
            f"✅ Available Credits: {credits['available_credits']}\n"
            f"❌ Used Credits: {credits['used_credits']}\n"
            f"⏰ Last Updated: {credits['last_updated'].strftime('%d-%m-%Y %H:%M') if credits['last_updated'] else 'N/A'}\n"
        )
        
        if credits['available_credits'] > 0:
            keyboard = [
                [InlineKeyboardButton("🥛 Order Shake", callback_data="cmd_order_shake")],
                [InlineKeyboardButton("📊 Shake Report", callback_data="cmd_shake_report")],
                [InlineKeyboardButton("🔄 Refresh", callback_data="cmd_check_shake_credits")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("💳 Buy Credits", callback_data="cmd_buy_shake_credits")],
                [InlineKeyboardButton("📊 Shake Report", callback_data="cmd_shake_report")],
                [InlineKeyboardButton("🔄 Refresh", callback_data="cmd_check_shake_credits")]
            ]
        
        await message.reply_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await message.reply_text("❌ Failed to retrieve credits. Try again.")


async def cmd_order_shake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Order shake if user has credits"""
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
        user_id = update.callback_query.from_user.id
    else:
        message = update.message
        user_id = update.message.from_user.id
    
    if not user_exists(user_id):
        await message.reply_text("❌ You must register first. Use /start")
        return ConversationHandler.END
    if not check_user_approved(user_id):
        await message.reply_text(
            "⏳ Registration pending approval. Please contact admin before ordering shakes."
        )
        return ConversationHandler.END
    
    # Check credits
    credits = get_user_credits(user_id)
    
    if not credits or credits['available_credits'] <= 0:
        await message.reply_text(
            "❌ *No Credits Available*\n\n"
            "You need at least 1 credit to order a shake.\n"
            "Tap 'Buy Credits' to purchase credits.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Show flavors
    flavors = get_shake_flavors()
    
    if not flavors:
        await message.reply_text("❌ No shake flavors available.")
        return ConversationHandler.END
    
    keyboard = []
    for flavor in flavors:
        button_text = f"{flavor['name']} 🥤"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"order_flavor_{flavor['flavor_id']}")])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="main_menu")])
    
    await message.reply_text(
        f"🥤 *Order Shake*\n\n"
        f"✅ Available Credits: {credits['available_credits']}\n\n"
        f"Select your shake flavor:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return ORDER_SHAKE_FLAVOR


async def process_shake_order(user_id: int, flavor_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Process shake order and deduct credit"""
    if not check_user_approved(user_id):
        logger.info(f"Shake order blocked; user {user_id} pending approval")
        return False
    try:
        # Create shake request
        result = request_shake(user_id, flavor_id, notes="Ordered with credit")
        
        if result:
            # Deduct credit
            if consume_credit(user_id, f"Shake ordered - Flavor ID: {flavor_id}"):
                logger.info(f"Shake order processed for user {user_id}, credit deducted")
                return True
            else:
                logger.error(f"Failed to deduct credit for user {user_id}")
                return False
        
        return False
    except Exception as e:
        logger.error(f"Failed to process shake order: {e}")
        return False


async def cmd_shake_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed shake credit report"""
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    user_id = update.effective_user.id
    
    if not user_exists(user_id):
        await message.reply_text("❌ You must register first. Use /start")
        return
    if not check_user_approved(user_id):
        await message.reply_text(
            "⏳ Registration pending approval. Please contact admin before viewing shake credits."
        )
        return
    
    report = get_shake_report(user_id)
    
    if report:
        credits = report['current_balance']
        transactions = report['transactions']
        
        # Build report text
        report_text = (
            f"📊 *Shake Credits Report*\n\n"
            f"💾 Total Credits Purchased: {credits['total_credits']}\n"
            f"✅ Available Credits: {credits['available_credits']}\n"
            f"❌ Used Credits: {credits['used_credits']}\n\n"
            f"📋 *Transaction History:*\n"
        )
        
        if transactions:
            for txn in transactions[:10]:  # Show last 10 transactions
                date_str = txn['reference_date'].strftime('%d-%m-%Y') if txn['reference_date'] else txn['created_at'].strftime('%d-%m-%Y')
                change_symbol = "➕" if txn['credit_change'] > 0 else "➖"
                report_text += f"{change_symbol} {txn['transaction_type']}: {txn['credit_change']} credits ({date_str})\n"
            
            if len(transactions) > 10:
                report_text += f"\n... and {len(transactions) - 10} more transactions"
        else:
            report_text += "No transactions yet."
        
        await message.reply_text(report_text, parse_mode='Markdown')
    else:
        await message.reply_text("❌ Failed to generate report.")


async def cmd_admin_pending_purchases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Show pending shake credit purchases"""
    user_id = update.effective_user.id
    
    if not is_admin_id(user_id):
        await update.message.reply_text("❌ Admin access only.")
        return
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    from src.database.shake_credits_operations import get_pending_purchase_requests
    
    purchases = get_pending_purchase_requests()
    
    if not purchases:
        await message.reply_text("✅ No pending shake credit purchase requests!")
        return
    
    # Show first purchase
    purchase = purchases[0]
    
    purchase_text = (
        f"💳 *Shake Credit Purchase Request*\n\n"
        f"👤 User: {purchase['full_name']}\n"
        f"📱 @{purchase['telegram_username'] or 'unknown'}\n"
        f"🥤 Credits: {purchase['credits_requested']}\n"
        f"💵 Amount: Rs {purchase['amount']}\n"
        f"📅 Requested: {purchase['created_at'].strftime('%d-%m-%Y %H:%M')}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_purchase_{purchase['purchase_id']}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"reject_purchase_{purchase['purchase_id']}")],
    ]
    
    await message.reply_text(
        purchase_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

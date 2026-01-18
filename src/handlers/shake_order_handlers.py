"""
Enhanced Shake Order Handler with Approval Workflow
Handles: Order selection, admin approval, confirmation messages with details
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from src.database.user_operations import user_exists, get_user, get_user_approval_status
from src.database.shake_operations import (
    get_shake_flavors, request_shake, approve_shake, complete_shake,
    get_pending_shakes, get_user_shake_count
)
from src.database.shake_credits_operations import (
    get_user_credits, consume_credit
)
from src.utils.auth import is_admin_id, is_staff
from src.utils.role_notifications import get_moderator_chat_ids
from src.config import SUPER_ADMIN_USER_ID

logger = logging.getLogger(__name__)

# Conversation states
ORDER_SHAKE_FLAVOR, CONFIRM_SHAKE_ORDER = range(2)


async def cmd_order_shake_enhanced(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Enhanced shake order with menu selection
    Shows: Kulfi, Strawberry, Vanilla, Dutch Chocolate, Mango, Orange Cream, Paan, Rose Kheer, Banana Caramel
    """
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
        user_id = update.callback_query.from_user.id
    else:
        message = update.message
        user_id = update.message.from_user.id
    
    # 1. Verify user is registered
    if not user_exists(user_id):
        await message.reply_text("❌ You must register first. Use /start")
        return ConversationHandler.END
    
    # 2. Verify user is approved
    if not check_user_approved(user_id):
        await message.reply_text(
            "⏳ *Registration Pending Approval*\n\n"
            "Your account is still pending admin approval.\n"
            "You'll be able to order shakes once approved.\n\n"
            "Please contact admin for faster approval.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # 3. Check credits
    credits = get_user_credits(user_id)
    available_credits = credits['available_credits'] if credits else 0
    
    if not credits or available_credits <= 0:
        await message.reply_text(
            "❌ *No Shake Credits*\n\n"
            "You need at least 1 credit to order a shake.\n\n"
            "💾 *To buy credits:* Tap 'Buy Credits' from your menu.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Buy Credits", callback_data="cmd_buy_shake_credits")],
                [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
            ])
        )
        return ConversationHandler.END
    
    # 4. Get and display shake menu
    flavors = get_shake_flavors()
    
    if not flavors:
        await message.reply_text("❌ No shake flavors available at the moment.")
        return ConversationHandler.END
    
    # Create menu grid (3 items per row for better UI)
    keyboard = []
    row = []
    for flavor in flavors:
        flavor_name = flavor.get('name') or flavor.get('flavor_name') or 'Unknown'
        flavor_id = flavor.get('flavor_id') or flavor.get('id')
        
        button_text = f"🥤 {flavor_name}"
        row.append(InlineKeyboardButton(button_text, callback_data=f"order_flavor_{flavor_id}"))
        
        # Create 2-column layout
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    # Add remaining items
    if row:
        keyboard.append(row)
    
    # Add cancel button
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="main_menu")])
    
    menu_text = (
        "🥤 *Order Your Shake*\n\n"
        f"✅ *Available Credits:* {available_credits}\n"
        f"📊 *Shakes This Month:* {get_user_shake_count(user_id, 30)}\n\n"
        "Select your favorite shake from the menu below:\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "• Kulfi - Traditional ice cream\n"
        "• Strawberry - Fresh & fruity\n"
        "• Vanilla - Classic taste\n"
        "• Dutch Chocolate - Rich & dark\n"
        "• Mango - Tropical flavor\n"
        "• Orange Cream - Citrus smoothness\n"
        "• Paan - Traditional flavor\n"
        "• Rose Kheer - Dessert shake\n"
        "• Banana Caramel - Sweet combo\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    await message.reply_text(
        menu_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return ORDER_SHAKE_FLAVOR


async def process_shake_flavor_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle flavor selection and create shake request"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    callback_data = query.data
    
    # Extract flavor ID from callback
    flavor_id = int(callback_data.split("_")[-1])
    
    # Verify user still has credits
    credits = get_user_credits(user_id)
    if not credits or credits['available_credits'] <= 0:
        await query.edit_message_text(
            "❌ You no longer have available credits to place an order.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Store selection in context
    context.user_data['selected_flavor_id'] = flavor_id
    
    # Get flavor name
    flavors = get_shake_flavors()
    flavor_name = None
    for flavor in flavors:
        if flavor.get('flavor_id') == flavor_id or flavor.get('id') == flavor_id:
            flavor_name = flavor.get('name') or flavor.get('flavor_name')
            break
    
    if not flavor_name:
        flavor_name = f"Flavor #{flavor_id}"
    
    # Show confirmation message
    user = get_user(user_id)
    current_balance = credits['available_credits']
    
    confirmation_text = (
        "✅ *Shake Order Summary*\n\n"
        f"👤 *Name:* {user['full_name']}\n"
        f"🥤 *Selected:* {flavor_name}\n"
        f"💳 *Credits Deduction:* -1\n"
        f"💰 *Current Balance:* {current_balance}\n"
        f"💰 *Balance After:* {current_balance - 1}\n"
        f"📅 *Date:* {datetime.now().strftime('%d-%b-%Y')}\n"
        f"⏰ *Time:* {datetime.now().strftime('%I:%M %p')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⏳ *Status:* Pending Admin Approval\n\n"
        "Your shake request has been sent to the admin for approval.\n"
        "Once approved and prepared, you'll receive a confirmation! 🥤"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm Order", callback_data=f"confirm_shake_{flavor_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        confirmation_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return CONFIRM_SHAKE_ORDER


async def confirm_shake_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm shake order and send to admin for approval"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    callback_data = query.data
    
    # Extract flavor ID
    flavor_id = int(callback_data.split("_")[-1])
    
    # Create shake request
    shake_request = request_shake(user_id, flavor_id, notes="Ordered from menu")
    
    if not shake_request:
        await query.edit_message_text(
            "❌ Failed to create shake request. Please try again.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    shake_id = shake_request.get('shake_request_id') or shake_request.get('id')
    
    # Deduct credit
    credit_deducted = consume_credit(user_id, f"Shake {flavor_id} ordered")
    
    if not credit_deducted:
        logger.error(f"Failed to deduct credit for user {user_id}")
        await query.edit_message_text(
            "⚠️ Shake request created but credit deduction failed. Contact admin.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Get user and flavor info
    user = get_user(user_id)
    flavors = get_shake_flavors()
    flavor_name = None
    for flavor in flavors:
        if flavor.get('flavor_id') == flavor_id or flavor.get('id') == flavor_id:
            flavor_name = flavor.get('name') or flavor.get('flavor_name')
            break
    
    if not flavor_name:
        flavor_name = f"Flavor #{flavor_id}"
    
    credits_after = get_user_credits(user_id)
    balance_after = credits_after['available_credits'] if credits_after else 0
    
    # Send confirmation to user
    user_confirmation = (
        "✅ *Shake Order Placed Successfully!*\n\n"
        f"🥤 *Flavor:* {flavor_name}\n"
        f"💳 *Credits Deducted:* 1\n"
        f"💰 *Remaining Balance:* {balance_after}\n"
        f"📅 *Date:* {datetime.now().strftime('%d-%b-%Y')}\n"
        f"⏰ *Time:* {datetime.now().strftime('%I:%M %p')}\n"
        f"📋 *Request ID:* #{shake_id}\n\n"
        "⏳ Your order is pending admin approval.\n"
        "You'll receive a notification once it's ready for pickup! 🎉"
    )
    
    await query.edit_message_text(
        user_confirmation,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Check Balance", callback_data="cmd_check_shake_credits")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ])
    )
    
    # Send notification to admin with Paid/Credit decision
    admin_text = (
        "🔔 *NEW SHAKE ORDER - PAYMENT TERMS DECISION REQUIRED*\n\n"
        f"👤 *User:* {user['full_name']}\n"
        f"📱 *Telegram ID:* {user_id}\n"
        f"🥤 *Flavor:* {flavor_name}\n"
        f"📋 *Request ID:* #{shake_id}\n"
        f"📅 *Date:* {datetime.now().strftime('%d-%b-%Y')}\n"
        f"⏰ *Time:* {datetime.now().strftime('%I:%M %p')}\n"
        f"💳 *Credit Deducted:* 1 (Balance: {balance_after})\n\n"
        "⚠️ *ACTION REQUIRED:* Choose payment terms\n\n"
        "💵 *Paid* - User pays cash/online now\n"
        "📋 *Credit Terms* - Start payment reminder follow-up"
    )
    
    # Get admin chat IDs and send notification
    try:
        admin_ids = get_moderator_chat_ids()
        if admin_ids:
            for admin_id in admin_ids:
                try:
                    keyboard = [
                        [InlineKeyboardButton("💵 Paid", callback_data=f"shake_paid_{shake_id}")],
                        [InlineKeyboardButton("📋 Credit Terms", callback_data=f"shake_credit_terms_{shake_id}")],
                        [InlineKeyboardButton("❌ Cancel Order", callback_data=f"cancel_shake_{shake_id}")]
                    ]
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=admin_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification to admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Failed to get admin IDs: {e}")
    
    logger.info(f"Shake order {shake_id} placed by user {user_id}, flavor {flavor_id}")
    
    return ConversationHandler.END


async def admin_approve_shake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin approves shake order
    Sends confirmation to both user and admin with details
    """
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    callback_data = query.data
    
    # Extract shake ID
    shake_id = int(callback_data.split("_")[-1])
    
    # Verify admin
    if not is_admin_id(admin_id) and admin_id != SUPER_ADMIN_USER_ID:
        await query.answer("❌ Unauthorized", show_alert=True)
        return
    
    # Approve shake
    result = approve_shake(shake_id, admin_id)
    
    if not result:
        await query.edit_message_text(
            "❌ Failed to approve shake. Please try again.",
            parse_mode='Markdown'
        )
        return
    
    if result.get('already_processed'):
        await query.answer(
            "⚠️ This shake was already approved",
            show_alert=True
        )
        return
    
    # Extract details
    user_id = result.get('user_id')
    flavor_name = result.get('flavor_name') or f"Flavor #{result.get('flavor_id')}"
    telegram_id = result.get('telegram_id') or user_id
    
    user = get_user(user_id)
    credits_info = get_user_credits(user_id)
    current_balance = credits_info['available_credits'] if credits_info else 0
    
    # Prepare confirmation message for user
    user_confirmation = (
        "✅ *YOUR SHAKE IS READY!*\n\n"
        f"🥤 *Flavor:* {flavor_name}\n"
        f"💳 *Credits Deducted:* 1\n"
        f"💰 *Remaining Balance:* {current_balance}\n"
        f"📅 *Date:* {datetime.now().strftime('%d-%b-%Y')}\n"
        f"⏰ *Time:* {datetime.now().strftime('%I:%M %p')}\n"
        f"📋 *Request ID:* #{shake_id}\n\n"
        "Your shake has been approved and is ready for pickup! 🎉\n"
        "Please collect from the admin desk."
    )
    
    # Prepare confirmation for admin
    admin_confirmation = (
        "✅ *SHAKE APPROVED & READY*\n\n"
        f"👤 *User:* {user['full_name']}\n"
        f"📱 *ID:* {user_id}\n"
        f"🥤 *Flavor:* {flavor_name}\n"
        f"📋 *Request ID:* #{shake_id}\n"
        f"📅 *Date:* {datetime.now().strftime('%d-%b-%Y')}\n"
        f"⏰ *Time:* {datetime.now().strftime('%I:%M %p')}\n"
        f"💰 *Credits Deducted:* 1\n"
        f"💰 *User Balance:* {current_balance}\n\n"
        f"✅ *Status:* READY FOR PICKUP\n\n"
        "Mark as completed once user picks up."
    )
    
    # Send confirmation to user
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=user_confirmation,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Check Balance", callback_data="cmd_check_shake_credits")]
            ])
        )
    except Exception as e:
        logger.error(f"Failed to send confirmation to user {user_id}: {e}")
    
    # Update admin message
    await query.edit_message_text(
        admin_confirmation,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Mark Completed", callback_data=f"complete_shake_{shake_id}")],
            [InlineKeyboardButton("📋 View Pending", callback_data="cmd_pending_shakes")]
        ])
    )
    
    logger.info(f"Shake {shake_id} approved by admin {admin_id}")


async def admin_complete_shake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mark shake as delivered/completed
    Send final confirmation to user
    """
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    callback_data = query.data
    
    # Extract shake ID
    shake_id = int(callback_data.split("_")[-1])
    
    # Get shake details before completing
    pending = get_pending_shakes(50)
    shake_record = None
    for shake in (pending or []):
        if shake.get('shake_request_id') == shake_id or shake.get('id') == shake_id:
            shake_record = shake
            break
    
    if not shake_record:
        await query.answer("❌ Shake not found", show_alert=True)
        return
    
    # Complete shake
    result = complete_shake(shake_id)
    
    if not result:
        await query.edit_message_text("❌ Failed to complete shake.")
        return
    
    # Extract details
    user_id = shake_record.get('user_id')
    flavor_name = shake_record.get('flavor_name') or f"Flavor #{shake_record.get('flavor_id')}"
    
    user = get_user(user_id)
    credits_info = get_user_credits(user_id)
    current_balance = credits_info['available_credits'] if credits_info else 0
    
    # Final confirmation for user
    final_confirmation = (
        "🎉 *SHAKE DELIVERY COMPLETE!*\n\n"
        f"👤 *Name:* {user['full_name']}\n"
        f"🥤 *Flavor:* {flavor_name}\n"
        f"💳 *Credits Deducted:* 1\n"
        f"💰 *Current Balance:* {current_balance}\n"
        f"📅 *Date:* {datetime.now().strftime('%d-%b-%Y')}\n"
        f"⏰ *Time:* {datetime.now().strftime('%I:%M %p')}\n"
        f"📋 *Request ID:* #{shake_id}\n\n"
        "✅ *Status:* COMPLETED\n\n"
        "Thank you for choosing our shakes! 💪\n"
        "Enjoy your shake and keep pushing! 🥤"
    )
    
    # Send final confirmation to user
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=final_confirmation,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to send completion confirmation to user {user_id}: {e}")
    
    # Update admin message
    admin_final = (
        "✅ *SHAKE DELIVERED*\n\n"
        f"👤 *User:* {user['full_name']}\n"
        f"🥤 *Flavor:* {flavor_name}\n"
        f"💰 *Balance Left:* {current_balance}\n"
        f"📋 *ID:* #{shake_id}\n\n"
        "✅ Order completed and delivered!"
    )
    
    await query.edit_message_text(
        admin_final,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 View Pending", callback_data="cmd_pending_shakes")]
        ])
    )
    
    logger.info(f"Shake {shake_id} completed by admin {admin_id}")

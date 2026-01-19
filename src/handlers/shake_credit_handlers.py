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
BUY_CREDITS, CONFIRM_PURCHASE, SELECT_PAYMENT_METHOD, ENTER_UPI_ID, ORDER_SHAKE_FLAVOR, ADMIN_SELECT_USER_DATE, ADMIN_ENTER_AMOUNT = range(7)


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


async def callback_confirm_buy_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirmation and show payment method selection"""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer()
    
    # Store purchase amount
    context.user_data['shake_credits_to_buy'] = CREDITS_PER_PURCHASE
    context.user_data['shake_credits_amount'] = CREDIT_COST
    
    # Show payment method selection
    keyboard = [
        [InlineKeyboardButton("� UPI Payment", callback_data="shake_pay_upi")],
        [InlineKeyboardButton("💵 Cash Payment", callback_data="shake_pay_cash")],
        [InlineKeyboardButton("⏳ Pay Later (Credit)", callback_data="shake_pay_credit")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        f"*💳 Select Payment Method*\n\n"
        f"Credits: {CREDITS_PER_PURCHASE}\n"
        f"Amount: Rs {CREDIT_COST:,}\n\n"
        f"Choose how you'd like to pay:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return SELECT_PAYMENT_METHOD


async def callback_select_shake_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle shake credit payment method selection"""
    query = update.callback_query
    user_id = query.from_user.id
    payment_method = query.data.split("_")[2]  # 'cash', 'upi' or 'credit'
    
    credits = context.user_data.get('shake_credits_to_buy', CREDITS_PER_PURCHASE)
    amount = context.user_data.get('shake_credits_amount', CREDIT_COST)
    
    await query.answer()
    context.user_data['shake_payment_method'] = payment_method
    
    if payment_method == 'cash':
        # Cash payment - create request for admin approval
        purchase_request = create_purchase_request(user_id, credits, 'cash')
        
        if not purchase_request:
            await query.edit_message_text(
                "❌ *Purchase Error*\n\n"
                "Failed to create purchase request. Please try again.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        context.user_data['shake_purchase_id'] = purchase_request['purchase_id']
        
        await query.edit_message_text(
            f"✅ *Purchase Request Created*\n\n"
            f"🥤 Credits: {credits}\n"
            f"💵 Amount: Rs {amount:,.2f}\n"
            f"⏳ Status: Pending Admin Approval\n\n"
            f"Our admin will verify your payment and transfer credits soon.",
            parse_mode='Markdown'
        )
        
        # Notify admins
        try:
            from src.handlers.admin_handlers import get_admin_ids
            from src.database.user_operations import get_user
            
            admin_ids = get_admin_ids()
            user_data = get_user(user_id)
            profile_pic_url = user_data.get('profile_pic_url') if user_data else None
            
            admin_text = (
                f"*💵 Shake Credit Purchase - Cash Payment*\n\n"
                f"User: {query.from_user.full_name} (ID: {user_id})\n"
                f"Credits: {credits}\n"
                f"Amount: Rs {amount:,}\n"
                f"Payment Method: 💵 Cash\n\n"
                f"Request ID: {purchase_request['purchase_id']}\n"
                f"Submitted: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
            )
            
            admin_keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_shake_purchase_{purchase_request['purchase_id']}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_shake_purchase_{purchase_request['purchase_id']}")
                ]
            ]
            
            for admin_id in admin_ids:
                try:
                    if profile_pic_url:
                        try:
                            await context.bot.send_photo(
                                chat_id=admin_id,
                                photo=profile_pic_url,
                                caption=admin_text,
                                reply_markup=InlineKeyboardMarkup(admin_keyboard),
                                parse_mode='Markdown'
                            )
                        except:
                            await context.bot.send_message(
                                chat_id=admin_id,
                                text=admin_text,
                                reply_markup=InlineKeyboardMarkup(admin_keyboard),
                                parse_mode='Markdown'
                            )
                    else:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=admin_text,
                            reply_markup=InlineKeyboardMarkup(admin_keyboard),
                            parse_mode='Markdown'
                        )
                    logger.info(f"Shake credit cash payment notification sent to admin {admin_id}")
                except Exception as e:
                    logger.error(f"Failed to send notification to admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Error sending admin notifications: {e}")
        
        return ConversationHandler.END
    
    elif payment_method == 'upi':
        # UPI payment - generate QR code
        from src.utils.upi_qrcode import generate_upi_qr_code, get_upi_id
        
        qr_path = generate_upi_qr_code(amount, f"ShakeCredits_{user_id}")
        upi_id = get_upi_id()
        
        if not qr_path:
            await query.edit_message_text(
                "❌ Failed to generate UPI QR code. Please try Cash payment or contact admin.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # Create purchase request with UPI method
        purchase_request = create_purchase_request(user_id, credits, 'upi')
        
        if not purchase_request:
            await query.edit_message_text(
                "❌ Failed to create purchase request. Please try again.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        context.user_data['shake_purchase_id'] = purchase_request['purchase_id']
        
        keyboard = [
            [InlineKeyboardButton("✅ I've Paid", callback_data=f"shake_upi_paid_{purchase_request['purchase_id']}")]
        ]
        
        await query.message.reply_photo(
            photo=open(qr_path, 'rb'),
            caption=(
                f"*📱 UPI Payment*\n\n"
                f"💰 Amount: Rs {amount:,}\n"
                f"📱 UPI ID: `{upi_id}`\n\n"
                f"*Instructions:*\n"
                f"1. Scan QR code or copy UPI ID\n"
                f"2. Complete payment in your UPI app\n"
                f"3. Tap 'I've Paid' after payment\n\n"
                f"⏳ Waiting for admin verification..."
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    
    elif payment_method == 'credit':
        # Pay later (credit) - create purchase request with credit method
        purchase_request = create_purchase_request(user_id, credits, 'credit')
        
        if not purchase_request:
            await query.edit_message_text(
                "❌ *Purchase Error*\n\n"
                "Failed to create purchase request. Please try again.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        context.user_data['shake_purchase_id'] = purchase_request['purchase_id']
        
        # Create AR receivable for full amount
        try:
            from src.database.ar_operations import create_receivable
            from src.utils.event_dispatcher import schedule_followups
            
            receivable = create_receivable(
                user_id=user_id,
                receivable_type='shake_purchase',
                source_id=purchase_request['purchase_id'],
                bill_amount=amount,
                final_amount=amount
            )
            
            # Trigger payment reminders immediately
            schedule_followups(context.application, user_id, 'PAYMENT_REMINDER_1', {
                'receivable_id': receivable['receivable_id'],
                'amount': amount,
                'type': 'Shake Credits',
                'user_name': query.from_user.full_name
            })
            
            logger.info(f"Created AR receivable {receivable['receivable_id']} for shake credit purchase {purchase_request['purchase_id']}")
        except Exception as e:
            logger.error(f"Error creating AR receivable for shake credit: {e}", exc_info=True)
        
        # Show confirmation message to user
        await query.edit_message_text(
            f"✅ *Pay Later (Credit) - Activated*\n\n"
            f"🥤 Credits: {credits}\n"
            f"💵 Amount: Rs {amount:,.2f}\n"
            f"📝 Payment Method: ⏳ Pay Later (Credit)\n\n"
            f"Your purchase request is pending admin approval.\n"
            f"Payment reminders will be sent to your registered contact.",
            parse_mode='Markdown'
        )
        
        # Notify admins with approve/reject buttons
        try:
            from src.handlers.admin_handlers import get_admin_ids
            from src.database.user_operations import get_user
            
            admin_ids = get_admin_ids()
            user_data = get_user(user_id)
            profile_pic_url = user_data.get('profile_pic_url') if user_data else None
            
            admin_text = (
                f"*⏳ Shake Credit Purchase - Pay Later (Credit)*\n\n"
                f"User: {query.from_user.full_name} (ID: {user_id})\n"
                f"Credits: {credits}\n"
                f"Amount: Rs {amount:,}\n"
                f"Payment Method: ⏳ Pay Later (Credit)\n\n"
                f"Request ID: {purchase_request['purchase_id']}\n"
                f"Submitted: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
                f"⚠️ This is a CREDIT order. User will be sent payment reminders."
            )
            
            admin_keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_shake_purchase_{purchase_request['purchase_id']}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_shake_purchase_{purchase_request['purchase_id']}")
                ]
            ]
            
            for admin_id in admin_ids:
                try:
                    if profile_pic_url:
                        try:
                            await context.bot.send_photo(
                                chat_id=admin_id,
                                photo=profile_pic_url,
                                caption=admin_text,
                                reply_markup=InlineKeyboardMarkup(admin_keyboard),
                                parse_mode='Markdown'
                            )
                        except:
                            await context.bot.send_message(
                                chat_id=admin_id,
                                text=admin_text,
                                reply_markup=InlineKeyboardMarkup(admin_keyboard),
                                parse_mode='Markdown'
                            )
                    else:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=admin_text,
                            reply_markup=InlineKeyboardMarkup(admin_keyboard),
                            parse_mode='Markdown'
                        )
                    logger.info(f"Shake credit pay later notification sent to admin {admin_id}")
                except Exception as e:
                    logger.error(f"Failed to send notification to admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Error sending admin notifications: {e}")
        
        return ConversationHandler.END


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

async def callback_approve_shake_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Start shake purchase approval - ask for amount"""
    query = update.callback_query
    
    if not is_admin_id(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    purchase_id = int(query.data.split("_")[-1])
    await query.answer()
    
    try:
        from src.database.shake_credits_operations import get_pending_purchase_requests
        
        # Find the purchase request
        purchases = get_pending_purchase_requests()
        purchase = None
        for p in purchases:
            if p['purchase_id'] == purchase_id:
                purchase = p
                break
        
        if not purchase:
            await query.edit_message_text("❌ Purchase request not found or already processed")
            return ADMIN_ENTER_AMOUNT
        
        # Store in context
        context.user_data['approving_shake_purchase_id'] = purchase_id
        context.user_data['approving_shake_purchase'] = purchase
        
        # Ask for amount
        text = (
            f"*💰 Enter Amount Received*\n\n"
            f"User: {purchase['full_name']}\n"
            f"Credits: {purchase['credits_requested']}\n"
            f"Expected: Rs {purchase['amount']:,}\n\n"
            f"Please reply with the amount you received from the user.\n"
            f"Example: 6000\n\n"
            f"💡 For part payment, enter the actual amount received."
        )
        
        try:
            if getattr(query.message, "photo", None):
                await query.edit_message_caption(text, parse_mode="Markdown")
            else:
                await query.edit_message_text(text, parse_mode="Markdown")
        except:
            await query.message.reply_text(text, parse_mode="Markdown")
        
        logger.info(f"Admin {query.from_user.id} starting shake purchase approval for {purchase_id}")
        return ADMIN_ENTER_AMOUNT
    except Exception as e:
        logger.error(f"Error in callback_approve_shake_purchase: {e}")
        await query.answer("❌ Error starting approval", show_alert=True)
        return ConversationHandler.END


async def handle_shake_approval_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount input for shake purchase approval"""
    try:
        amount_str = update.message.text.strip()
        amount = float(amount_str)
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive. Try again:")
            return ADMIN_ENTER_AMOUNT
        
        purchase_id = context.user_data.get('approving_shake_purchase_id')
        purchase = context.user_data.get('approving_shake_purchase')
        
        if not purchase_id or not purchase:
            await update.message.reply_text("❌ Session expired. Please start again.")
            return ConversationHandler.END
        
        # Approve purchase with the provided amount
        from src.database.shake_credits_operations import approve_purchase
        
        result = approve_purchase(purchase_id, update.effective_user.id, amount)
        
        if result:
            user_id = purchase['user_id']
            credits = purchase['credits_requested']
            expected_amount = purchase['amount']
            
            # Calculate discount if partial payment
            discount_text = ""
            if amount < expected_amount:
                discount = expected_amount - amount
                discount_text = f"\n💸 Discount: Rs {discount:,.2f}"
            
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"✅ *Your Shake Credit Purchase is Approved!*\n\n"
                        f"🥤 {credits} credits added to your account\n"
                        f"💵 Amount Paid: Rs {amount:,.2f}{discount_text}\n"
                        f"✅ Available to use now!\n\n"
                        f"Tap 'Order Shake' from menu to order your shake."
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
            
            await update.message.reply_text(
                f"✅ *Shake Purchase Approved!*\n\n"
                f"User: {purchase['full_name']}\n"
                f"Credits: {credits}\n"
                f"Amount: Rs {amount:,.2f}{discount_text}\n\n"
                f"Credits have been added to user's account.",
                parse_mode='Markdown'
            )
            
            # Clear context
            context.user_data.pop('approving_shake_purchase_id', None)
            context.user_data.pop('approving_shake_purchase', None)
            
            logger.info(f"Shake purchase {purchase_id} approved with amount {amount}")
            return ConversationHandler.END
        else:
            await update.message.reply_text("❌ Failed to approve purchase. Please try again.")
            return ADMIN_ENTER_AMOUNT
            
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number:\n\nExample: 6000")
        return ADMIN_ENTER_AMOUNT


async def callback_reject_shake_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Reject shake purchase"""
    query = update.callback_query
    
    if not is_admin_id(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    purchase_id = int(query.data.split("_")[-1])
    await query.answer()
    
    try:
        from src.database.shake_credits_operations import reject_purchase
        
        result = reject_purchase(purchase_id, query.from_user.id, "Rejected by admin")
        
        if result:
            await query.edit_message_text(
                "✅ *Shake Purchase Rejected!*\n\n"
                "User has been notified.",
                parse_mode='Markdown'
            )
            logger.info(f"Shake purchase {purchase_id} rejected by admin {query.from_user.id}")
        else:
            await query.edit_message_text("❌ Failed to reject purchase")
    except Exception as e:
        logger.error(f"Error rejecting shake purchase: {e}")
        await query.answer("❌ Error rejecting purchase", show_alert=True)
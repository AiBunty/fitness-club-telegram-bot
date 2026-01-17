"""
Payment Request Handlers
User Flow: Submit payment request → Admin reviews → Admin approves with amount & dates using calendar
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from datetime import datetime, timedelta
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

from src.database.payment_request_operations import (
    create_payment_request,
    get_pending_payment_requests,
    get_payment_request_by_id,
    approve_payment_request,
    approve_payment_request_with_dates,
    reject_payment_request,
    has_pending_payment_request
)
from src.database.payment_operations import get_user_fee_status
from src.database.role_operations import is_admin
from src.utils.role_notifications import get_moderator_chat_ids
from src.utils.auth import check_user_approved

logger = logging.getLogger(__name__)

# Conversation states for payment request submission
REQUEST_AMOUNT, REQUEST_PROOF, REQUEST_NOTES = range(3)

# Conversation states for admin approval with calendar
APPROVE_AMOUNT, APPROVE_START_DATE, APPROVE_END_DATE = range(3)

# ============= USER: SUBMIT PAYMENT REQUEST =============

async def cmd_request_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User initiates payment request submission"""
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    user_id = update.effective_user.id

    if not check_user_approved(user_id):
        await message.reply_text(
            "⏳ Registration pending approval. Please contact admin to approve your account before submitting payments."
        )
        return ConversationHandler.END
    
    # Check if user already has pending request
    if has_pending_payment_request(user_id):
        await message.reply_text(
            "❗ You already have a pending payment request.\n"
            "Please wait for admin approval."
        )
        return ConversationHandler.END
    
    # Show current subscription status
    fee_status = get_user_fee_status(user_id)
    
    status_msg = "💳 *Request Payment Approval*\n\n"
    
    if fee_status:
        status_msg += f"Current Status: *{fee_status['fee_status'].upper()}*\n"
        if fee_status['fee_expiry_date']:
            status_msg += f"Expiry Date: {fee_status['fee_expiry_date']}\n"
    
    status_msg += "\n📝 Please enter the amount you paid (in ₹):"
    
    await message.reply_text(status_msg, parse_mode='Markdown')
    return REQUEST_AMOUNT

async def request_receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive payment amount from user"""
    amount_text = update.message.text.strip()
    
    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        context.user_data['payment_request_amount'] = amount
        
        await update.message.reply_text(
            f"💵 Amount: ₹{amount}\n\n"
            "📸 Please send payment proof (screenshot/photo)\n"
            "or /skip if you don't have proof yet."
        )
        return REQUEST_PROOF
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a valid number (e.g., 1500):"
        )
        return REQUEST_AMOUNT

async def request_receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive payment proof image"""
    if update.message.photo:
        # Get the largest photo
        photo = update.message.photo[-1]
        context.user_data['payment_proof_url'] = photo.file_id
        
        await update.message.reply_text(
            "✅ Payment proof received!\n\n"
            "📝 Add any notes for admin (e.g., transaction ID, payment method)\n"
            "or send /skip to submit without notes."
        )
        return REQUEST_NOTES
    else:
        await update.message.reply_text(
            "❌ Please send a photo of your payment proof\n"
            "or send /skip to continue without proof."
        )
        return REQUEST_PROOF

async def request_skip_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip payment proof"""
    context.user_data['payment_proof_url'] = None
    
    await update.message.reply_text(
        "📝 Add any notes for admin (e.g., transaction ID, payment method)\n"
        "or send /done to submit your request."
    )
    return REQUEST_NOTES

async def request_receive_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive notes and submit payment request"""
    notes = update.message.text.strip()
    
    # Extract data
    amount = context.user_data.get('payment_request_amount')
    proof_url = context.user_data.get('payment_proof_url')
    user_id = update.effective_user.id
    
    # Create payment request
    request_id = create_payment_request(
        user_id=user_id,
        amount=amount,
        notes=notes,
        proof_url=proof_url
    )
    
    if request_id:
        await update.message.reply_text(
            "✅ *Payment Request Submitted!*\n\n"
            f"Request ID: #{request_id}\n"
            f"Amount: ₹{amount}\n"
            f"Status: ⏳ Pending Admin Approval\n\n"
            "Admins have been notified. You'll be alerted once approved.",
            parse_mode='Markdown'
        )
        
        # Notify admins about new request
        await notify_admins_new_request(context, request_id, user_id, amount)
    else:
        await update.message.reply_text(
            "❌ Failed to submit payment request. Please try again later."
        )
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

async def request_skip_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Submit request without notes"""
    # Extract data
    amount = context.user_data.get('payment_request_amount')
    proof_url = context.user_data.get('payment_proof_url')
    user_id = update.effective_user.id
    
    # Create payment request
    request_id = create_payment_request(
        user_id=user_id,
        amount=amount,
        notes="",
        proof_url=proof_url
    )
    
    if request_id:
        await update.message.reply_text(
            "✅ *Payment Request Submitted!*\n\n"
            f"Request ID: #{request_id}\n"
            f"Amount: ₹{amount}\n"
            f"Status: ⏳ Pending Admin Approval\n\n"
            "Admins have been notified. You'll be alerted once approved.",
            parse_mode='Markdown'
        )
        
        # Notify admins
        await notify_admins_new_request(context, request_id, user_id, amount)
    else:
        await update.message.reply_text(
            "❌ Failed to submit payment request. Please try again later."
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def request_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel payment request submission"""
    await update.message.reply_text(
        "❌ Payment request cancelled."
    )
    context.user_data.clear()
    return ConversationHandler.END

# ============= ADMIN: VIEW & APPROVE REQUESTS =============

async def cmd_pending_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin views pending payment requests"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.callback_query.answer("Admin access only", show_alert=True)
        return
    
    pending = get_pending_payment_requests()
    
    if not pending:
        msg = "✅ No pending payment requests."
        
        if update.callback_query:
            await update.callback_query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return
    
    msg = f"💳 *Pending Payment Requests* ({len(pending)})\n\n"
    
    keyboard = []
    for req in pending:
        user_info = f"{req['full_name']}"
        if req['telegram_username']:
            user_info += f" (@{req['telegram_username']})"
        
        amount_str = f"₹{req['amount']}" if req['amount'] else "Amount not specified"
        requested_date = req['requested_at'].strftime('%d %b %Y, %I:%M %p')
        
        msg += f"🆔 Request #{req['request_id']}\n"
        msg += f"👤 User: {user_info}\n"
        msg += f"💵 Amount: {amount_str}\n"
        msg += f"📅 Requested: {requested_date}\n"
        if req['notes']:
            msg += f"📝 Notes: {req['notes'][:50]}...\n"
        msg += "\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"✅ Review #{req['request_id']}", 
                callback_data=f"review_request_{req['request_id']}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def callback_review_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin reviews specific payment request"""
    query = update.callback_query
    await query.answer()
    
    request_id = int(query.data.split('_')[-1])
    request = get_payment_request_by_id(request_id)
    
    if not request:
        await query.edit_message_text("❌ Payment request not found.")
        return
    
    user_info = f"{request['full_name']}"
    if request['telegram_username']:
        user_info += f" (@{request['telegram_username']})"
    
    amount_str = f"₹{request['amount']}" if request['amount'] else "Not specified"
    
    msg = f"💳 *Payment Request Details*\n\n"
    msg += f"🆔 Request ID: #{request['request_id']}\n"
    msg += f"👤 User: {user_info}\n"
    msg += f"📱 User ID: {request['user_id']}\n"
    msg += f"💵 Amount: {amount_str}\n"
    msg += f"📅 Requested: {request['requested_at'].strftime('%d %b %Y, %I:%M %p')}\n"
    
    if request['notes']:
        msg += f"\n📝 Notes:\n{request['notes']}\n"
    
    if request['payment_proof_url']:
        msg += "\n📸 Payment proof attached\n"
    
    msg += f"\n⏳ Status: *{request['status'].upper()}*"
    
    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_req_{request_id}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject_req_{request_id}")],
        [InlineKeyboardButton("🔙 Back to List", callback_data="cmd_pending_requests")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Show payment proof if available
    if request['payment_proof_url']:
        try:
            await query.message.reply_photo(
                photo=request['payment_proof_url'],
                caption=msg,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            await query.message.delete()
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def callback_approve_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start approval process - ask for amount"""
    query = update.callback_query
    await query.answer()
    
    request_id = int(query.data.split('_')[-1])
    context.user_data['approving_request_id'] = request_id
    
    request = get_payment_request_by_id(request_id)
    suggested_amount = request['amount'] if request['amount'] else ""
    
    msg = f"💵 *Approve Payment Request #{request_id}*\n\n"
    msg += f"User: {request['full_name']}\n\n"
    
    if suggested_amount:
        msg += f"Suggested Amount: ₹{suggested_amount}\n\n"
    
    msg += "Please enter the approved amount (in ₹):"
    
    await query.edit_message_text(msg, parse_mode='Markdown')
    return APPROVE_AMOUNT

async def approve_receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive approved amount from admin and show start date calendar"""
    amount_text = update.message.text.strip()
    
    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        context.user_data['approved_amount'] = amount
        
        # Show calendar for start date selection
        calendar, step = DetailedTelegramCalendar(
            min_date=datetime.now().date() - timedelta(days=7),  # Allow backdating up to 7 days
            max_date=datetime.now().date() + timedelta(days=30)   # Max 30 days ahead
        ).build()
        
        await update.message.reply_text(
            f"💵 Approved Amount: ₹{amount}\n\n"
            "📅 Select subscription *START DATE*:\n"
            "(When did the user pay?)",
            reply_markup=calendar,
            parse_mode='Markdown'
        )
        return APPROVE_START_DATE
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a valid number:"
        )
        return APPROVE_AMOUNT

async def approve_receive_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive start date and show end date calendar"""
    query = update.callback_query
    await query.answer()
    
    result, key, step = DetailedTelegramCalendar(
        min_date=datetime.now().date() - timedelta(days=7),
        max_date=datetime.now().date() + timedelta(days=30)
    ).process(query.data)
    
    if not result and key:
        # Still navigating calendar
        await query.edit_message_text(
            f"📅 Select subscription *START DATE*:",
            reply_markup=key,
            parse_mode='Markdown'
        )
        return APPROVE_START_DATE
    elif result:
        # Date selected
        context.user_data['start_date'] = result
        
        # Show calendar for end date
        calendar, step = DetailedTelegramCalendar(
            min_date=result + timedelta(days=1),  # End date must be after start
            max_date=result + timedelta(days=730)  # Max 2 years subscription
        ).build()
        
        await query.edit_message_text(
            f"✅ Start Date: {result.strftime('%d %b %Y')}\n\n"
            "📅 Select subscription *END DATE*:\n"
            "(When will subscription expire?)",
            reply_markup=calendar,
            parse_mode='Markdown'
        )
        return APPROVE_END_DATE

async def approve_receive_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive end date and finalize approval"""
    query = update.callback_query
    await query.answer()
    
    start_date = context.user_data.get('start_date')
    
    result, key, step = DetailedTelegramCalendar(
        min_date=start_date + timedelta(days=1),
        max_date=start_date + timedelta(days=730)
    ).process(query.data)
    
    if not result and key:
        # Still navigating calendar
        await query.edit_message_text(
            f"📅 Select subscription *END DATE*:",
            reply_markup=key,
            parse_mode='Markdown'
        )
        return APPROVE_END_DATE
    elif result:
        # End date selected - finalize approval
        end_date = result
        request_id = context.user_data['approving_request_id']
        amount = context.user_data['approved_amount']
        admin_id = update.effective_user.id
        
        # Calculate duration in days
        duration = (end_date - start_date).days
        
        # Approve the request with custom dates
        approval = approve_payment_request_with_dates(
            request_id, admin_id, amount, start_date, end_date
        )
        
        if approval and approval.get('already_processed'):
            await query.edit_message_text(
                f"ℹ️ Payment request #{request_id} already {approval.get('status', 'processed')} by another admin."
            )
            context.user_data.clear()
            return ConversationHandler.END

        if approval:
            request = approval
            
            await query.edit_message_text(
                f"✅ *Payment Request Approved!*\n\n"
                f"Request ID: #{request_id}\n"
                f"User: {request['full_name']}\n"
                f"Amount: ₹{amount}\n"
                f"📅 Start: {start_date.strftime('%d %b %Y')}\n"
                f"📅 End: {end_date.strftime('%d %b %Y')}\n"
                f"⏰ Duration: {duration} days\n\n"
                "User has been notified and subscription activated.",
                parse_mode='Markdown'
            )
            
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=request['user_id'],
                    text=(
                        f"✅ *Payment Approved!*\n\n"
                        f"Your payment request has been approved by admin.\n\n"
                        f"💵 Amount: ₹{amount}\n"
                        f"📅 Start Date: {start_date.strftime('%d %b %Y')}\n"
                        f"📅 Valid Until: {end_date.strftime('%d %b %Y')}\n"
                        f"⏰ Subscription Duration: {duration} days\n\n"
                        "Your subscription is now active! 🎉"
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify user {request['user_id']}: {e}")
            
            # Notify admins of approval
            try:
                await notify_admins_payment_approved(
                    context, request_id, request['user_id'], amount, 
                    request['full_name'], start_date, end_date
                )
            except Exception as e:
                logger.error(f"Failed to notify admins of approval: {e}")
        else:
            await query.edit_message_text(
                "❌ Failed to approve payment request. Please try again."
            )
        
        context.user_data.clear()
        return ConversationHandler.END

async def callback_reject_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject payment request"""
    query = update.callback_query
    await query.answer()
    
    request_id = int(query.data.split('_')[-1])
    admin_id = update.effective_user.id
    
    # Reject the request
    rejection = reject_payment_request(request_id, admin_id, "Rejected by admin")
    
    if rejection and rejection.get('already_processed'):
        await query.edit_message_text(
            f"ℹ️ Payment request #{request_id} already {rejection.get('status', 'processed')} by another admin."
        )
        return ConversationHandler.END
    
    if rejection:
        request = get_payment_request_by_id(request_id)
        
        await query.edit_message_text(
            f"❌ *Payment Request Rejected*\n\n"
            f"Request ID: #{request_id}\n"
            f"User: {request['full_name']}\n\n"
            "User has been notified.",
            parse_mode='Markdown'
        )
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=request['user_id'],
                text=(
                    f"❌ *Payment Request Rejected*\n\n"
                    f"Your payment request #{request_id} was not approved.\n"
                    "Please contact admin for more information."
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user {request['user_id']}: {e}")
    else:
        await query.edit_message_text(
            "❌ Failed to reject payment request. Please try again."
        )
    
    return ConversationHandler.END

# ============= HELPER FUNCTIONS =============

async def notify_admins_new_request(context: ContextTypes.DEFAULT_TYPE, request_id: int, user_id: int, amount: float):
    """Notify moderators (super admin, admins, staff) about new payment request."""
    recipients = get_moderator_chat_ids(include_staff=True)

    for chat_id in recipients:
        try:
            keyboard = [[
                InlineKeyboardButton("🔍 Review Request", callback_data=f"review_request_{request_id}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🔔 *New Payment Request*\n\n"
                    f"Request ID: #{request_id}\n"
                    f"User ID: {user_id}\n"
                    f"Amount: ₹{amount}\n\n"
                    "Click below to review and approve."
                ),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify moderator {chat_id}: {e}")

async def notify_admins_payment_approved(context: ContextTypes.DEFAULT_TYPE, request_id: int, user_id: int, amount: float, full_name: str, start_date, end_date):
    """Notify moderators (super admin, admins, staff) that a payment request has been approved."""
    recipients = get_moderator_chat_ids(include_staff=True)

    for chat_id in recipients:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ *Payment Request Approved*\n\n"
                    f"Request ID: #{request_id}\n"
                    f"User: {full_name} (ID: {user_id})\n"
                    f"Amount: ₹{amount}\n"
                    f"📅 Start: {start_date.strftime('%d %b %Y')}\n"
                    f"📅 End: {end_date.strftime('%d %b %Y')}\n\n"
                    "Subscription activated ✅"
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify moderator {chat_id} of approval: {e}")

# ============= CONVERSATION HANDLERS =============

payment_request_conversation = ConversationHandler(
    entry_points=[CommandHandler('request_payment', cmd_request_payment)],
    states={
        REQUEST_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, request_receive_amount)],
        REQUEST_PROOF: [
            MessageHandler(filters.PHOTO, request_receive_proof),
            CommandHandler('skip', request_skip_proof)
        ],
        REQUEST_NOTES: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, request_receive_notes),
            CommandHandler('done', request_skip_notes),
            CommandHandler('skip', request_skip_notes)
        ],
    },
    fallbacks=[CommandHandler('cancel', request_cancel)]
)

approval_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(callback_approve_start, pattern=r'^approve_req_\d+$')],
    states={
        APPROVE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, approve_receive_amount)],
        APPROVE_START_DATE: [CallbackQueryHandler(approve_receive_start_date)],
        APPROVE_END_DATE: [CallbackQueryHandler(approve_receive_end_date)],
    },
    fallbacks=[]
)

"""
Subscription Management Handlers
- User subscription selection and purchase
- Admin subscription approval
- Subscription reminders and expiry notifications
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from src.database.subscription_operations import (
    SUBSCRIPTION_PLANS, create_subscription_request, get_pending_subscription_requests,
    approve_subscription, reject_subscription, get_user_subscription, is_subscription_active,
    is_in_grace_period, is_subscription_expired, get_expiring_subscriptions,
    get_users_in_grace_period, get_expired_subscriptions, mark_subscription_locked,
    get_user_pending_subscription_request
)
from src.database.user_operations import get_user
from src.utils.auth import is_admin

logger = logging.getLogger(__name__)

# Conversation states
SELECT_PLAN, CONFIRM_PLAN, SELECT_PAYMENT, ENTER_UPI_VERIFICATION, ADMIN_APPROVE_SUB, ADMIN_ENTER_AMOUNT, ADMIN_SELECT_DATE, ENTER_SPLIT_UPI_AMOUNT, ENTER_SPLIT_CONFIRM, ADMIN_ENTER_BILL, ADMIN_ENTER_UPI_RECEIVED, ADMIN_ENTER_CASH_RECEIVED, ADMIN_FINAL_CONFIRM = range(13)


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
    from src.database.subscription_operations import get_user_pending_subscription_request
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


async def callback_confirm_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and show payment method selection"""
    query = update.callback_query
    user_id = query.from_user.id
    logger.info(f"[SUB] callback_confirm_subscription triggered for user {user_id}")
    plan_id = context.user_data.get('selected_plan_id')
    plan = context.user_data.get('selected_plan')
    logger.info(f"[SUB] Plan info: plan_id={plan_id}, plan={plan}")
    
    if not plan_id or not plan:
        logger.error(f"Plan info missing for user {user_id}")
        await query.answer("Plan information not found", show_alert=True)
        return ConversationHandler.END
    
    # Verify user exists before proceeding to payment
    user = get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database at payment confirmation stage")
        await query.answer("❌ Your profile is not yet registered. Please wait a moment and try again.", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    logger.info(f"User {user_id} confirmed subscription for plan {plan_id}")
    
    # Show payment method selection
    keyboard = [
        [InlineKeyboardButton("� UPI Payment", callback_data="pay_method_upi")],
        [InlineKeyboardButton("💵 Cash Payment", callback_data="pay_method_cash")],
        [InlineKeyboardButton("⏳ Pay Later (Credit)", callback_data="pay_method_credit")],
        [InlineKeyboardButton("🔀 Split Payment (UPI + Cash)", callback_data="pay_method_split")],
        [InlineKeyboardButton("❌ Cancel", callback_data="sub_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"*💳 Select Payment Method*\n\n"
        f"Plan: {plan['name']}\n"
        f"Amount: Rs. {plan['amount']:,}\n\n"
        f"Choose how you'd like to pay:"
    )
    
    try:
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
        logger.info(f"Payment method options shown to user {user_id}")
    except Exception as e:
        logger.error(f"Error editing message for user {user_id}: {e}")
        await query.answer("Error loading payment options. Please try again.", show_alert=True)
        return ConversationHandler.END
    
    return SELECT_PAYMENT


async def callback_select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment method selection"""
    query = update.callback_query
    user_id = query.from_user.id
    payment_method = query.data.split("_")[2]  # 'cash' or 'upi'
    plan_id = context.user_data.get('selected_plan_id')
    plan = context.user_data.get('selected_plan')
    
    if not plan_id or not plan:
        await query.answer("Plan information not found")
        return ConversationHandler.END
    
    # CRITICAL: Verify user exists in database before creating subscription request
    user = get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database when selecting payment method")
        await query.answer("❌ User profile not found. Please /start and register again.", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    context.user_data['payment_method'] = payment_method
    
    if payment_method == 'cash':
        # Cash payment - submit for admin approval directly
        sub_request = create_subscription_request(user_id, plan_id, plan['amount'], 'cash')
        
        if not sub_request:
            logger.error(f"Failed to create subscription request for user {user_id}. User may not exist in database yet.")
            await query.edit_message_text(
                "⚠️ *Subscription Error*\n\n"
                "There was an issue processing your subscription.\n"
                "Please try again in a moment or contact support.\n\n"
                "This usually means your profile is still being registered."
            )
            return ConversationHandler.END
        
        context.user_data['subscription_request_id'] = sub_request['id']
        
        keyboard = [
            [InlineKeyboardButton("💬 WhatsApp Support", url="https://wa.me/9158243377")],
            [InlineKeyboardButton("📞 Contact Admin", callback_data="admin_contact")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ *Cash Payment - Awaiting Admin Approval*\n\n"
            f"Plan: {plan['name']}\n"
            f"Amount: Rs. {plan['amount']:,}\n"
            f"Payment Method: 💵 Cash\n\n"
            f"Your subscription request has been submitted.\n"
            f"Please contact the admin or visit the gym to complete the payment.\n"
            f"You will be notified once approved. 🎉\n\n"
            f"Questions? Reach out on WhatsApp or contact admin.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
        # Send cash payment notification to admins with approve/reject buttons
        try:
            from src.handlers.admin_handlers import get_admin_ids
            
            admin_ids = get_admin_ids()
            logger.info(f"Cash payment: Found {len(admin_ids)} admins: {admin_ids}")
            
            # Get user profile picture
            user_data = get_user(user_id)
            profile_pic_url = user_data.get('profile_pic_url') if user_data else None
            
            admin_caption = (
                f"*💵 Cash Payment Request - Admin Review*\n\n"
                f"User: {query.from_user.full_name} (ID: {user_id})\n"
                f"Plan: {plan['name']}\n"
                f"Amount: Rs. {plan['amount']:,}\n"
                f"Payment Method: 💵 Cash\n\n"
                f"Request ID: {sub_request['id']}\n"
                f"Submitted: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
                f"*Action:* Please verify cash payment and approve/reject below."
            )
            
            admin_keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_cash_{sub_request['id']}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_cash_{sub_request['id']}"),
                ]
            ]
            admin_reply_markup = InlineKeyboardMarkup(admin_keyboard)
            
            if not admin_ids:
                logger.warning("No admins found to notify about cash payment")
            
            for admin_id in admin_ids:
                try:
                    # Send profile pic if available, otherwise just send text
                    if profile_pic_url:
                        try:
                            await context.bot.send_photo(
                                chat_id=admin_id,
                                photo=profile_pic_url,
                                caption=admin_caption,
                                reply_markup=admin_reply_markup,
                                parse_mode="Markdown"
                            )
                            logger.info(f"✅ Cash payment notification with profile pic sent to admin {admin_id}")
                        except Exception as pic_error:
                            logger.debug(f"Could not send photo, sending text only: {pic_error}")
                            await context.bot.send_message(
                                chat_id=admin_id,
                                text=admin_caption,
                                reply_markup=admin_reply_markup,
                                parse_mode="Markdown"
                            )
                    else:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=admin_caption,
                            reply_markup=admin_reply_markup,
                            parse_mode="Markdown"
                        )
                    logger.info(f"✅ Cash payment notification sent to admin {admin_id} for request {sub_request['id']}")
                except Exception as e:
                    logger.error(f"❌ Failed to send cash payment notification to admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Error in cash payment admin notification flow: {e}", exc_info=True)
        
        logger.info(f"Cash subscription request: User {user_id}, Plan {plan_id}, Amount {plan['amount']}")
        return ConversationHandler.END
    
    elif payment_method == 'upi':
        # UPI payment - generate QR code
        from src.utils.upi_qrcode import generate_upi_qr_code, get_upi_id
        from src.database.subscription_operations import record_payment
        
        transaction_ref = f"GYM{user_id}{int(datetime.now().timestamp())}"
        
        # Generate QR code
        qr_bytes = generate_upi_qr_code(plan['amount'], query.from_user.full_name, transaction_ref)
        
        if not qr_bytes:
            await query.edit_message_text(
                "❌ Error generating UPI QR code. Please try cash payment instead."
            )
            return ConversationHandler.END
        
        # Create pending request for UPI
        sub_request = create_subscription_request(user_id, plan_id, plan['amount'], 'upi')
        context.user_data['subscription_request_id'] = sub_request['id']
        context.user_data['transaction_ref'] = transaction_ref
        context.user_data['screenshot_file_id'] = None  # Will store file_id if user uploads
        
        # Send QR code to user
        # Get UPI ID
        upi_id = get_upi_id()
        
        keyboard = [
            [InlineKeyboardButton("📸 Upload Screenshot", callback_data="upi_upload_screenshot")],
            [InlineKeyboardButton("⏭️ Skip for Now", callback_data="upi_skip_screenshot")],
            [InlineKeyboardButton("💬 WhatsApp Support", url="https://wa.me/9158243377")],
            [InlineKeyboardButton("❌ Cancel", callback_data="sub_cancel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        caption = (
            f"*📱 UPI Payment Details*\n\n"
            f"Plan: {plan['name']}\n"
            f"Amount: Rs. {plan['amount']:,}\n"
            f"Reference: {transaction_ref}\n\n"
            f"*UPI ID:* `{upi_id}`\n"
            f"_(Tap to copy)_\n\n"
            f"*How to Pay:*\n"
            f"1️⃣ Scan the QR code below with any UPI app\n"
            f"2️⃣ OR Copy the UPI ID above and pay via PhonePe/GPay/Paytm\n"
            f"3️⃣ Enter amount: Rs. {plan['amount']}\n\n"
            f"After payment, upload the payment screenshot for verification.\n"
            f"Or click 'Skip for Now' to submit without screenshot."
        )
        
        await query.message.reply_photo(
            photo=qr_bytes,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Send QR code to admins with approve/reject buttons
        try:
            from src.handlers.admin_handlers import get_admin_ids
            
            admin_ids = get_admin_ids()
            
            # Get user profile picture
            user_data = get_user(user_id)
            profile_pic_url = user_data.get('profile_pic_url') if user_data else None
            
            admin_caption = (
                f"*📱 UPI Payment Request - Admin Review*\n\n"
                f"User: {query.from_user.full_name} (ID: {user_id})\n"
                f"Plan: {plan['name']}\n"
                f"Amount: Rs. {plan['amount']:,}\n"
                f"Reference: {transaction_ref}\n"
                f"UPI ID: 9158243377@ybl\n\n"
                f"Request ID: {sub_request['id']}\n"
                f"Submitted: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
            )
            
            admin_keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_upi_{sub_request['id']}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_upi_{sub_request['id']}"),
                ]
            ]
            admin_reply_markup = InlineKeyboardMarkup(admin_keyboard)
            
            for admin_id in admin_ids:
                try:
                    # Send QR code
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=qr_bytes,
                        caption=admin_caption,
                        reply_markup=admin_reply_markup,
                        parse_mode="Markdown"
                    )
                    logger.info(f"✅ UPI payment QR sent to admin {admin_id}")
                    
                    # Send profile picture if available
                    if profile_pic_url:
                        try:
                            await context.bot.send_photo(
                                chat_id=admin_id,
                                photo=profile_pic_url,
                                caption="📸 User Profile Picture"
                            )
                            logger.info(f"✅ User profile picture sent to admin {admin_id}")
                        except Exception as pic_error:
                            logger.debug(f"Could not send profile picture to admin {admin_id}: {pic_error}")
                except Exception as e:
                    logger.debug(f"Could not send UPI notification to admin {admin_id}: {e}")
        except Exception as e:
            logger.debug(f"Error sending admin notification: {e}")
        
        logger.info(f"UPI QR generated for user {user_id}, amount {plan['amount']}")
        return ENTER_UPI_VERIFICATION
    
    elif payment_method == 'credit':
        # Pay Later (Credit) - full amount outstanding
        total_amount = plan['amount']
        sub_request = create_subscription_request(user_id, plan_id, total_amount, 'credit')
        
        if not sub_request:
            logger.error(f"Failed to create pay later subscription request for user {user_id}")
            await query.edit_message_text(
                "⚠️ *Pay Later Error*\n\n"
                "There was an issue processing your pay later request.\n"
                "Please try again in a moment or contact support."
            )
            return ConversationHandler.END
        
        context.user_data['subscription_request_id'] = sub_request['id']
        
        # Create AR receivable for full amount (credit)
        try:
            from src.database.ar_operations import create_receivable, get_receivable_by_source, get_receivable_breakdown
            from src.utils.event_dispatcher import schedule_followups
            
            # Create receivable for full amount
            receivable = create_receivable(
                user_id=user_id,
                receivable_type='subscription',
                source_id=sub_request['id'],
                bill_amount=total_amount,
                discount_amount=0.0,
                final_amount=total_amount
            )
            
            # If receivable created successfully, compute balance and schedule reminders
            if receivable:
                receivable_id = receivable.get('receivable_id') or receivable.get('id')
                try:
                    breakdown = get_receivable_breakdown(receivable_id)
                    balance = breakdown.get('balance', 0)
                except Exception:
                    balance = 0

                if balance > 0:
                    from datetime import datetime, timedelta

                    reminder_time = datetime.now() + timedelta(hours=48)
                    if context and getattr(context, 'application', None):
                        schedule_followups(
                            context.application,
                            user_id,
                            'PAYMENT_REMINDER_1',
                            {
                                'amount_due': balance,
                                'due_in_hours': 48,
                            },
                            reminder_time,
                        )

                    # Notify user
                    try:
                        end_date_str = end_date.strftime('%d-%m-%Y') if end_date else 'Not Set'
                        message = (
                            f"✅ *Subscription Approved!*\n\n"
                            f"Plan: {request_details.get('plan_id', 'N/A')}\n"
                            f"Amount: Rs. {final_bill:,}\n"
                            f"UPI Received: Rs. {upi_received:,}\n"
                            f"Cash Received: Rs. {cash_received:,}\n"
                            f"Balance: Rs. {balance:,}\n"
                            f"Valid Until: {end_date_str}\n\n"
                            f"Your subscription is now active! 🎉"
                        )
                        await context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
                        logger.info(f"Approval notification sent to user {user_id}")
                    except Exception as e:
                        logger.debug(f"Could not send approval notification to user: {e}")
            
                    # Update UI
                    await query.edit_message_text(
                        f"✅ Subscription Approved!\n\n"
                        f"Final Bill: Rs. {final_bill:,}\n"
                        f"UPI Received: Rs. {upi_received:,}\n"
                        f"Cash Received: Rs. {cash_received:,}\n"
                        f"Balance: Rs. {balance:,}\n"
                        f"Valid Until: {end_date.strftime('%d-%m-%Y') if end_date else 'Not Set'}\n\n"
                        f"Reminders scheduled for outstanding balance."
                    )
            
                    return ConversationHandler.END
        
        except Exception as e:
            logger.error(f"Error processing pay later credit: {e}", exc_info=True)
        
        # Show confirmation to user
        keyboard = [
            [InlineKeyboardButton("💬 WhatsApp Support", url="https://wa.me/9158243377")],
            [InlineKeyboardButton("📞 Contact Admin", callback_data="admin_contact")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ *Pay Later (Credit) - Activated*\n\n"
            f"Plan: {plan['name']}\n"
            f"Amount: Rs. {total_amount:,}\n"
            f"Payment Method: ⏳ Credit\n\n"
            f"Your credit has been activated for this subscription.\n"
            f"You will receive payment reminders to settle the outstanding amount.\n"
            f"Your subscription is now active. 🎉\n\n"
            f"Questions? Reach out on WhatsApp or contact admin.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
        logger.info(f"Pay later (credit) subscription created: User {user_id}, Plan {plan_id}, Amount {total_amount}")
        return ConversationHandler.END
    
    elif payment_method == 'split':
        # Split payment (UPI + Cash) - ask for UPI amount
        total_amount = plan['amount']
        context.user_data['split_total'] = total_amount
        context.user_data['subscription_request_split'] = True
        
        await query.answer()
        
        message = (
            f"*💳 Split Payment Setup*\n\n"
            f"Plan: {plan['name']}\n"
            f"Total Amount: Rs. {total_amount:,}\n\n"
            f"Enter the amount you'd like to pay via *UPI*\n"
            f"(Remaining will be collected as cash)\n\n"
            f"_Example: For total Rs. 2500, enter 1000 to pay Rs. 1000 via UPI and Rs. 1500 via cash_"
        )
        
        try:
            await query.edit_message_text(message, parse_mode="Markdown")
            logger.info(f"Split payment prompt shown to user {user_id}")
        except Exception as e:
            logger.error(f"Error editing message for user {user_id}: {e}")
            await query.answer("Error loading split payment setup. Please try again.", show_alert=True)
            return ConversationHandler.END
        
        return ENTER_SPLIT_UPI_AMOUNT


async def callback_upi_payment_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle UPI payment completion"""
    query = update.callback_query
    user_id = query.from_user.id
    plan_id = context.user_data.get('selected_plan_id')
    plan = context.user_data.get('selected_plan')
    request_id = context.user_data.get('subscription_request_id')
    transaction_ref = context.user_data.get('transaction_ref')
    
    if not plan or not request_id:
        await query.answer("Payment data not found")
        return ConversationHandler.END
    
    await query.answer()
    
    # Record UPI payment
    from src.database.subscription_operations import record_payment
    payment = record_payment(user_id, request_id, plan['amount'], 'upi', transaction_ref)
    
    if not payment:
        await query.edit_message_text(
            "❌ Error recording payment. Please contact admin."
        )
        return ConversationHandler.END
    
    await query.edit_message_text(
        f"✅ *UPI Payment Received*\n\n"
        f"Plan: {plan['name']}\n"
        f"Amount: Rs. {plan['amount']:,}\n"
        f"Payment Method: 📱 UPI\n"
        f"Reference: {transaction_ref}\n\n"
        f"Your payment has been recorded.\n"
        f"Your subscription will be activated shortly. 🎉",
        parse_mode="Markdown"
    )
    
    logger.info(f"UPI payment verified for user {user_id}, amount {plan['amount']}")
    return ConversationHandler.END


async def handle_split_upi_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user input for split payment UPI amount"""
    user_id = update.effective_user.id
    total_amount = context.user_data.get('split_total')
    plan = context.user_data.get('selected_plan')
    
    if not total_amount or not plan:
        await update.message.reply_text("❌ Payment setup expired. Please start again with /subscribe")
        return ConversationHandler.END
    
    try:
        upi_amount = float(update.message.text.strip())
        
        # Validate UPI amount
        if upi_amount <= 0:
            await update.message.reply_text(f"❌ UPI amount must be greater than 0. Try again:")
            return ENTER_SPLIT_UPI_AMOUNT
        
        if upi_amount >= total_amount:
            await update.message.reply_text(
                f"❌ UPI amount must be less than total (Rs. {total_amount:,}). Try again:"
            )
            return ENTER_SPLIT_UPI_AMOUNT
        
        # Calculate cash amount
        cash_amount = total_amount - upi_amount
        
        # Store split amounts
        context.user_data['split_upi_amount'] = upi_amount
        context.user_data['split_cash_amount'] = cash_amount
        
        # Show confirmation
        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data="split_confirm")],
            [InlineKeyboardButton("❌ Cancel", callback_data="split_cancel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            f"*🔀 Split Payment Summary*\n\n"
            f"Plan: {plan['name']}\n"
            f"Total Amount: Rs. {total_amount:,}\n\n"
            f"💾 Breakdown:\n"
            f"• UPI Payment: Rs. {upi_amount:,.0f}\n"
            f"• Cash Payment: Rs. {cash_amount:,.0f}\n\n"
            f"Is this correct?"
        )
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
        logger.info(f"Split payment summary shown to user {user_id}: UPI={upi_amount}, Cash={cash_amount}")
        
        return ENTER_SPLIT_CONFIRM
        
    except ValueError:
        await update.message.reply_text(f"❌ Please enter a valid amount (e.g., 1000). Try again:")
        return ENTER_SPLIT_UPI_AMOUNT


async def callback_split_confirm_or_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle split payment confirmation or cancellation"""
    query = update.callback_query
    user_id = query.from_user.id
    action = query.data.replace("split_", "")
    
    if action == 'cancel':
        await query.answer()
        await query.edit_message_text("❌ Split payment cancelled. Type /subscribe to try again.")
        return ConversationHandler.END
    
    await query.answer()
    
    # Get payment details
    plan_id = context.user_data.get('selected_plan_id')
    plan = context.user_data.get('selected_plan')
    upi_amount = context.user_data.get('split_upi_amount')
    cash_amount = context.user_data.get('split_cash_amount')
    total_amount = context.user_data.get('split_total')
    
    if not all([plan_id, plan, upi_amount, cash_amount]):
        await query.answer("Payment data expired. Please /subscribe again.", show_alert=True)
        return ConversationHandler.END
    
    # Verify user exists
    user = get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database when confirming split payment")
        await query.answer("❌ User profile not found. Please /start and register again.", show_alert=True)
        return ConversationHandler.END
    
    # Create split payment request (with method='split' for now)
    sub_request = create_subscription_request(user_id, plan_id, total_amount, 'split')
    
    if not sub_request:
        logger.error(f"Failed to create split payment subscription request for user {user_id}")
        await query.edit_message_text(
            "⚠️ *Split Payment Error*\n\n"
            "There was an issue processing your payment.\n"
            "Please try again in a moment or contact support."
        )
        return ConversationHandler.END
    
    context.user_data['subscription_request_id'] = sub_request['id']
    
    # Generate UPI QR for the UPI portion
    try:
        from src.utils.upi_qrcode import generate_upi_qr_code, get_upi_id
        
        transaction_ref = f"SPLIT{user_id}{int(datetime.now().timestamp())}"
        qr_bytes = generate_upi_qr_code(upi_amount, query.from_user.full_name, transaction_ref)
        
        if not qr_bytes:
            logger.error(f"Failed to generate UPI QR for split payment")
            await query.edit_message_text(
                "❌ Error generating UPI QR code. Please try cash payment instead."
            )
            return ConversationHandler.END
        
        context.user_data['transaction_ref'] = transaction_ref
        context.user_data['screenshot_file_id'] = None
        
        # Send UPI QR for the UPI portion
        upi_id = get_upi_id()
        
        keyboard = [
            [InlineKeyboardButton("📸 Upload Screenshot", callback_data="split_upi_upload_screenshot")],
            [InlineKeyboardButton("⏭️ Skip for Now", callback_data="split_upi_skip_screenshot")],
            [InlineKeyboardButton("💬 WhatsApp Support", url="https://wa.me/9158243377")],
            [InlineKeyboardButton("❌ Cancel", callback_data="sub_cancel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        caption = (
            f"*💳 Split Payment - UPI QR Code*\n\n"
            f"Plan: {plan['name']}\n"
            f"*UPI Amount: Rs. {upi_amount:,.0f}*\n"
            f"Cash Amount: Rs. {cash_amount:,.0f}\n"
            f"Reference: {transaction_ref}\n\n"
            f"*UPI ID:* `{upi_id}`\n"
            f"_(Tap to copy)_\n\n"
            f"*How to Pay:*\n"
            f"1️⃣ Scan the QR code below with any UPI app\n"
            f"2️⃣ OR Copy the UPI ID above and pay via PhonePe/GPay/Paytm\n"
            f"3️⃣ Enter amount: Rs. {upi_amount:,.0f}\n\n"
            f"After UPI payment, upload the screenshot for verification.\n"
            f"The admin will confirm cash collection separately. 💵"
        )
        
        await query.message.reply_photo(
            photo=qr_bytes,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Send split payment notification to admins
        try:
            from src.handlers.admin_handlers import get_admin_ids
            
            admin_ids = get_admin_ids()
            logger.info(f"Split payment: Found {len(admin_ids)} admins")
            
            user_data = get_user(user_id)
            profile_pic_url = user_data.get('profile_pic_url') if user_data else None
            
            admin_caption = (
                f"*🔀 Split Payment Request - Admin Review*\n\n"
                f"User: {query.from_user.full_name} (ID: {user_id})\n"
                f"Plan: {plan['name']}\n"
                f"Total Amount: Rs. {total_amount:,}\n\n"
                f"*Payment Breakdown:*\n"
                f"• UPI: Rs. {upi_amount:,.0f}\n"
                f"• Cash: Rs. {cash_amount:,.0f}\n\n"
                f"Request ID: {sub_request['id']}\n"
                f"Submitted: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
                f"*Action:* Verify UPI receipt. Confirm cash collection once received."
            )
            
            admin_keyboard = [
                [
                    InlineKeyboardButton("✅ Approve UPI", callback_data=f"admin_approve_split_upi_{sub_request['id']}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_split_{sub_request['id']}"),
                ]
            ]
            admin_reply_markup = InlineKeyboardMarkup(admin_keyboard)
            
            for admin_id in admin_ids:
                try:
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=qr_bytes,
                        caption=admin_caption,
                        reply_markup=admin_reply_markup,
                        parse_mode="Markdown"
                    )
                    logger.info(f"✅ Split payment notification sent to admin {admin_id}")
                    
                    if profile_pic_url:
                        try:
                            await context.bot.send_photo(
                                chat_id=admin_id,
                                photo=profile_pic_url,
                                caption="📸 User Profile Picture"
                            )
                        except Exception as e:
                            logger.debug(f"Could not send profile picture: {e}")
                except Exception as e:
                    logger.error(f"Failed to send split payment notification to admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Error in split payment admin notification: {e}", exc_info=True)
        
        logger.info(f"Split payment initialized: User {user_id}, Total {total_amount}, UPI {upi_amount}, Cash {cash_amount}")
        return ENTER_UPI_VERIFICATION
        
    except Exception as e:
        logger.error(f"Error processing split payment: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Error processing split payment. Please contact admin."
        )
        return ConversationHandler.END


async def callback_cancel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel subscription"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("❌ Subscription cancelled.")
    return ConversationHandler.END


async def cmd_my_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's current subscription or pending request"""
    user_id = update.effective_user.id
    
    # First check for active subscription
    sub = get_user_subscription(user_id)
    
    if sub:
        now = datetime.now()
        days_remaining = (sub['end_date'] - now).days
        plan = SUBSCRIPTION_PLANS.get(sub['plan_id'], {})

        if success:
            # Schedule reminders if balance > 0 (48 hours from now)
            if balance > 0:
                from src.utils.event_dispatcher import schedule_followups
                from datetime import datetime, timedelta
                
                reminder_time = datetime.now() + timedelta(hours=48)
                if context and getattr(context, 'application', None):
                    schedule_followups(
                        context.application,
                        user_id,
                        'PAYMENT_REMINDER_1',
                        {
                            'amount_due': balance,
                            'due_in_hours': 48,
                        },
                        reminder_time,
                    )

            # Notify user
            try:
                end_date_str = end_date.strftime('%d-%m-%Y') if end_date else 'Not Set'
                message = (
                    f"✅ *Subscription Approved!*\n\n"
                    f"Plan: {request_details.get('plan_id', 'N/A')}\n"
                    f"Amount: Rs. {final_bill:,}\n"
                    f"UPI Received: Rs. {upi_received:,}\n"
                    f"Cash Received: Rs. {cash_received:,}\n"
                    f"Balance: Rs. {balance:,}\n"
                    f"Valid Until: {end_date_str}\n\n"
                    f"Your subscription is now active! 🎉"
                )
                await context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
                logger.info(f"Approval notification sent to user {user_id}")
            except Exception as e:
                logger.debug(f"Could not send approval notification to user: {e}")
            
            # Update UI
            await query.edit_message_text(
                f"✅ Subscription Approved!\n\n"
                f"Final Bill: Rs. {final_bill:,}\n"
                f"UPI Received: Rs. {upi_received:,}\n"
                f"Cash Received: Rs. {cash_received:,}\n"
                f"Balance: Rs. {balance:,}\n"
                f"Valid Until: {end_date.strftime('%d-%m-%Y') if end_date else 'Not Set'}\n\n"
                f"Reminders scheduled for outstanding balance."
            )
            
            return ConversationHandler.END
        await update.message.reply_text("❌ Admin access only.")
        return
    
    await show_pending_subscriptions_list(update, context)


async def show_pending_subscriptions_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of pending subscriptions (can be called from message or callback)"""
    # Handle both command and callback contexts
    if update.callback_query:
        message = update.callback_query.message
    else:
        message = update.message
    
    pending = get_pending_subscription_requests()
    
    if not pending:
        text = "📭 No pending subscription requests."
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown")
        else:
            await message.reply_text(text, parse_mode="Markdown")
        return
    
    text = f"*📋 Pending Subscriptions ({len(pending)})*\n\n"
    
    for sub in pending:
        plan = SUBSCRIPTION_PLANS.get(sub['plan_id'], {})
        text += (
            f"👤 {sub['full_name']}\n"
            f"📱 {sub['phone']}\n"
            f"💰 Amount: Rs. {sub['amount']:,}\n"
            f"📅 Plan: {plan.get('name', 'Unknown')}\n"
            f"🆔 Request ID: `{sub['id']}`\n"
            f"─────────────────────\n"
        )
    
    keyboard = [
        [InlineKeyboardButton("👉 Approve Subscription", callback_data="admin_sub_approve")],
        [InlineKeyboardButton("← Back", callback_data="cmd_notifications")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )



async def cmd_admin_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command - show pending subscription requests"""
    uid = update.effective_user.id
    if not is_admin(uid):
        # If invoked via message
        if update.message:
            await update.message.reply_text("❌ Admin access only.")
        else:
            await update.callback_query.answer("❌ Admin access only.", show_alert=True)
        return
    return await show_pending_subscriptions_list(update, context)


async def callback_admin_approve_upi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Start UPI approval process - ask for amount"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    request_id = int(query.data.split("_")[-1])
    try:
        await query.answer()
    except Exception as answer_err:
        logger.warning(f"callback_admin_approve_upi: query.answer failed: {answer_err}")
    
    try:
        from src.database.subscription_operations import get_subscription_request_details
        
        # Get request details
        request_details = get_subscription_request_details(request_id)
        if not request_details:
            try:
                await query.edit_message_text("❌ Request not found")
            except:
                try:
                    await query.edit_message_caption("❌ Request not found")
                except:
                    pass
            return
        
        # Store request details in context for later
        context.user_data['approving_request_id'] = request_id
        context.user_data['approving_request_details'] = request_details
        context.user_data['payment_method'] = 'upi'
        
        # Get plan duration to show admin
        plan = SUBSCRIPTION_PLANS.get(request_details['plan_id'], {})
        duration_text = f"{plan.get('duration_days', 0)} days" if plan else "Unknown"
        
        # Ask admin to enter the amount received
        message = query.message
        text = (
            f"*💰 Enter Amount Received*\n\n"
            f"User: {request_details.get('user_name', 'Unknown')}\n"
            f"Plan: {plan.get('name', 'Unknown')} ({duration_text})\n"
            f"Expected: Rs. {request_details['amount']:,}\n\n"
            f"Please reply with the amount you received from the user.\n"
            f"Example: 2500\n\n"
            f"ℹ️ You'll select a custom end date in the next step."
        )
        
        # Try to edit appropriate message type
        try:
            if getattr(message, "photo", None):
                await query.edit_message_caption(text, parse_mode="Markdown")
            elif getattr(message, "text", None):
                await query.edit_message_text(text, parse_mode="Markdown")
            else:
                await message.reply_text(text, parse_mode="Markdown")
        except Exception as edit_err:
            logger.warning(f"Edit attempt failed: {edit_err}, trying caption")
            try:
                await query.edit_message_caption(text, parse_mode="Markdown")
            except:
                logger.warning(f"Caption failed, trying text")
                try:
                    await query.edit_message_text(text, parse_mode="Markdown")
                except:
                    logger.warning(f"Text failed, trying reply")
                    await message.reply_text(text, parse_mode="Markdown")
        
        logger.info(f"Admin {query.from_user.id} starting UPI approval for request {request_id}")
        return ADMIN_ENTER_AMOUNT
    except Exception as e:
        logger.error(f"Error in callback_admin_approve_upi: {e}", exc_info=True)
        try:
            await query.edit_message_text("❌ Error starting approval process")
        except:
            try:
                await query.edit_message_caption("❌ Error starting approval process")
            except:
                pass


async def callback_admin_reject_upi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Reject UPI subscription from QR notification"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    request_id = int(query.data.split("_")[-1])
    await query.answer()
    
    try:
        # Reject the subscription
        success = reject_subscription(request_id, "UPI payment not verified by admin")
        
        if success:
            message = query.message
            text = (
                "✅ *UPI Payment Rejected!*\n\n"
                "User will receive notification and can try again."
            )
            try:
                if getattr(message, "photo", None):
                    await query.edit_message_caption(text, parse_mode="Markdown")
                else:
                    await query.edit_message_text(text, parse_mode="Markdown")
            except:
                try:
                    await query.edit_message_caption(text, parse_mode="Markdown")
                except:
                    await query.edit_message_text(text, parse_mode="Markdown")
            logger.info(f"Admin {query.from_user.id} rejected UPI subscription {request_id}")
        else:
            try:
                await query.edit_message_text("❌ Error rejecting subscription")
            except:
                await query.edit_message_caption("❌ Error rejecting subscription")
    except Exception as e:
        logger.error(f"Error in callback_admin_reject_upi: {e}")
        try:
            await query.edit_message_text("❌ Error rejecting subscription")
        except:
            try:
                await query.edit_message_caption("❌ Error rejecting subscription")
            except:
                pass


async def callback_admin_approve_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Start cash approval process - ask for amount"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    request_id = int(query.data.split("_")[-1])
    await query.answer()
    
    try:
        from src.database.subscription_operations import get_subscription_request_details
        
        # Get request details
        request_details = get_subscription_request_details(request_id)
        if not request_details:
            try:
                await query.edit_message_text("❌ Request not found")
            except:
                await query.edit_message_caption("❌ Request not found")
            return
        
        # Store request details in context for later
        context.user_data['approving_request_id'] = request_id
        context.user_data['approving_request_details'] = request_details
        context.user_data['payment_method'] = 'cash'
        
        # Get plan duration to show admin
        plan = SUBSCRIPTION_PLANS.get(request_details['plan_id'], {})
        duration_text = f"{plan.get('duration_days', 0)} days" if plan else "Unknown"
        
        # Ask admin to enter the amount received
        text = (
            f"*💰 Enter Amount Received*\n\n"
            f"User: {request_details.get('user_name', 'Unknown')}\n"
            f"Plan: {plan.get('name', 'Unknown')} ({duration_text})\n"
            f"Expected: Rs. {request_details['amount']:,}\n\n"
            f"Please reply with the amount you received from the user.\n"
            f"Example: 2500\n\n"
            f"ℹ️ You'll select a custom end date in the next step."
        )
        
        # Try to edit as caption (for photo messages), fallback to text
        message = query.message
        try:
            if getattr(message, "photo", None):
                await query.edit_message_caption(text, parse_mode="Markdown")
            else:
                await query.edit_message_text(text, parse_mode="Markdown")
        except Exception as edit_err:
            logger.warning(f"First edit attempt failed: {edit_err}, trying alternative method")
            # Try alternative approach
            if getattr(message, "photo", None):
                await query.edit_message_caption(text, parse_mode="Markdown")
            else:
                await query.edit_message_text(text, parse_mode="Markdown")
        
        logger.info(f"Admin {query.from_user.id} starting cash approval for request {request_id}")
        return ADMIN_ENTER_AMOUNT
    except Exception as e:
        logger.error(f"Error in callback_admin_approve_cash: {e}")
        try:
            await query.edit_message_text("❌ Error starting approval process")
        except:
            try:
                await query.edit_message_caption("❌ Error starting approval process")
            except:
                pass


async def callback_admin_approve_split_upi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Start split payment UPI approval - ask for FINAL BILL amount"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    request_id = int(query.data.split("_")[-1])
    
    # Simplified, robust implementation: ask admin for final bill amount and move to ADMIN_ENTER_BILL
    try:
        await query.answer()
    except Exception:
        logger.debug("callback_admin_approve_split_upi: query.answer failed")

    try:
        from src.database.subscription_operations import get_subscription_request_details

        request_details = get_subscription_request_details(request_id)
        if not request_details:
            try:
                await query.edit_message_text("❌ Request not found")
            except Exception:
                try:
                    await query.edit_message_caption("❌ Request not found")
                except Exception:
                    pass
            return ConversationHandler.END

        context.user_data['approving_request_id'] = request_id
        context.user_data['approving_request_details'] = request_details
        context.user_data['payment_method'] = 'split'
        context.user_data['approval_step'] = 'enter_bill'

        plan = SUBSCRIPTION_PLANS.get(request_details['plan_id'], {})

        text = (
            f"*💰 STEP 1: Enter Final Bill Amount*\n\n"
            f"User: {request_details.get('user_name', 'Unknown')}\n"
            f"Plan: {plan.get('name', 'Unknown')}\n"
            f"Expected: Rs. {request_details['amount']:,}\n\n"
            f"⚠️ *Enter the FINAL BILL amount* (must be > 0)\n\n"
            f"This will be the SINGLE SOURCE OF TRUTH for accounting.\n\n"
            f"Example: 2500"
        )

        await query.edit_message_text(text, parse_mode="Markdown")
        logger.info(f"Admin {query.from_user.id} starting split UPI approval for request {request_id} - asking for bill amount")
        return ADMIN_ENTER_BILL
    except Exception as e:
        logger.error(f"Error in callback_admin_approve_split_upi: {e}", exc_info=True)
        try:
            await query.edit_message_text("❌ Error starting approval process")
        except Exception:
            pass
        return ConversationHandler.END


async def callback_admin_confirm_split_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Confirm cash portion of split payment"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    request_id = int(query.data.split("_")[-1])
    
    try:
        await query.answer()
    except Exception as answer_err:
        logger.warning(f"Split cash confirm: query.answer failed: {answer_err}")
    
    try:
        from src.database.subscription_operations import (
            get_subscription_request_details, record_split_cash_payment,
            get_receivable_by_source
        )
        from src.database.ar_operations import get_receivable_breakdown
        
        # Get request details
        request_details = get_subscription_request_details(request_id)
        if not request_details:
            await query.edit_message_text("❌ Request not found")
            return
        
        user_id = request_details['user_id']
        
        # Get receivable and confirm cash
        receivable = get_receivable_by_source('subscription', request_id)
        if not receivable:
            await query.edit_message_text("❌ Payment record not found")
            return
        
        # Record cash payment
        success = record_split_cash_payment(user_id, request_id)
        
        if success:
            # Get updated breakdown
            breakdown = get_receivable_breakdown(receivable.get('receivable_id'))
            upi_amount = breakdown.get('methods', {}).get('upi', 0)
            cash_amount = breakdown.get('methods', {}).get('cash', 0)
            status = breakdown.get('receivable', {}).get('status', 'unknown')
            
            # Cancel payment reminders since payment is now complete
            try:
                if context and getattr(context, 'application', None):
                    # Get jobs for this user's payment reminders
                    job_names = [
                        f"payment_reminder_1_{user_id}",
                        f"payment_reminder_2_{user_id}",
                    ]
                    for job_name in job_names:
                        try:
                            jobs = context.application.job_queue.get_jobs_by_name(job_name)
                            for job in jobs:
                                job.schedule_removal()
                            logger.info(f"[SCHEDULER] Cancelled payment reminder job: {job_name}")
                        except Exception as e:
                            logger.debug(f"Could not cancel job {job_name}: {e}")
            except Exception as e:
                logger.debug(f"Could not cancel payment reminders: {e}")
            
            # Notify user
            user = get_user(user_id)
            if user and user.get('user_id'):
                try:
                    message = (
                        f"✅ *Split Payment - Cash Confirmed*\n\n"
                        f"*Payment Complete!*\n"
                        f"• 📱 UPI: Rs. {upi_amount:,.0f} ✅\n"
                        f"• 💵 Cash: Rs. {cash_amount:,.0f} ✅\n\n"
                        f"Status: PAID\n"
                        f"Your subscription is fully active. 🎉"
                    )
                    await context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
                    logger.info(f"✅ Split cash confirmation notification sent to user {user_id}")
                except Exception as e:
                    logger.debug(f"Could not send cash confirmation to user: {e}")
            
            await query.edit_message_text(
                f"✅ *Split Payment - Cash Confirmed*\n\n"
                f"User: {request_details.get('user_name', 'Unknown')}\n"
                f"• UPI: Rs. {upi_amount:,.0f} ✅\n"
                f"• Cash: Rs. {cash_amount:,.0f} ✅\n\n"
                f"Status: {status.upper()}\n"
                f"Payment fully settled."
            )
            logger.info(f"Admin {query.from_user.id} confirmed split cash payment for request {request_id}")
        else:
            await query.edit_message_text("❌ Failed to confirm cash payment")
            logger.error(f"Failed to confirm cash for request {request_id}")
    
    except Exception as e:
        logger.error(f"Error in callback_admin_confirm_split_cash: {e}", exc_info=True)
        try:
            await query.edit_message_text("❌ Error confirming cash payment")
        except:
            pass


async def callback_admin_reject_split(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Reject split payment request"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    request_id = int(query.data.split("_")[-1])
    
    try:
        await query.answer()
    except Exception as answer_err:
        logger.warning(f"Split reject: query.answer failed: {answer_err}")
    
    try:
        from src.database.subscription_operations import (
            get_subscription_request_details, reject_subscription
        )
        
        # Get request details
        request_details = get_subscription_request_details(request_id)
        if not request_details:
            await query.edit_message_text("❌ Request not found")
            return
        
        user_id = request_details['user_id']
        
        # Reject subscription
        reason = "Split payment rejected by admin"
        reject_subscription(request_id, reason)
        
        # Notify user
        user = get_user(user_id)
        if user and user.get('user_id'):
            try:
                message = (
                    f"❌ *Split Payment - Rejected*\n\n"
                    f"Your split payment request has been rejected.\n"
                    f"Please contact the admin or try again."
                )
                await context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
                logger.info(f"❌ Split payment rejection notification sent to user {user_id}")
            except Exception as e:
                logger.debug(f"Could not send rejection notification: {e}")
        
        await query.edit_message_text(
            f"❌ *Split Payment - Rejected*\n\n"
            f"User: {request_details.get('user_name', 'Unknown')}\n"
            f"Reason: {reason}\n\n"
            f"User has been notified."
        )
        logger.info(f"Admin {query.from_user.id} rejected split payment for request {request_id}")
    
    except Exception as e:
        logger.error(f"Error in callback_admin_reject_split: {e}", exc_info=True)
        try:
            await query.edit_message_text("❌ Error rejecting payment")
        except:
            pass


async def callback_admin_approve_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Approve pay later (credit) subscription"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    request_id = int(query.data.split("_")[-1])
    
    try:
        await query.answer()
    except Exception as answer_err:
        logger.warning(f"Credit approve: query.answer failed: {answer_err}")
    
    try:
        from src.database.subscription_operations import (
            get_subscription_request_details, approve_subscription,
            get_receivable_by_source
        )
        
        # Get request details
        request_details = get_subscription_request_details(request_id)
        if not request_details:
            await query.edit_message_text("❌ Request not found")
            return
        
        user_id = request_details['user_id']
        plan_id = request_details['plan_id']
        total_amount = request_details['amount']
        
        # Auto-approve subscription for full amount
        plan = SUBSCRIPTION_PLANS.get(plan_id, {})
        end_date = datetime.now() + timedelta(days=plan.get('duration_days', 30))
        
        success = approve_subscription(request_id, total_amount, end_date)
        
        if success:
            # Notify user
            user = get_user(user_id)
            if user and user.get('user_id'):
                try:
                    message = (
                        f"✅ *Pay Later (Credit) - Approved*\n\n"
                        f"Plan: {plan.get('name', 'Unknown')}\n"
                        f"Amount: Rs. {total_amount:,}\n\n"
                        f"Your subscription is now active!\n"
                        f"Payment reminders will be sent to settle the outstanding amount. 🎉"
                    )
                    await context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
                    logger.info(f"✅ Credit approval notification sent to user {user_id}")
                except Exception as e:
                    logger.debug(f"Could not send approval notification to user: {e}")
            
            await query.edit_message_text(
                f"✅ *Pay Later (Credit) - Approved*\n\n"
                f"User: {request_details.get('user_name', 'Unknown')}\n"
                f"Plan: {plan.get('name', 'Unknown')}\n"
                f"Amount: Rs. {total_amount:,}\n\n"
                f"Subscription activated. Payment reminders will be sent."
            )
            logger.info(f"Admin {query.from_user.id} approved credit payment for request {request_id}")
        else:
            await query.edit_message_text("❌ Failed to approve subscription")
            logger.error(f"Failed to approve subscription for request {request_id}")
    
    except Exception as e:
        logger.error(f"Error in callback_admin_approve_credit: {e}", exc_info=True)
        try:
            await query.edit_message_text("❌ Error approving credit payment")
        except:
            pass


async def callback_admin_reject_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Reject pay later (credit) subscription"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    request_id = int(query.data.split("_")[-1])
    
    try:
        await query.answer()
    except Exception as answer_err:
        logger.warning(f"Credit reject: query.answer failed: {answer_err}")
    
    try:
        from src.database.subscription_operations import (
            get_subscription_request_details, reject_subscription
        )
        
        # Get request details
        request_details = get_subscription_request_details(request_id)
        if not request_details:
            await query.edit_message_text("❌ Request not found")
            return
        
        user_id = request_details['user_id']
        reason = "Pay later (credit) request rejected by admin"
        
        # Reject subscription
        reject_subscription(request_id, reason)
        
        # Notify user
        user = get_user(user_id)
        if user and user.get('user_id'):
            try:
                message = (
                    f"❌ *Pay Later (Credit) - Rejected*\n\n"
                    f"Your pay later request has been rejected.\n"
                    f"Please contact the admin or try another payment method."
                )
                await context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
                logger.info(f"❌ Credit rejection notification sent to user {user_id}")
            except Exception as e:
                logger.debug(f"Could not send rejection notification: {e}")
        
        await query.edit_message_text(
            f"❌ *Pay Later (Credit) - Rejected*\n\n"
            f"User: {request_details.get('user_name', 'Unknown')}\n"
            f"Reason: {reason}\n\n"
            f"User has been notified."
        )
        logger.info(f"Admin {query.from_user.id} rejected credit payment for request {request_id}")
    
    except Exception as e:
        logger.error(f"Error in callback_admin_reject_credit: {e}", exc_info=True)
        try:
            await query.edit_message_text("❌ Error rejecting credit payment")
        except:
            pass


async def callback_admin_reject_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Reject cash subscription payment"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    request_id = int(query.data.split("_")[-1])
    await query.answer()
    
    try:
        # Reject the subscription
        success = reject_subscription(request_id, "Cash payment not verified by admin")
        
        if success:
            message = query.message
            text = (
                "✅ *Cash Payment Rejected!*\n\n"
                "User will receive notification and can try again."
            )
            try:
                if getattr(message, "photo", None):
                    await query.edit_message_caption(text, parse_mode="Markdown")
                else:
                    await query.edit_message_text(text, parse_mode="Markdown")
            except:
                try:
                    await query.edit_message_caption(text, parse_mode="Markdown")
                except:
                    await query.edit_message_text(text, parse_mode="Markdown")
            logger.info(f"Admin {query.from_user.id} rejected cash subscription {request_id}")
        else:
            try:
                await query.edit_message_text("❌ Error rejecting subscription")
            except:
                await query.edit_message_caption("❌ Error rejecting subscription")
    except Exception as e:
        logger.error(f"Error in callback_admin_reject_cash: {e}")
        try:
            await query.edit_message_text("❌ Error rejecting subscription")
        except:
            try:
                await query.edit_message_caption("❌ Error rejecting subscription")
            except:
                pass


async def callback_admin_cancel_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Cancel the approval process"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    try:
        request_id = context.user_data.get('approving_request_id')
        await query.edit_message_text(
            "❌ *Approval Cancelled*\n\n"
            f"Request ID: {request_id}\n\n"
            "You can approve it later from the admin dashboard.",
            parse_mode="Markdown"
        )
        logger.info(f"Admin {query.from_user.id} cancelled approval for request {request_id}")
    except Exception as e:
        logger.error(f"Error in callback_admin_cancel_approval: {e}")
        await query.edit_message_text("❌ Approval cancelled")
    
    return ConversationHandler.END


async def handle_approval_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount input and show calendar for custom end date selection"""
    try:
        amount_str = update.message.text.strip()
        amount = int(amount_str)
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive. Try again:")
            return ADMIN_ENTER_AMOUNT
        
        # Store amount in context
        context.user_data['approval_amount'] = amount
        context.user_data['calendar_month'] = datetime.now()
        
        # Show calendar for selecting custom end date
        calendar_markup = await generate_calendar_keyboard(context, use_admin_pattern=True)
        await update.message.reply_text(
            f"✅ Amount: Rs. {amount:,}\n\n"
            f"*📅 Select Subscription End Date*\n\n"
            f"Choose a custom date or use the quick select buttons below:",
            reply_markup=calendar_markup,
            parse_mode="Markdown"
        )
        
        return ADMIN_SELECT_DATE
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number:\n\nExample: 2500")
        return ADMIN_ENTER_AMOUNT
        return ADMIN_ENTER_AMOUNT


async def handle_admin_enter_bill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin entering FINAL BILL amount (STEP 1)"""
    try:
        bill_amount = float(update.message.text.strip().replace(',', ''))
        
        if bill_amount <= 0:
            await update.message.reply_text("❌ Bill amount must be greater than 0. Please try again:")
            return ADMIN_ENTER_BILL
        
        # Store bill amount
        context.user_data['final_bill_amount'] = bill_amount
        
        request_details = context.user_data.get('approving_request_details')
        payment_method = context.user_data.get('payment_method')
        
        # STEP 2: Ask for payment received based on method
        if payment_method == 'split':
            # For split: ask for UPI received first
            context.user_data['approval_step'] = 'enter_upi_received'
            text = (
                f"*📱 STEP 2A: Enter UPI Amount Received*\n\n"
                f"Final Bill: Rs. {bill_amount:,.2f}\n\n"
                f"How much did you receive via UPI?\n"
                f"(Must be >= 0 and <= {bill_amount:,.2f})\n\n"
                f"Example: 1000"
            )
            await update.message.reply_text(text, parse_mode="Markdown")
            return ADMIN_ENTER_UPI_RECEIVED
        elif payment_method == 'upi':
            context.user_data['approval_step'] = 'enter_upi_received'
            text = (
                f"*📱 STEP 2: Enter UPI Amount Received*\n\n"
                f"Final Bill: Rs. {bill_amount:,.2f}\n\n"
                f"How much did you receive via UPI?\n"
                f"(Must be >= 0 and <= {bill_amount:,.2f})\n\n"
                f"Example: {bill_amount:,.0f}"
            )
            await update.message.reply_text(text, parse_mode="Markdown")
            return ADMIN_ENTER_UPI_RECEIVED
        elif payment_method == 'cash':
            context.user_data['approval_step'] = 'enter_cash_received'
            text = (
                f"*💵 STEP 2: Enter Cash Amount Received*\n\n"
                f"Final Bill: Rs. {bill_amount:,.2f}\n\n"
                f"How much did you receive via Cash?\n"
                f"(Must be >= 0 and <= {bill_amount:,.2f})\n\n"
                f"Example: {bill_amount:,.0f}"
            )
            await update.message.reply_text(text, parse_mode="Markdown")
            return ADMIN_ENTER_CASH_RECEIVED
        elif payment_method == 'credit':
            # Pay later: received = 0
            context.user_data['upi_received'] = 0
            context.user_data['cash_received'] = 0
            # Move to calendar
            return await show_calendar_or_confirm(update, context)
            
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number:\n\nExample: 2500")
        return ADMIN_ENTER_BILL


async def handle_admin_enter_upi_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin entering UPI amount received (STEP 2A for split, STEP 2 for UPI)"""
    try:
        upi_received = float(update.message.text.strip().replace(',', ''))
        final_bill = context.user_data.get('final_bill_amount', 0)
        
        if upi_received < 0 or upi_received > final_bill:
            await update.message.reply_text(
                f"❌ UPI amount must be between 0 and {final_bill:,.2f}. Please try again:"
            )
            return ADMIN_ENTER_UPI_RECEIVED
        
        # Store UPI received
        context.user_data['upi_received'] = upi_received
        
        payment_method = context.user_data.get('payment_method')
        
        if payment_method == 'split':
            # For split: now ask for CASH received
            context.user_data['approval_step'] = 'enter_cash_received'
            remaining = final_bill - upi_received
            text = (
                f"*💵 STEP 2B: Enter Cash Amount Received*\n\n"
                f"Final Bill: Rs. {final_bill:,.2f}\n"
                f"UPI Received: Rs. {upi_received:,.2f}\n"
                f"Remaining: Rs. {remaining:,.2f}\n\n"
                f"How much did you receive via Cash?\n"
                f"(Must be >= 0 and <= {remaining:,.2f})\n\n"
                f"Example: {remaining:,.0f}"
            )
            await update.message.reply_text(text, parse_mode="Markdown")
            return ADMIN_ENTER_CASH_RECEIVED
        else:
            # UPI only: set cash to 0 and move to calendar/confirm
            context.user_data['cash_received'] = 0
            return await show_calendar_or_confirm(update, context)
            
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number:\n\nExample: 1000")
        return ADMIN_ENTER_UPI_RECEIVED


async def handle_admin_enter_cash_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin entering CASH amount received (STEP 2B for split, STEP 2 for cash)"""
    try:
        cash_received = float(update.message.text.strip().replace(',', ''))
        final_bill = context.user_data.get('final_bill_amount', 0)
        upi_received = context.user_data.get('upi_received', 0)
        total_received = upi_received + cash_received
        
        if cash_received < 0 or total_received > final_bill:
            await update.message.reply_text(
                f"❌ Cash amount invalid. Total received cannot exceed {final_bill:,.2f}.\n"
                f"UPI already received: {upi_received:,.2f}\n"
                f"Maximum cash: {final_bill - upi_received:,.2f}\n\n"
                f"Please try again:"
            )
            return ADMIN_ENTER_CASH_RECEIVED
        
        # Store cash received
        context.user_data['cash_received'] = cash_received
        
        # Move to calendar (for subscription) or final confirm
        return await show_calendar_or_confirm(update, context)
            
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number:\n\nExample: 1500")
        return ADMIN_ENTER_CASH_RECEIVED


async def show_calendar_or_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show calendar for subscription end date (STEP 3) or skip to confirm"""
    request_details = context.user_data.get('approving_request_details')
    plan_id = request_details.get('plan_id')
    
    # Check if this is a subscription (has plan_id)
    if plan_id:
        # STEP 3: Show calendar
        plan = SUBSCRIPTION_PLANS.get(plan_id, {})
        duration_days = plan.get('duration_days', 30)
        
        # Generate calendar
        from src.utils.calendar_picker import generate_calendar
        calendar_markup = generate_calendar()
        
        final_bill = context.user_data.get('final_bill_amount', 0)
        upi_received = context.user_data.get('upi_received', 0)
        cash_received = context.user_data.get('cash_received', 0)
        balance = final_bill - upi_received - cash_received
        
        text = (
            f"*📅 STEP 3: Select Subscription End Date*\n\n"
            f"Plan: {plan.get('name', 'Unknown')} ({duration_days} days)\n"
            f"User: {request_details.get('user_name', 'Unknown')}\n\n"
            f"*Payment Summary:*\n"
            f"Final Bill: Rs. {final_bill:,.2f}\n"
            f"UPI Received: Rs. {upi_received:,.2f}\n"
            f"Cash Received: Rs. {cash_received:,.2f}\n"
            f"Balance: Rs. {balance:,.2f}\n\n"
            f"Please select the subscription end date:"
        )
        
        await update.message.reply_text(
            text,
            reply_markup=calendar_markup,
            parse_mode="Markdown"
        )
        return ADMIN_SELECT_DATE
    else:
        # Not a subscription: show final confirm
        return await show_final_confirmation(update, context)


async def show_final_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show final confirmation screen (STEP 4)"""
    request_details = context.user_data.get('approving_request_details')
    final_bill = context.user_data.get('final_bill_amount', 0)
    upi_received = context.user_data.get('upi_received', 0)
    cash_received = context.user_data.get('cash_received', 0)
    balance = final_bill - upi_received - cash_received
    end_date = context.user_data.get('selected_end_date')
    request_id = context.user_data.get('approving_request_id')
    
    text = (
        f"*✅ STEP 4: Final Confirmation*\n\n"
        f"User: {request_details.get('user_name', 'Unknown')}\n\n"
        f"*Payment Summary:*\n"
        f"💰 Total Bill: Rs. {final_bill:,.2f}\n"
    )
    
    if upi_received > 0:
        text += f"📱 UPI: Rs. {upi_received:,.2f}\n"
    if cash_received > 0:
        text += f"💵 Cash: Rs. {cash_received:,.2f}\n"
    
    text += f"💳 Balance: Rs. {balance:,.2f}\n\n"
    
    if end_date:
        text += f"📅 End Date: {end_date.strftime('%d %b %Y')}\n\n"
    
    if balance == 0:
        text += "✅ *FULL PAYMENT - Subscription will activate*"
    elif upi_received + cash_received > 0:
        text += f"⚠️ *PARTIAL PAYMENT - Balance: Rs. {balance:,.2f}*\n"
        text += "Reminders will be sent after 48 hours."
    else:
        text += "⚠️ *PAY LATER - Full amount outstanding*\n"
        text += "Reminders will be sent after 48 hours."
    
    keyboard = [
        [
            InlineKeyboardButton("✅ CONFIRM", callback_data=f"admin_final_confirm_{request_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"admin_cancel_approval_{request_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return ADMIN_FINAL_CONFIRM


async def callback_admin_final_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle final admin confirmation and complete approval"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return ConversationHandler.END
    
    try:
        request_id = context.user_data.get('approving_request_id')
        request_details = context.user_data.get('approving_request_details')
        final_bill = context.user_data.get('final_bill_amount', 0)
        upi_received = context.user_data.get('upi_received', 0)
        cash_received = context.user_data.get('cash_received', 0)
        balance = final_bill - upi_received - cash_received
        end_date = context.user_data.get('selected_end_date')
        
        # Approve subscription with final bill amount
        from src.database.subscription_operations import (
            approve_subscription,
            get_pending_payment,
            finalize_pending_payment,
        )

        payment_lines = []
        user_id = request_details['user_id']

        if upi_received > 0:
            pending = get_pending_payment(request_id, 'upi')
            if pending and pending.get('id'):
                finalize_pending_payment(pending['id'], reference=pending.get('reference'))
            else:
                payment_lines.append({'method': 'upi', 'amount': upi_received, 'reference': None})

        if cash_received > 0:
            pending_cash = get_pending_payment(request_id, 'cash')
            if pending_cash and pending_cash.get('id'):
                finalize_pending_payment(pending_cash['id'], reference=pending_cash.get('reference'))
            else:
                payment_lines.append({'method': 'cash', 'amount': cash_received, 'reference': None})

        success = approve_subscription(
            request_id,
            final_bill,
            end_date,
            payment_lines=payment_lines,
            admin_user_id=query.from_user.id,
        )

        if success:
            # Schedule reminders if balance > 0 (48 hours from now)
            if balance > 0:
                from src.utils.event_dispatcher import schedule_followups
                from datetime import datetime, timedelta
                
                # Schedule first reminder 48 hours from now
                reminder_time = datetime.now() + timedelta(hours=48)
                if context and getattr(context, 'application', None):
                    schedule_followups(
                        context.application, user_id, 'PAYMENT_REMINDER_1',
                        {
                            'name': request_details.get('user_name', ''),
                            'amount': balance,
                            'delay_hours': 48
                        }
                    )
                    logger.info(f"Payment reminder scheduled (48hr delay) for user {user_id}, balance {balance}")
            
            # Notify user
            from src.database.user_operations import get_user
            user = get_user(user_id)
            if user and user.get('user_id'):
                plan = SUBSCRIPTION_PLANS.get(request_details.get('plan_id'), {})
                message = (
                    f"✅ *Subscription Approved!*\n\n"
                    f"Plan: {plan.get('name', 'Unknown')}\n"
                    f"Amount: Rs. {final_bill:,.2f}\n"
                )
                if upi_received > 0:
                    message += f"UPI: Rs. {upi_received:,.2f} ✅\n"
                if cash_received > 0:
                    message += f"Cash: Rs. {cash_received:,.2f} ✅\n"
                if balance > 0:
                    message += f"\n⚠️ Balance: Rs. {balance:,.2f}\n"
                    message += "Reminder will be sent in 48 hours."
                if end_date:
                    message += f"\n📅 Valid until: {end_date.strftime('%d %b %Y')}"
                
                try:
                    await context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
                except Exception as e:
                    logger.debug(f"Could not send approval notification: {e}")
            
            await query.edit_message_text(
                f"✅ *Approval Complete!*\n\n"
                f"User: {request_details.get('user_name', 'Unknown')}\n"
                f"Amount: Rs. {final_bill:,.2f}\n"
                f"Balance: Rs. {balance:,.2f}",
                parse_mode="Markdown"
            )
            
            logger.info(f"Admin {query.from_user.id} approved request {request_id} - Bill:{final_bill}, Balance:{balance}")
            return ConversationHandler.END
        else:
            await query.edit_message_text("❌ Failed to approve. Please try again.")
            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Error in callback_admin_final_confirm: {e}", exc_info=True)
        await query.edit_message_text("❌ Error completing approval")
        return ConversationHandler.END


async def callback_approve_with_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Complete approval after date selection - store date and show final confirm"""
    query = update.callback_query
    logger.info(f"[APPROVE_DATE] callback_approve_with_date triggered by admin {query.from_user.id}, callback_data={query.data}")
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    try:
        # Extract date from callback data
        date_str = query.data.split("_")[-1]
        end_date = datetime.strptime(date_str, "%Y%m%d")
        logger.info(f"[APPROVE_DATE] Extracted end_date: {end_date}")
        
        # Store end date in context
        context.user_data['selected_end_date'] = end_date
        
        # Show final confirmation screen
        # Convert query update to message-like update for show_final_confirmation
        from types import SimpleNamespace
        fake_update = SimpleNamespace(message=query.message)
        return await show_final_confirmation(fake_update, context)
        
    except Exception as e:
        logger.error(f"Error in callback_approve_with_date: {e}", exc_info=True)
        await query.edit_message_text("❌ Error processing date selection")
        return ConversationHandler.END


# Keep old callback_approve_with_date logic as fallback
async def callback_approve_with_date_old(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Complete approval after date selection"""
    query = update.callback_query
    logger.info(f"[APPROVE_DATE] callback_approve_with_date triggered by admin {query.from_user.id}, callback_data={query.data}")
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    try:
        # Extract date from callback data
        date_str = query.data.split("_")[-1]
        end_date = datetime.strptime(date_str, "%Y%m%d")
        logger.info(f"[APPROVE_DATE] Extracted end_date: {end_date}")
        
        request_id = context.user_data.get('approving_request_id')
        amount = context.user_data.get('approval_amount')
        request_details = context.user_data.get('approving_request_details')
        payment_method = context.user_data.get('payment_method', 'cash')
        logger.info(f"[APPROVE_DATE] Context data - request_id:{request_id}, amount:{amount}, payment_method:{payment_method}")
        
        if not request_id or not amount or not request_details:
            await query.edit_message_text("❌ Error: Missing approval data. Please try again.")
            return ConversationHandler.END
        
        # Approve the subscription
        payment_lines = [
            {
                'method': payment_method or 'cash',
                'amount': amount,
                'reference': None,
            }
        ]

        success = approve_subscription(
            request_id,
            amount,
            end_date,
            payment_lines=payment_lines,
            admin_user_id=query.from_user.id,
        )
        
        if success:
            # Also mark user as approved (in case they were pending)
            from src.database.user_operations import approve_user
            try:
                approve_user(request_details['user_id'], query.from_user.id)
                logger.info(f"User {request_details['user_id']} approval_status set to 'approved'")
            except Exception as approve_err:
                logger.warning(f"Could not approve user status: {approve_err}")
            
            # Send detailed payment receipt to user
            receipt_message = (
                "✅ *Payment Approved!*\n\n"
                "📋 *Payment Receipt*\n"
                f"💰 Amount: Rs. {amount:,}\n"
                f"📅 Valid Until: {end_date.strftime('%d-%m-%Y')}\n"
                f"✓ Plan: {SUBSCRIPTION_PLANS.get(request_details.get('plan_id', 1), {}).get('name', 'Subscription')}\n\n"
                f"🎉 *You now have full access to all gym features!*\n\n"
                "📱 *What to do next:*\n"
                "1️⃣ Send /menu to access the app\n"
                "2️⃣ Enjoy all features:\n"
                "   • 💪 Activity Tracking\n"
                "   • ⚖️ Weight Tracking\n"
                "   • 🏆 Challenges\n"
                "   • 🥤 Shake Orders\n"
                "   • 📊 Statistics\n\n"
                "Thank you for subscribing! 🙏"
            )
            
            try:
                await context.bot.send_message(
                    chat_id=request_details['user_id'],
                    text=receipt_message,
                    parse_mode="Markdown"
                )
                logger.info(f"Payment receipt sent to user {request_details['user_id']}")
            except Exception as e:
                logger.error(f"Error notifying user: {e}")
            
            await query.edit_message_text(
                f"✅ *{payment_method.upper()} Payment Approved!*\n\n"
                f"User: {request_details.get('user_name', 'Unknown')}\n"
                f"Plan: {SUBSCRIPTION_PLANS[request_details['plan_id']]['name']}\n"
                f"Amount Received: Rs. {amount:,}\n"
                f"End Date: {end_date.strftime('%d-%m-%Y')}\n\n"
                f"Payment receipt sent to user. ✅",
                parse_mode="Markdown"
            )
            logger.info(f"Admin {query.from_user.id} approved {payment_method} subscription {request_id} with amount {amount} and end date {end_date}")
            # If there's an accounts_receivable for this subscription and outstanding balance, schedule payment reminders
            try:
                from src.database.ar_operations import get_receivable_breakdown, get_receivable_by_source
                from src.utils.event_dispatcher import schedule_followups
                rec = None
                rr = get_receivable_by_source('subscription', request_id)
                if rr:
                    rec = get_receivable_breakdown(rr.get('receivable_id'))
                balance = rec.get('balance', 0) if rec else 0
                if balance and balance > 0 and context and getattr(context, 'application', None):
                    schedule_followups(context.application, request_details['user_id'], 'PAYMENT_REMINDER_1', {'name': request_details.get('user_name',''), 'amount': balance})
            except Exception:
                logger.debug('Could not schedule follow-ups for subscription approval')
        else:
            # Better error message
            error_msg = (
                "❌ *Error Approving Subscription*\n\n"
                "Failed to process the subscription approval. Please try again.\n\n"
                "If the problem persists:\n"
                "• Check database connection\n"
                "• Verify user still exists\n"
                "• Try starting the approval process again"
            )
            await query.edit_message_text(error_msg, parse_mode="Markdown")
            logger.error(f"Failed to approve subscription {request_id} for user {request_details['user_id']}")
        
        # Clear context
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        await query.edit_message_text("❌ Invalid date selected. Please try again.")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in callback_approve_with_date: {e}", exc_info=True)
        await query.edit_message_text("❌ An unexpected error occurred. Please try again.")
        return ConversationHandler.END


async def callback_admin_approve_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Approve or reject subscription"""
    query = update.callback_query
    
    if not is_admin(query.from_user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return
    
    pending = get_pending_subscription_requests()
    
    if not pending:
        await query.answer("No pending subscriptions", show_alert=True)
        return
    
    # Show first pending
    sub = pending[0]
    plan = SUBSCRIPTION_PLANS.get(sub['plan_id'], {})
    
    message = (
        f"*Approve Subscription*\n\n"
        f"User: {sub['full_name']}\n"
        f"Phone: {sub['phone']}\n"
        f"Amount: Rs. {sub['amount']:,}\n"
        f"Plan: {plan.get('name', 'Unknown')}\n\n"
        f"Choose action:"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm Payment", callback_data=f"sub_approve_{sub['id']}")],
        [InlineKeyboardButton("📝 Custom Amount & Date", callback_data=f"sub_custom_{sub['id']}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"sub_reject_{sub['id']}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.user_data['pending_sub_id'] = sub['id']
    context.user_data['pending_sub'] = sub
    
    await query.answer()
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")


async def callback_approve_sub_standard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Standard approval with default amount and date"""
    query = update.callback_query
    sub_id = int(query.data.split("_")[-1])
    
    pending = get_pending_subscription_requests()
    sub = next((s for s in pending if s['id'] == sub_id), None)
    
    if not sub:
        await query.answer("Subscription not found", show_alert=True)
        return
    
    plan = SUBSCRIPTION_PLANS.get(sub['plan_id'], {})
    end_date = datetime.now() + timedelta(days=plan['duration_days'])
    
    payment_lines = [{'method': 'cash', 'amount': sub['amount'], 'reference': None}]

    if approve_subscription(sub_id, sub['amount'], end_date, payment_lines=payment_lines, admin_user_id=query.from_user.id):
        await query.answer()
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=sub['user_id'],
                text="✅ *Subscription Approved!*\n\n"
                     f"Your payment has been received.\n\n"
                     f"💰 Amount: Rs. {sub['amount']:,}\n"
                     f"📅 Valid Until: {end_date.strftime('%d-%m-%Y')}\n\n"
                     f"You now have full access to the app! 🎉\n\n"
                     f"Start tracking your fitness journey!",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
        
        await query.edit_message_text(
            f"✅ *Subscription Approved*\n\n"
            f"User: {sub['full_name']}\n"
            f"Amount: Rs. {sub['amount']:,}\n"
            f"End Date: {end_date.strftime('%d-%m-%Y')}\n\n"
            f"✓ User notified",
            parse_mode="Markdown"
        )
        # Schedule payment follow-ups if receivable still has outstanding balance
        try:
            from src.database.ar_operations import get_receivable_breakdown, get_receivable_by_source
            from src.utils.event_dispatcher import schedule_followups
            rec_row = get_receivable_by_source('subscription', sub_id)
            receivable_id = rec_row.get('receivable_id') if rec_row else None
            if receivable_id:
                breakdown = get_receivable_breakdown(receivable_id)
                balance = breakdown.get('balance', 0)
                if balance and balance > 0 and context and getattr(context, 'application', None):
                    schedule_followups(context.application, sub['user_id'], 'PAYMENT_REMINDER_1', {'name': sub.get('full_name',''), 'amount': balance})
        except Exception:
            logger.debug('Could not schedule follow-ups for subscription approval')
    else:
        await query.edit_message_text("❌ Error approving subscription")


async def callback_custom_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Enter custom amount"""
    query = update.callback_query
    sub_id = int(query.data.split("_")[-1])
    
    context.user_data['pending_sub_id'] = sub_id
    
    await query.answer()
    await query.edit_message_text(
        "Enter custom amount to charge:\n\n"
        "Example: 2500"
    )
    
    return ADMIN_ENTER_AMOUNT


async def generate_calendar_keyboard(context: ContextTypes.DEFAULT_TYPE, use_admin_pattern: bool = False):
    """Generate an inline calendar for date selection
    
    Args:
        context: Telegram context
        use_admin_pattern: If True, use 'approve_date_' prefix; otherwise use 'sub_date_'
    """
    current_month = context.user_data.get('calendar_month', datetime.now())
    keyboard = []
    date_prefix = "approve_date_" if use_admin_pattern else "sub_date_"
    
    # Navigation row
    prev_month = (current_month.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (current_month.replace(day=28) + timedelta(days=4)).replace(day=1)
    
    nav_row = [
        InlineKeyboardButton("◀️", callback_data=f"cal_prev_{prev_month.strftime('%Y%m')}"),
        InlineKeyboardButton(f"{current_month.strftime('%B %Y')}", callback_data="cal_noop"),
        InlineKeyboardButton("▶️", callback_data=f"cal_next_{next_month.strftime('%Y%m')}")
    ]
    keyboard.append(nav_row)
    
    # Days header
    days_header = [InlineKeyboardButton(day, callback_data="cal_noop") for day in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]]
    keyboard.append(days_header)
    
    # Days of month
    first_day = current_month.replace(day=1)
    last_day = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    
    # Calculate starting position
    start_weekday = first_day.weekday()
    
    week = []
    # Empty cells for days before month starts
    for _ in range(start_weekday):
        week.append(InlineKeyboardButton(" ", callback_data="cal_noop"))
    
    # Days of the month
    for day in range(1, last_day.day + 1):
        date = current_month.replace(day=day)
        if date.date() < datetime.now().date():
            # Disable past dates
            week.append(InlineKeyboardButton(f"✗{day}", callback_data="cal_noop"))
        else:
            week.append(InlineKeyboardButton(
                str(day),
                callback_data=f"{date_prefix}{date.strftime('%Y%m%d')}"
            ))
        
        if len(week) == 7:
            keyboard.append(week)
            week = []
    
    # Fill remaining cells
    if week:
        while len(week) < 7:
            week.append(InlineKeyboardButton(" ", callback_data="cal_noop"))
        keyboard.append(week)
    
    # Quick select buttons
    today = datetime.now()
    quick_select = [
        InlineKeyboardButton("+30 days", callback_data=f"{date_prefix}{(today + timedelta(days=30)).strftime('%Y%m%d')}"),
        InlineKeyboardButton("+60 days", callback_data=f"{date_prefix}{(today + timedelta(days=60)).strftime('%Y%m%d')}"),
        InlineKeyboardButton("+90 days", callback_data=f"{date_prefix}{(today + timedelta(days=90)).strftime('%Y%m%d')}")
    ]
    keyboard.append(quick_select)
    
    return InlineKeyboardMarkup(keyboard)


async def handle_custom_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom amount input"""
    try:
        amount = int(update.message.text)
        context.user_data['custom_amount'] = amount
        context.user_data['calendar_month'] = datetime.now()
        
        await update.message.reply_text(
            f"💰 Amount: Rs. {amount:,}\n\n"
            f"Now select the subscription end date:"
        )
        
        calendar_markup = await generate_calendar_keyboard(context)
        await update.message.reply_text(
            "📅 Select subscription end date:",
            reply_markup=calendar_markup
        )
        
        return ADMIN_SELECT_DATE
    
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a number.")
        return ADMIN_ENTER_AMOUNT


async def callback_calendar_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle calendar navigation"""
    query = update.callback_query
    logger.info(f"[CALENDAR_NAV] callback_calendar_nav triggered by user {query.from_user.id}, callback_data={query.data}")
    
    action = query.data.split("_")[1]  # 'prev' or 'next'
    date_str = query.data.split("_")[2]  # 'YYYYMM'
    
    try:
        nav_month = datetime.strptime(date_str, "%Y%m")
        context.user_data['calendar_month'] = nav_month
        
        await query.answer()
        # Check if we're in admin approval flow
        use_admin_pattern = context.user_data.get('approving_request_id') is not None
        logger.info(f"[CALENDAR_NAV] Regenerating calendar with use_admin_pattern={use_admin_pattern}")
        
        calendar_markup = await generate_calendar_keyboard(context, use_admin_pattern=use_admin_pattern)
        await query.edit_message_reply_markup(reply_markup=calendar_markup)
        
    except Exception as e:
        logger.error(f"Error in calendar navigation: {e}")
        await query.answer("Error updating calendar", show_alert=True)


async def callback_select_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Select end date and approve"""
    query = update.callback_query
    sub_id = context.user_data.get('pending_sub_id')
    amount = context.user_data.get('custom_amount')
    
    try:
        date_str = query.data.split("_")[-1]
        end_date = datetime.strptime(date_str, "%Y%m%d")
        
        pending = get_pending_subscription_requests()
        sub = next((s for s in pending if s['id'] == sub_id), None)
        
        if not sub:
            await query.answer("Subscription not found", show_alert=True)
            return ConversationHandler.END
        
        await query.answer()
        
        # Try to approve subscription
        payment_lines = [{'method': 'cash', 'amount': amount, 'reference': None}]

        if approve_subscription(sub_id, amount, end_date, payment_lines=payment_lines, admin_user_id=query.from_user.id):
            # Send payment receipt to user
            receipt_message = (
                "✅ *Payment Received & Approved!*\n\n"
                "📋 *Payment Receipt*\n"
                f"💰 Amount: Rs. {amount:,}\n"
                f"📅 Valid Until: {end_date.strftime('%d-%m-%Y')}\n"
                f"✓ Plan: {SUBSCRIPTION_PLANS.get(sub.get('plan_id', 1), {}).get('name', 'Standard')}\n\n"
                f"🎉 You now have full access to all gym features!\n\n"
                "Thank you for your subscription! 🙏"
            )
            
            try:
                await context.bot.send_message(
                    chat_id=sub['user_id'],
                    text=receipt_message,
                    parse_mode="Markdown"
                )
                logger.info(f"Payment receipt sent to user {sub['user_id']}")
            except Exception as e:
                logger.error(f"Error sending receipt to user: {e}")
            
            # Confirm to admin
            await query.edit_message_text(
                f"✅ *Subscription Approved Successfully*\n\n"
                f"👤 User: {sub['full_name']}\n"
                f"💰 Amount: Rs. {amount:,}\n"
                f"📅 End Date: {end_date.strftime('%d-%m-%Y')}\n\n"
                f"✓ Payment receipt sent to user",
                parse_mode="Markdown"
            )
        else:
            # Provide detailed error message
            error_msg = (
                "❌ *Error Approving Subscription*\n\n"
                "Failed to process the subscription approval. Please try again.\n\n"
                "If the problem persists:\n"
                "• Check database connection\n"
                "• Verify user exists\n"
                "• Try canceling and restarting"
            )
            await query.edit_message_text(error_msg, parse_mode="Markdown")
            logger.error(f"Failed to approve subscription {sub_id} for user {sub['user_id']}")
        
        return ConversationHandler.END
    
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        await query.answer("Invalid date selected", show_alert=True)
        return ADMIN_SELECT_DATE
    except Exception as e:
        logger.error(f"Error in callback_select_end_date: {e}")
        await query.edit_message_text(
            "❌ An unexpected error occurred. Please try again.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END


async def callback_reject_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Reject subscription"""
    query = update.callback_query
    sub_id = int(query.data.split("_")[-1])
    
    pending = get_pending_subscription_requests()
    sub = next((s for s in pending if s['id'] == sub_id), None)
    
    if not sub:
        await query.answer("Subscription not found", show_alert=True)
        return
    
    await query.answer()
    
    if reject_subscription(sub_id, "Admin rejected"):
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=sub['user_id'],
                text="❌ *Subscription Request Rejected*\n\n"
                     "Your subscription request has been rejected by the admin.\n"
                     "Please contact the fitness club for more information.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
        
        await query.edit_message_text(
            f"❌ *Subscription Rejected*\n\n"
            f"User: {sub['full_name']}\n"
            f"✓ User notified",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text("❌ Error rejecting subscription")


async def callback_upi_upload_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to upload UPI payment screenshot"""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "📸 *Upload Payment Screenshot*\n\n"
        "Please share the screenshot of your UPI payment confirmation.\n"
        "This helps us verify your payment quickly.",
        parse_mode="Markdown"
    )
    return ENTER_UPI_VERIFICATION


async def handle_upi_screenshot_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle UPI payment screenshot upload"""
    user_id = update.effective_user.id
    request_id = context.user_data.get('subscription_request_id')
    plan = context.user_data.get('selected_plan')
    
    # Check if user sent a photo
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        context.user_data['screenshot_file_id'] = file_id
        
        keyboard = [
            [InlineKeyboardButton("✅ Submit Payment", callback_data="upi_submit_with_screenshot")],
            [InlineKeyboardButton("⏭️ Skip Screenshot", callback_data="upi_skip_screenshot")],
            [InlineKeyboardButton("❌ Cancel", callback_data="sub_cancel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "✅ Screenshot received!\n\n"
            "Click 'Submit Payment' to confirm, or 'Skip Screenshot' to submit without it.",
            reply_markup=reply_markup
        )
        
        logger.info(f"UPI screenshot uploaded by user {user_id}, Request ID: {request_id}")
        return ENTER_UPI_VERIFICATION
    else:
        await update.message.reply_text(
            "❌ Please send a photo/screenshot of the UPI payment.\n"
            "Or click 'Skip Screenshot' to continue without it."
        )
        return ENTER_UPI_VERIFICATION


async def callback_split_upi_upload_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to upload split payment UPI screenshot"""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "📸 *Upload UPI Payment Screenshot*\n\n"
        "Please share the screenshot of your UPI payment confirmation.\n"
        "This helps us verify your payment quickly.",
        parse_mode="Markdown"
    )
    return ENTER_UPI_VERIFICATION


async def callback_split_upi_skip_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip screenshot for split UPI payment"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    request_id = context.user_data.get('subscription_request_id')
    plan = context.user_data.get('selected_plan')
    transaction_ref = context.user_data.get('transaction_ref')
    split_upi_amount = context.user_data.get('split_upi_amount')
    split_cash_amount = context.user_data.get('split_cash_amount')
    
    if not request_id or not plan or not split_upi_amount or not split_cash_amount:
        await query.message.reply_text("❌ Payment data not found")
        return ConversationHandler.END
    
    from src.database.subscription_operations import create_pending_payment

    # Persist pending UPI evidence (defer ledger writes until admin confirms)
    pending = create_pending_payment(user_id, request_id, split_upi_amount, 'upi', transaction_ref, None)
    if not pending:
        await query.message.reply_text("❌ Error saving payment evidence. Please contact admin.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("💬 WhatsApp Support", url="https://wa.me/9158243377")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ *Split Payment Submitted*\n\n"
        f"Plan: {plan['name']}\n"
        f"*Total Amount: Rs. {(split_upi_amount + split_cash_amount):,.0f}*\n\n"
        f"*Payment Breakdown:*\n"
        f"• UPI: Rs. {split_upi_amount:,.0f}\n"
        f"• Cash: Rs. {split_cash_amount:,.0f}\n\n"
        f"✅ UPI portion submitted for verification\n"
        f"⏳ Admin will contact you for cash collection\n\n"
        f"Thank you for your purchase! 🎉",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    logger.info(f"Split payment UPI submitted (no screenshot): User {user_id}, Request {request_id}")
    return ConversationHandler.END


async def callback_upi_skip_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip screenshot and submit UPI payment"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    request_id = context.user_data.get('subscription_request_id')
    plan = context.user_data.get('selected_plan')
    transaction_ref = context.user_data.get('transaction_ref')
    
    # Check if this is a split payment
    is_split = context.user_data.get('subscription_request_split', False)
    split_upi_amount = context.user_data.get('split_upi_amount')
    split_cash_amount = context.user_data.get('split_cash_amount')
    
    if not request_id or not plan:
        await query.message.reply_text("❌ Payment data not found")
        return ConversationHandler.END
    
    # For split payments, create AR receivable with both lines
    if is_split and split_upi_amount and split_cash_amount:
        from src.database.subscription_operations import create_pending_payment

        # Persist pending UPI evidence (defer ledger writes until admin confirms)
        pending = create_pending_payment(user_id, request_id, split_upi_amount, 'upi', transaction_ref, None)
        if not pending:
            await query.message.reply_text("❌ Error saving payment evidence. Please contact admin.")
            return ConversationHandler.END
        
        keyboard = [
            [InlineKeyboardButton("💬 WhatsApp Support", url="https://wa.me/9158243377")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ *Split Payment Submitted*\n\n"
            f"Plan: {plan['name']}\n"
            f"*Total Amount: Rs. {(split_upi_amount + split_cash_amount):,.0f}*\n\n"
            f"*Payment Breakdown:*\n"
            f"• 📱 UPI: Rs. {split_upi_amount:,.0f} (Reference: {transaction_ref})\n"
            f"• 💵 Cash: Rs. {split_cash_amount:,.0f} (Pending Confirmation)\n\n"
            f"Your UPI payment has been submitted for verification.\n"
            f"The admin will confirm cash collection separately.\n"
            f"Your subscription will be activated once both payments are confirmed. 🎉\n\n"
            f"If you have any questions, reach out on WhatsApp.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
        # Send split payment notification to admins
        try:
            from src.handlers.admin_handlers import get_admin_ids
            from datetime import datetime
            
            admin_ids = get_admin_ids()
            logger.info(f"Split payment (no screenshot): Found {len(admin_ids)} admins to notify")
            
            admin_caption = (
                f"*🔀 Split Payment Request - Admin Review*\n\n"
                f"User: {query.from_user.full_name} (ID: {user_id})\n"
                f"Plan: {plan['name']}\n"
                f"*Total: Rs. {(split_upi_amount + split_cash_amount):,.0f}*\n\n"
                f"*Payment Breakdown:*\n"
                f"• 📱 UPI: Rs. {split_upi_amount:,.0f}\n"
                f"  Reference: {transaction_ref}\n"
                f"• 💵 Cash: Rs. {split_cash_amount:,.0f}\n"
                f"  Status: Awaiting confirmation\n\n"
                f"Request ID: {request_id}\n"
                f"Submitted: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n"
                f"Screenshot: ❌ Not attached\n\n"
                f"*Action:* Verify UPI payment and confirm/request cash payment."
            )
            
            admin_keyboard = [
                [InlineKeyboardButton("✅ Approve UPI", callback_data=f"admin_approve_split_upi_{request_id}")],
                [InlineKeyboardButton("✅ Confirm Cash", callback_data=f"admin_confirm_split_cash_{request_id}")],
                [InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_split_{request_id}")],
            ]
            admin_reply_markup = InlineKeyboardMarkup(admin_keyboard)
            
            user_data = get_user(user_id)
            profile_pic_url = user_data.get('profile_pic_url') if user_data else None
            
            for admin_id in admin_ids:
                try:
                    await context.bot.send_message(chat_id=admin_id, text=admin_caption, reply_markup=admin_reply_markup, parse_mode="Markdown")
                    
                    if profile_pic_url:
                        try:
                            await context.bot.send_photo(chat_id=admin_id, photo=profile_pic_url, caption="📸 User Profile Picture")
                        except Exception as e:
                            logger.debug(f"Could not send profile picture: {e}")
                    
                    logger.info(f"✅ Split payment notification sent to admin {admin_id}")
                except Exception as e:
                    logger.error(f"Failed to send split payment notification to admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Error in split payment admin notification: {e}", exc_info=True)
        
        logger.info(f"Split payment submitted (no screenshot): User {user_id}, UPI {split_upi_amount}, Cash {split_cash_amount}")
        return ConversationHandler.END
    
    # Regular UPI payment (non-split)
    # Persist pending UPI evidence (defer ledger writes until admin confirms)
    from src.database.subscription_operations import create_pending_payment
    payment = create_pending_payment(user_id, request_id, plan['amount'], 'upi', transaction_ref, None)

    if not payment:
        await query.message.reply_text("❌ Error saving payment evidence. Please contact admin.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("💬 WhatsApp Support", url="https://wa.me/9158243377")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ *UPI Payment Submitted*\n\n"
        f"Plan: {plan['name']}\n"
        f"Amount: Rs. {plan['amount']:,}\n"
        f"Payment Method: 📱 UPI\n"
        f"Reference: {transaction_ref}\n\n"
        f"Your payment has been submitted for verification.\n"
        f"Your subscription will be activated shortly. 🎉\n\n"
        f"If you have any questions, reach out on WhatsApp.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    # Send UPI payment notification to admins
    try:
        from src.handlers.admin_handlers import get_admin_ids
        from datetime import datetime
        
        admin_ids = get_admin_ids()
        logger.info(f"UPI payment (no screenshot): Found {len(admin_ids)} admins to notify")
        
        admin_caption = (
            f"*📱 UPI Payment Request - Admin Review*\n\n"
            f"User: {query.from_user.full_name} (ID: {user_id})\n"
            f"Plan: {plan['name']}\n"
            f"Amount: Rs. {plan['amount']:,}\n"
            f"Payment Method: 📱 UPI\n"
            f"Reference: {transaction_ref}\n\n"
            f"Request ID: {request_id}\n"
            f"Submitted: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n"
            f"Screenshot: ❌ Not attached\n\n"
            f"*Action:* Please verify UPI payment and approve/reject below."
        )
        
        admin_keyboard = [[InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_upi_{request_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_upi_{request_id}")]]
        admin_reply_markup = InlineKeyboardMarkup(admin_keyboard)
        
        # Get user profile picture
        user_data = get_user(user_id)
        profile_pic_url = user_data.get('profile_pic_url') if user_data else None
        
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(chat_id=admin_id, text=admin_caption, reply_markup=admin_reply_markup, parse_mode="Markdown")
                
                # Send user profile picture if available
                if profile_pic_url:
                    try:
                        await context.bot.send_photo(chat_id=admin_id, photo=profile_pic_url, caption="📸 User Profile Picture")
                    except Exception as profile_error:
                        logger.debug(f"Could not send profile picture to admin {admin_id}: {profile_error}")
                
                logger.info(f"✅ UPI payment notification (no screenshot) sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"❌ Failed to send UPI notification to admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Error in UPI payment admin notification: {e}", exc_info=True)
    
    logger.info(f"UPI payment submitted (no screenshot) for user {user_id}, amount {plan['amount']}")
    return ConversationHandler.END


async def callback_upi_submit_with_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Submit UPI payment with screenshot"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    request_id = context.user_data.get('subscription_request_id')
    plan = context.user_data.get('selected_plan')
    transaction_ref = context.user_data.get('transaction_ref')
    screenshot_file_id = context.user_data.get('screenshot_file_id')
    
    if not request_id or not plan:
        await query.message.reply_text("❌ Payment data not found")
        return ConversationHandler.END
    
    # Persist pending UPI evidence (with screenshot) — defer ledger writes until admin confirms
    from src.database.subscription_operations import create_pending_payment
    payment = create_pending_payment(user_id, request_id, plan['amount'], 'upi', transaction_ref, screenshot_file_id)

    if not payment:
        await query.message.reply_text("❌ Error saving payment evidence. Please contact admin.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("💬 WhatsApp Support", url="https://wa.me/9158243377")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ *UPI Payment Verified*\n\n"
        f"Plan: {plan['name']}\n"
        f"Amount: Rs. {plan['amount']:,}\n"
        f"Payment Method: 📱 UPI\n"
        f"Reference: {transaction_ref}\n"
        f"Screenshot: ✅ Attached\n\n"
        f"Your payment has been verified.\n"
        f"Your subscription will be activated shortly. 🎉\n\n"
        f"Thank you for joining our fitness club!",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    # Send UPI payment notification to admins
    try:
        from src.handlers.admin_handlers import get_admin_ids
        from datetime import datetime
        
        admin_ids = get_admin_ids()
        logger.info(f"UPI payment (with screenshot): Found {len(admin_ids)} admins to notify")
        
        admin_caption = (
            f"*📱 UPI Payment Request - Admin Review*\n\n"
            f"User: {query.from_user.full_name} (ID: {user_id})\n"
            f"Plan: {plan['name']}\n"
            f"Amount: Rs. {plan['amount']:,}\n"
            f"Payment Method: 📱 UPI\n"
            f"Reference: {transaction_ref}\n\n"
            f"Request ID: {request_id}\n"
            f"Submitted: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n"
            f"Screenshot: ✅ Attached\n\n"
            f"*Action:* Please verify UPI payment and approve/reject below."
        )
        
        admin_keyboard = [[InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_upi_{request_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_upi_{request_id}")]]
        admin_reply_markup = InlineKeyboardMarkup(admin_keyboard)
        
        # Get user profile picture
        user_data = get_user(user_id)
        profile_pic_url = user_data.get('profile_pic_url') if user_data else None
        
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(chat_id=admin_id, text=admin_caption, reply_markup=admin_reply_markup, parse_mode="Markdown")
                try:
                    await context.bot.send_photo(chat_id=admin_id, photo=screenshot_file_id, caption="UPI Payment Screenshot")
                except Exception as photo_error:
                    logger.error(f"Could not send payment screenshot to admin {admin_id}: {photo_error}")
                    # Fallback: send a text note so admin knows screenshot is missing
                    await context.bot.send_message(chat_id=admin_id, text="⚠️ Unable to attach payment screenshot. Please request the user to resend.")
                
                # Send user profile picture if available
                if profile_pic_url:
                    try:
                        await context.bot.send_photo(chat_id=admin_id, photo=profile_pic_url, caption="📸 User Profile Picture")
                    except Exception as profile_error:
                        logger.error(f"Could not send profile picture to admin {admin_id}: {profile_error}")
                
                logger.info(f"✅ UPI payment notification (with screenshot) sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"❌ Failed to send UPI notification to admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Error in UPI payment admin notification: {e}", exc_info=True)
    
    logger.info(f"UPI payment submitted with screenshot for user {user_id}, amount {plan['amount']}")
    return ConversationHandler.END


async def callback_admin_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Contact admin button for cash payment"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💬 WhatsApp", url="https://wa.me/9158243377")],
        [InlineKeyboardButton("📞 Call", url="tel:+919158243377")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📞 *Contact Admin*\n\n"
        "Reach out to admin via:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
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

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from src.database.activity_operations import get_leaderboard, get_user_points, get_today_log
from src.database.attendance_operations import get_user_attendance_today
from src.database.shake_operations import get_shake_flavors, request_shake
from src.database.user_operations import get_user
from src.utils.role_notifications import get_moderator_chat_ids
from src.utils.auth import is_admin_id, is_staff, check_user_approved
from src.utils.role_notifications import get_moderator_chat_ids
from src.database.user_operations import get_user
from src.database.shake_credits_operations import (
    approve_purchase, reject_purchase, get_pending_purchase_requests, get_user_credits
)

logger = logging.getLogger(__name__)


# Security: Role-based access control for callbacks
async def verify_admin_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Verify user has admin access before executing admin callback.
    Returns True if authorized, False otherwise (and sends error message).
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin_id(user_id):
        logger.warning(f"[SECURITY] Unauthorized admin callback attempt by user {user_id}")
        await query.answer("❌ Admin access only.", show_alert=True)
        return False
    
    return True


async def verify_staff_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Verify user has staff access before executing staff callback.
    Returns True if authorized, False otherwise (and sends error message).
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_staff(user_id):
        logger.warning(f"[SECURITY] Unauthorized staff callback attempt by user {user_id}")
        await query.answer("❌ Staff access only.", show_alert=True)
        return False
    
    return True


async def verify_fee_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Verify user has paid membership fee before allowing activity.
    Also checks if user is approved.
    Returns True if approved and paid, False otherwise (and sends error message).
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # Check approval first
    if not check_user_approved(user_id):
        logger.info(f"[APPROVAL] User {user_id} attempted activity without approval")
        await query.answer(
            "⏳ Registration pending approval. Contact admin.",
            show_alert=True
        )
        return False
    
    return True


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu with inline buttons"""
    keyboard = [
        [InlineKeyboardButton("📊 My Stats", callback_data="stats"),
         InlineKeyboardButton("🏋️ Check In", callback_data="checkin")],
        [InlineKeyboardButton("💪 Log Activity", callback_data="log_activity"),
         InlineKeyboardButton("🥛 Order Shake", callback_data="shake")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
         InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📱 *Fitness Club Menu*\n\nChoose an option:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    points = get_user_points(user_id)
    today_log = get_today_log(user_id)
    
    stats_text = f"""
📊 *Your Stats Today*

💰 Total Points: `{points}`

🔥 Today's Activity:
• Weight: {'✅' if today_log and today_log['weight'] else '❌'}
• Water: {today_log['water_cups'] if today_log else 0} cups
• Meals: {today_log['meals_logged'] if today_log else 0}/4
• Habits: {'✅' if today_log and today_log['habits_completed'] else '❌'}
"""
    
    keyboard = [[InlineKeyboardButton("📱 Back to Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=stats_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Checkin attendance"""
    query = update.callback_query
    await query.answer()
    
    # Verify fee is paid
    if not await verify_fee_paid(update, context):
        return
    
    user_id = update.effective_user.id
    existing = get_user_attendance_today(user_id)
    
    if existing and existing['status'] == 'pending':
        message = "⏳ You already have a pending check-in request today."
    elif existing and existing['status'] == 'approved':
        message = "✅ Already checked in today!"
    else:
        # Show checkin options
        keyboard = [
            [InlineKeyboardButton("📸 Upload Photo", callback_data="checkin_photo"),
             InlineKeyboardButton("📝 Text Checkin", callback_data="checkin_text")],
            [InlineKeyboardButton("📱 Back to Menu", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="🏋️ *Check In*\n\nHow would you like to check in?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return
    
    keyboard = [[InlineKeyboardButton("📱 Back to Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_shake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show shake flavor selection"""
    query = update.callback_query
    await query.answer()
    
    # Verify fee is paid
    if not await verify_fee_paid(update, context):
        return
    
    flavors = get_shake_flavors()
    
    keyboard = []
    for flavor in flavors:
        keyboard.append([
            InlineKeyboardButton(
                f"🥛 {flavor['flavor_name']}", 
                callback_data=f"select_flavor_{flavor['flavor_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("📱 Back to Menu", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="🥛 *Select Shake Flavor*\n\nChoose your favorite:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_select_flavor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle shake flavor selection"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    flavor_id = int(query.data.split("_")[-1])
    
    result = request_shake(user_id, flavor_id)
    
    if result:
        await query.answer("✅ Shake request submitted!", show_alert=True)
        
        keyboard = [[InlineKeyboardButton("📱 Back to Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="✅ *Shake Ordered*\n\nYour shake has been ordered and will be ready soon!",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        # Notify moderators (super admin, admins, staff)
        user = get_user(user_id)
        flavor_name = None
        for flavor in get_shake_flavors() or []:
            if flavor.get('flavor_id') == flavor_id:
                flavor_name = flavor.get('flavor_name')
                break
        flavor_display = flavor_name or "Unknown"
        for chat_id in get_moderator_chat_ids(include_staff=True):
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "🔔 *New Shake Request*\n\n"
                        f"User: {user.get('full_name') if user else user_id}\n"
                        f"ID: `{user_id}`\n"
                        f"Flavor: {flavor_display}\n\n"
                        "Use Pending Shakes to approve."
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🥤 Pending Shakes", callback_data="cmd_pending_shakes")]
                    ]),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Failed to notify moderator {chat_id} for shake: {e}")
    else:
        await query.answer("❌ Failed to order shake. Try again.", show_alert=True)

async def callback_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top members leaderboard"""
    query = update.callback_query
    await query.answer()
    
    leaderboard = get_leaderboard(10)
    
    leaderboard_text = "🏆 *Top 10 Members*\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for i, member in enumerate(leaderboard, 1):
        medal = medals[i-1] if i <= 3 else f"{i}."
        name = member['full_name'] or f"User {member['user_id']}"
        leaderboard_text += f"{medal} {name}: {member['total_points']} pts\n"
    
    keyboard = [[InlineKeyboardButton("📱 Back to Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=leaderboard_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_log_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show activity logging options"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("⚖️ Log Weight", callback_data="log_weight")],
        [InlineKeyboardButton("💧 Log Water", callback_data="log_water")],
        [InlineKeyboardButton("🍽️ Log Meal", callback_data="log_meal")],
        [InlineKeyboardButton("💪 Complete Habits", callback_data="log_habits")],
        [InlineKeyboardButton("📱 Back to Menu", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="📋 *Log Activity*\n\nSelect what you'd like to log:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📱 Phone", callback_data="settings_phone")],
        [InlineKeyboardButton("💰 Fee Status", callback_data="settings_fee")],
        [InlineKeyboardButton("🔔 Notifications", callback_data="settings_notif")],
        [InlineKeyboardButton("📱 Back to Menu", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="⚙️ *Settings*\n\nChoose an option:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main menu"""
    await show_main_menu(update, context)

# Callback handler router
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route callback queries to appropriate handlers"""
    from src.handlers.user_handlers import cmd_qrcode, cmd_points_chart, cmd_studio_rules
    from src.handlers.misc_handlers import cmd_whoami, cmd_get_telegram_id
    from src.handlers.activity_handlers import cmd_weight, cmd_water, cmd_meal, cmd_habits, cmd_checkin, get_habits_confirm
    from src.handlers.admin_handlers import (
        cmd_pending_attendance, cmd_pending_shakes, cmd_add_staff, cmd_remove_staff, 
        cmd_list_staff, cmd_add_admin, cmd_remove_admin, cmd_list_admins,
        cmd_list_users, cmd_delete_user, cmd_ban_user, cmd_unban_user
    )
    from src.handlers.payment_handlers import cmd_challenges
    from src.handlers.challenge_handlers import cmd_my_challenges
    from src.handlers.analytics_handlers import cmd_admin_dashboard
    from src.handlers.notification_handlers import cmd_notifications
    from src.handlers.broadcast_handlers import cmd_broadcast, cmd_followup_settings
    from src.handlers.payment_request_handlers import cmd_pending_requests
    from src.handlers.shake_credit_handlers import (
        cmd_buy_shake_credits, cmd_check_shake_credits, cmd_shake_report,
        cmd_admin_pending_purchases, process_shake_order,
        callback_confirm_buy_credits, callback_select_shake_payment,
        callback_approve_shake_purchase, callback_reject_shake_purchase
    )
    from src.handlers.shake_order_handlers import (
        cmd_order_shake_enhanced, process_shake_flavor_selection, confirm_shake_order,
        admin_approve_shake, admin_complete_shake
    )
    from src.handlers.commerce_hub_handlers import (
        cmd_manage_subscriptions, cmd_manage_store, cmd_manage_pt_plans, cmd_manage_events,
        handle_commerce_callbacks, cmd_user_store
    )
    from src.handlers.role_keyboard_handlers import show_role_menu
    from src.handlers.role_keyboard_handlers import show_manage_staff_submenu, show_manage_admins_submenu
    
    query = update.callback_query
    logger.info(f"[CALLBACK] handle_callback_query received: {query.data} from user {query.from_user.id} - Chat ID: {query.message.chat_id if query.message else 'NO MESSAGE'}")
    
    # Try to answer callback, but handle old/expired queries gracefully
    try:
        await query.answer()
    except Exception as e:
        logger.debug(f"Could not answer callback query (likely expired): {e}")
        # Continue processing even if answer fails - query might be too old
    
    # Habit callbacks (habit toggling and submission)
    if query.data.startswith("habit_toggle_") or query.data == "habit_submit":
        await get_habits_confirm(update, context)
    # Menu button callbacks (cmd_* prefix)
    elif query.data == "cmd_notifications":
        await cmd_notifications(update, context)
    elif query.data == "cmd_challenges":
        await cmd_challenges(update, context)
    elif query.data == "cmd_my_challenges":
        await cmd_my_challenges(update, context)
    elif query.data == "cmd_weight":
        await cmd_weight(update, context)
    elif query.data == "cmd_water":
        await cmd_water(update, context)
    elif query.data == "cmd_meal":
        await cmd_meal(update, context)
    elif query.data == "cmd_habits":
        await cmd_habits(update, context)
    elif query.data == "cmd_checkin":
        await cmd_checkin(update, context)
    elif query.data == "cmd_qrcode":
        await cmd_qrcode(update, context)
    elif query.data == "cmd_points_chart":
        await cmd_points_chart(update, context)
    elif query.data == "cmd_studio_rules":
        await cmd_studio_rules(update, context)
    elif query.data == "cmd_user_store":
        # Legacy static store, keep for backward compatibility (if needed)
        await cmd_user_store(update, context)
    elif query.data == "cmd_store":
        # New cart-based store
        from src.handlers.store_user_handlers import cmd_store
        await cmd_store(update, context)
    elif query.data == "cmd_check_shake_credits":
        await cmd_check_shake_credits(update, context)
    elif query.data == "cmd_order_shake":
        await cmd_order_shake_enhanced(update, context)
    elif query.data.startswith("order_flavor_"):
        await process_shake_flavor_selection(update, context)
    elif query.data.startswith("confirm_shake_"):
        await confirm_shake_order(update, context)
    elif query.data.startswith("approve_shake_"):
        await admin_approve_shake(update, context)
    elif query.data.startswith("complete_shake_"):
        await admin_complete_shake(update, context)
    elif query.data == "cmd_buy_shake_credits":
        await cmd_buy_shake_credits(update, context)
    elif query.data == "confirm_buy_25":
        await callback_confirm_buy_credits(update, context)
    elif query.data.startswith("shake_pay_"):
        await callback_select_shake_payment(update, context)
    elif query.data.startswith("approve_shake_purchase_"):
        await callback_approve_shake_purchase(update, context)
    elif query.data.startswith("reject_shake_purchase_"):
        await callback_reject_shake_purchase(update, context)
    elif query.data == "cmd_shake_report":
        await cmd_shake_report(update, context)
    elif query.data == "cmd_pending_shake_purchases":
        await cmd_admin_pending_purchases(update, context)
    elif query.data == "cmd_get_telegram_id":
        await cmd_get_telegram_id(update, context)
    elif query.data == "cmd_whoami":
        await cmd_whoami(update, context)
    elif query.data == "cmd_pending_attendance":
        await cmd_pending_attendance(update, context)
    elif query.data == "cmd_pending_shakes":
        await cmd_pending_shakes(update, context)
    elif query.data == "cmd_admin_dashboard":
        await cmd_admin_dashboard(update, context)
    elif query.data == "admin_manage_staff":
        await show_manage_staff_submenu(update, context)
    elif query.data == "admin_manage_admins":
        await show_manage_admins_submenu(update, context)
    elif query.data == "cmd_add_staff":
        await cmd_add_staff(update, context)
    elif query.data == "cmd_remove_staff":
        await cmd_remove_staff(update, context)
    elif query.data == "cmd_list_staff":
        await cmd_list_staff(update, context)
    elif query.data == "cmd_add_admin":
        await cmd_add_admin(update, context)
    elif query.data == "cmd_remove_admin":
        await cmd_remove_admin(update, context)
    elif query.data == "cmd_list_admins":
        await cmd_list_admins(update, context)
    elif query.data == "cmd_list_users":
        await cmd_list_users(update, context)
    elif query.data == "cmd_admin_back":
        # Back to admin main menu
        await show_role_menu(update, context)
    elif query.data == "admin_delete_user":
        await cmd_delete_user(update, context)
    elif query.data == "admin_ban_user":
        await cmd_ban_user(update, context)
    elif query.data == "admin_unban_user":
        await cmd_unban_user(update, context)
    elif query.data.startswith("confirm_delete_"):
        user_id_to_delete = int(query.data.split("_")[2])
        from src.database.user_operations import delete_user
        result = delete_user(user_id_to_delete)
        if result:
            await query.edit_message_text(f"✅ User {result['full_name']} (ID: {user_id_to_delete}) deleted successfully.")
        else:
            await query.edit_message_text("❌ Failed to delete user.")
    elif query.data == "cancel_delete":
        await query.edit_message_text("❌ Deletion cancelled.")
    elif query.data == "cmd_broadcast":
        await cmd_broadcast(update, context)
    elif query.data == "cmd_followup_settings":
        await cmd_followup_settings(update, context)
    elif query.data.startswith("confirm_buy_"):
        # Confirm shake credit purchase
        credits = int(query.data.split("_")[-1])
        from src.handlers.shake_credit_handlers import cmd_check_shake_credits as confirm_purchase_handler
        from src.database.shake_credits_operations import create_purchase_request
        user_id = query.from_user.id
        if not check_user_approved(user_id):
            await query.answer("Registration pending approval. Contact admin.", show_alert=True)
            return
        purchase = create_purchase_request(user_id, credits)
        if purchase:
            await query.answer("✅ Purchase request created! Awaiting admin approval.", show_alert=True)
            await query.message.reply_text(
                f"✅ *Purchase Request Created*\n\n"
                f"🥤 Credits: {credits}\n"
                f"💵 Amount: Rs {purchase['amount']}\n"
                f"⏳ Status: Pending Admin Approval\n\n"
                f"Our admin will verify your payment and transfer credits soon.",
                parse_mode='Markdown'
            )

            # Notify all admins immediately with approve/reject buttons
            admin_ids = get_moderator_chat_ids(include_staff=False)
            user_info = get_user(user_id) or {}
            notif_text = (
                f"💳 *Shake Credit Purchase Request*\n\n"
                f"👤 User: {user_info.get('full_name', 'Unknown')}\n"
                f"📱 @{user_info.get('telegram_username') or 'unknown'}\n"
                f"🥤 Credits: {credits}\n"
                f"💵 Amount: Rs {purchase['amount']}\n"
                f"📅 Requested: {purchase['created_at'].strftime('%d-%m-%Y %H:%M')}\n"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"approve_purchase_{purchase['purchase_id']}")],
                [InlineKeyboardButton("❌ Reject", callback_data=f"reject_purchase_{purchase['purchase_id']}")],
            ])
            for admin_id in admin_ids:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=notif_text,
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id} about purchase {purchase['purchase_id']}: {e}")
        else:
            await query.answer("❌ Failed to create purchase request", show_alert=True)
    elif query.data.startswith("approve_purchase_"):
        purchase_id = int(query.data.split("_")[-1])
        if not is_admin_id(query.from_user.id):
            await query.answer("❌ Admin access only.", show_alert=True)
            return
        result = approve_purchase(purchase_id, query.from_user.id)
        if result and result.get('already_processed'):
            await query.answer(f"Already {result.get('status', 'processed')}", show_alert=True)
            return

        if result:
            await query.answer("✅ Purchase approved!", show_alert=False)
            await query.message.reply_text(
                f"✅ *Purchase Approved!*\n\n"
                f"👤 User: {result['full_name']}\n"
                f"🥤 Credits: {result['credits_requested']}\n"
                f"✅ Status: Completed\n\n"
                f"{result['credits_requested']} shake credits have been transferred to the user."
            )
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=result['user_id'],
                    text=f"✅ *Your Shake Credit Purchase is Approved!*\n\n"
                         f"🥤 {result['credits_requested']} credits added to your account\n"
                         f"✅ Available to use now!\n\n"
                         f"Tap 'Order Shake' from menu to order your shake.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify user {result['user_id']}: {e}")
            # Show next purchase request
            purchases = get_pending_purchase_requests()
            if purchases:
                purchase = purchases[0]
                purchase_text = (
                    f"💳 *Next Shake Credit Purchase Request*\n\n"
                    f"👤 User: {purchase['full_name']}\n"
                    f"🥤 Credits: {purchase['credits_requested']}\n"
                    f"💵 Amount: Rs {purchase['amount']}\n"
                )
                keyboard = [
                    [InlineKeyboardButton("✅ Approve", callback_data=f"approve_purchase_{purchase['purchase_id']}"),
                     InlineKeyboardButton("❌ Reject", callback_data=f"reject_purchase_{purchase['purchase_id']}")],
                ]
                await query.message.reply_text(
                    purchase_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
        else:
            await query.answer("❌ Failed to approve purchase", show_alert=True)
    elif query.data.startswith("reject_purchase_"):
        purchase_id = int(query.data.split("_")[-1])
        if not is_admin_id(query.from_user.id):
            await query.answer("❌ Admin access only.", show_alert=True)
            return
        rejection = reject_purchase(purchase_id, query.from_user.id)
        if rejection and isinstance(rejection, dict) and rejection.get('already_processed'):
            await query.answer(f"Already {rejection.get('status', 'processed')}", show_alert=True)
            return
        if rejection:
            await query.answer("✅ Purchase rejected", show_alert=False)
            await query.message.reply_text("✅ Purchase request has been rejected.")
        else:
            await query.answer("❌ Failed to reject purchase", show_alert=True)
    elif query.data.startswith("order_flavor_"):
        flavor_id = int(query.data.split("_")[-1])
        user_id = query.from_user.id
        if not check_user_approved(user_id):
            await query.answer("Registration pending approval. Contact admin.", show_alert=True)
            return
        if await process_shake_order(user_id, flavor_id, context):
            credits = get_user_credits(user_id)
            await query.answer("✅ Shake order placed!", show_alert=True)
            await query.message.reply_text(
                f"✅ *Shake Order Placed!*\n\n"
                f"🥤 Your shake has been ordered\n"
                f"1️⃣ Credit deducted\n"
                f"✅ Available credits left: {credits['available_credits']}\n\n"
                f"Your shake will be ready soon!",
                parse_mode='Markdown'
            )
        else:
            await query.answer("❌ Failed to place order. Check your credits.", show_alert=True)
    elif query.data.startswith("shake_paid_"):
        # Admin marks shake order as PAID
        shake_id = int(query.data.split("_")[-1])
        admin_id = query.from_user.id
        
        if not is_admin_id(admin_id):
            await query.answer("❌ Admin access only.", show_alert=True)
            return
        
        try:
            from src.database.payment_approvals import approve_shake_payment
            result = approve_shake_payment(shake_id, admin_id)
            
            if result:
                user_id = result.get('user_id')
                flavor_name = result.get('flavor_name', f"Flavor #{result.get('flavor_id')}")
                
                # Notify user that order is approved (paid path)
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ *Your Shake Order is Approved - PAID*\n\n"
                             f"🥤 *{flavor_name}*\n"
                             f"💵 *Status:* PAID\n"
                             f"📋 *Request ID:* #{shake_id}\n\n"
                             f"Your shake is being prepared and ready for pickup soon! 🎉",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {user_id}: {e}")
                
                # Confirm to admin
                await query.answer("✅ Shake marked as PAID - order approved!", show_alert=False)
                await query.edit_message_text(
                    text=f"✅ *SHAKE ORDER - PAID*\n\n"
                         f"Order #{shake_id} marked as PAID and approved.\n"
                         f"User will be notified.",
                    parse_mode='Markdown'
                )
            else:
                await query.answer("❌ Failed to mark shake as paid", show_alert=True)
        except Exception as e:
            logger.error(f"Error processing shake_paid: {e}")
            await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    
    elif query.data.startswith("shake_credit_terms_"):
        # Admin chooses CREDIT TERMS for shake order
        shake_id = int(query.data.split("_")[-1])
        admin_id = query.from_user.id
        
        if not is_admin_id(admin_id):
            await query.answer("❌ Admin access only.", show_alert=True)
            return
        
        try:
            from src.database.payment_approvals import approve_shake_credit
            result = approve_shake_credit(shake_id, admin_id)
            
            if result:
                user_id = result.get('user_id')
                flavor_name = result.get('flavor_name', f"Flavor #{result.get('flavor_id')}")
                
                # Notify user that order is on credit terms with payment reminder
                try:
                    keyboard = [
                        [InlineKeyboardButton("✅ Mark as Paid", callback_data=f"user_paid_shake_{shake_id}")],
                    ]
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ *Your Shake Order is Approved - CREDIT TERMS*\n\n"
                             f"🥤 *{flavor_name}*\n"
                             f"📋 *Payment Terms:* Credit\n"
                             f"📋 *Request ID:* #{shake_id}\n\n"
                             f"💳 *Payment Due:* Within 7 days\n"
                             f"📱 *You will receive payment reminders*\n\n"
                             f"Your shake is being prepared for pickup! 🎉",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {user_id}: {e}")
                
                # Confirm to admin
                await query.answer("✅ Shake set to CREDIT TERMS - reminders will start", show_alert=False)
                await query.edit_message_text(
                    text=f"✅ *SHAKE ORDER - CREDIT TERMS*\n\n"
                         f"Order #{shake_id} approved with credit terms.\n"
                         f"Automatic payment reminders will be sent to user.\n"
                         f"User notified.",
                    parse_mode='Markdown'
                )
            else:
                await query.answer("❌ Failed to set credit terms", show_alert=True)
        except Exception as e:
            logger.error(f"Error processing shake_credit_terms: {e}")
            await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    
    elif query.data.startswith("user_paid_shake_"):
        # User confirms payment for credit-based shake order
        shake_id = int(query.data.split("_")[-1])
        user_id = query.from_user.id
        
        try:
            from src.database.shake_operations import mark_user_paid_for_shake
            result = mark_user_paid_for_shake(shake_id, user_id)
            
            if result:
                # Notify admins that user confirmed payment
                admin_text = (
                    f"🔔 *USER PAYMENT CONFIRMATION*\n\n"
                    f"👤 *User:* {get_user(user_id)['full_name']}\n"
                    f"📱 *ID:* {user_id}\n"
                    f"📋 *Shake Request ID:* #{shake_id}\n\n"
                    f"✅ User has confirmed payment for their credit-based shake order.\n\n"
                    f"*ACTION:* Please review and approve final payment if needed."
                )
                
                try:
                    admin_ids = get_moderator_chat_ids()
                    for admin_id in admin_ids:
                        try:
                            keyboard = [
                                [InlineKeyboardButton("✅ Approve Payment", callback_data=f"admin_approve_user_payment_{shake_id}")],
                            ]
                            await context.bot.send_message(
                                chat_id=admin_id,
                                text=admin_text,
                                reply_markup=InlineKeyboardMarkup(keyboard),
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            logger.error(f"Failed to notify admin {admin_id}: {e}")
                except Exception as e:
                    logger.error(f"Failed to get admin IDs: {e}")
                
                # Confirm to user
                await query.answer("✅ Payment confirmation sent to admin", show_alert=False)
                await query.edit_message_text(
                    text=f"✅ *Payment Confirmed*\n\n"
                         f"Your payment for order #{shake_id} has been confirmed.\n"
                         f"Admins will review and approve shortly. ⏳",
                    parse_mode='Markdown'
                )
            else:
                await query.answer("❌ Failed to confirm payment", show_alert=True)
        except Exception as e:
            logger.error(f"Error processing user_paid_shake: {e}")
            await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    
    elif query.data.startswith("admin_approve_user_payment_"):
        # Admin approves user's payment confirmation
        shake_id = int(query.data.split("_")[-1])
        admin_id = query.from_user.id
        
        if not is_admin_id(admin_id):
            await query.answer("❌ Admin access only.", show_alert=True)
            return
        
        try:
            from src.database.shake_operations import approve_user_payment
            result = approve_user_payment(shake_id, admin_id)
            
            if result:
                user_id = result.get('user_id')
                
                # Notify user that payment is approved
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ *Payment Approved!*\n\n"
                             f"Your payment for order #{shake_id} has been approved by admin.\n"
                             f"Thank you! 🙏",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {user_id}: {e}")
                
                await query.answer("✅ Payment approved", show_alert=False)
                await query.edit_message_text(
                    text=f"✅ *USER PAYMENT APPROVED*\n\n"
                         f"Order #{shake_id} payment confirmed and approved.\n"
                         f"No further reminders will be sent.",
                    parse_mode='Markdown'
                )
            else:
                await query.answer("❌ Failed to approve payment", show_alert=True)
        except Exception as e:
            logger.error(f"Error processing admin_approve_user_payment: {e}")
            await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    # Legacy callbacks
    elif query.data == "stats":
        await callback_stats(update, context)
    elif query.data == "checkin":
        await callback_checkin(update, context)
    elif query.data == "shake":
        await callback_shake(update, context)
    elif query.data.startswith("select_flavor_"):
        await callback_select_flavor(update, context)
    elif query.data == "leaderboard":
        await callback_leaderboard(update, context)
    elif query.data == "log_activity":
        await callback_log_activity(update, context)
    elif query.data == "settings":
        await callback_settings(update, context)
    elif query.data == "main_menu":
        await callback_main_menu(update, context)
    # Commerce hub callbacks
    elif query.data.startswith("store_") or query.data.startswith("sub_") or \
         query.data.startswith("pt_") or query.data.startswith("event_"):
        await handle_commerce_callbacks(update, context)
    else:
        pass

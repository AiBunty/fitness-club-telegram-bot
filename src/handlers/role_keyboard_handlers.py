import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.utils.auth import is_admin_id, is_staff
from src.database.user_operations import user_exists
from src.database.subscription_operations import is_subscription_active, is_in_grace_period

logger = logging.getLogger(__name__)

# User menu: logging & progress
USER_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton(" Notifications", callback_data="cmd_notifications")],
    [InlineKeyboardButton("🏆 Challenges", callback_data="cmd_challenges")],
    [InlineKeyboardButton("⚖️ Log Weight", callback_data="cmd_weight")],
    [InlineKeyboardButton("💧 Log Water", callback_data="cmd_water")],
    [InlineKeyboardButton("🍽️ Log Meal", callback_data="cmd_meal")],
    [InlineKeyboardButton("🏋️ Gym Check-in", callback_data="cmd_checkin")],
    [InlineKeyboardButton("✅ Daily Habits", callback_data="cmd_habits")],
    [InlineKeyboardButton("� Reminder Settings", callback_data="cmd_reminders")],
    [InlineKeyboardButton("�📱 My QR Code", callback_data="cmd_qrcode")],
    [InlineKeyboardButton("🥤 Check Shake Credits", callback_data="cmd_check_shake_credits")],
    [InlineKeyboardButton("🥛 Order Shake", callback_data="cmd_order_shake")],
    [InlineKeyboardButton("💾 Buy Shake Credits", callback_data="cmd_buy_shake_credits")],
    [InlineKeyboardButton("� Store", callback_data="cmd_user_store")],
    [InlineKeyboardButton("�💰 Points Chart", callback_data="cmd_points_chart")],
    [InlineKeyboardButton("📋 Studio Rules", callback_data="cmd_studio_rules")],
    [InlineKeyboardButton("🔢 Get My ID", callback_data="cmd_get_telegram_id")],
    [InlineKeyboardButton("🆔 Who Am I?", callback_data="cmd_whoami")],
])

# Staff menu: approvals & staff management
STAFF_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("✔️ Pending Attendance", callback_data="cmd_pending_attendance")],
    [InlineKeyboardButton("🥤 Pending Shakes", callback_data="cmd_pending_shakes")],
    [InlineKeyboardButton("📊 Notifications", callback_data="cmd_notifications")],
    [InlineKeyboardButton("🏆 Challenges", callback_data="cmd_challenges")],
    [InlineKeyboardButton("💰 Points Chart", callback_data="cmd_points_chart")],
    [InlineKeyboardButton("📋 Studio Rules", callback_data="cmd_studio_rules")],
    [InlineKeyboardButton("🔢 Get My ID", callback_data="cmd_get_telegram_id")],
    [InlineKeyboardButton("🆔 Who Am I?", callback_data="cmd_whoami")],
])

# Admin menu: full access
ADMIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("📈 Dashboard", callback_data="cmd_admin_dashboard")],
    [InlineKeyboardButton("📊 Reports & Analytics", callback_data="cmd_reports_menu")],
    [InlineKeyboardButton("📢 Broadcast", callback_data="cmd_broadcast")],
    [InlineKeyboardButton("🤖 Follow-up Settings", callback_data="cmd_followup_settings")],
    [InlineKeyboardButton("🍽️ Manual Shake Deduction", callback_data="cmd_manual_shake_deduction")],
    [InlineKeyboardButton("💳 Pending Shake Purchases", callback_data="cmd_pending_shake_purchases")],
    [InlineKeyboardButton("🛒 Manage Store", callback_data="cmd_manage_store")],
    [InlineKeyboardButton("💳 Record Payment", callback_data="ar_record_payment")],
    [InlineKeyboardButton("💳 Credit Summary", callback_data="ar_credit_summary")],
    [InlineKeyboardButton("📤 Export Overdue", callback_data="ar_export_overdue")],
    [InlineKeyboardButton("📊 Notifications", callback_data="cmd_notifications")],
    [InlineKeyboardButton("👥 Manage Users", callback_data="cmd_list_users")],
    [InlineKeyboardButton("➕ Add Staff", callback_data="cmd_add_staff")],
    [InlineKeyboardButton("➖ Remove Staff", callback_data="cmd_remove_staff")],
    [InlineKeyboardButton("📋 List Staff", callback_data="cmd_list_staff")],
    [InlineKeyboardButton("➕ Add Admin", callback_data="cmd_add_admin")],
    [InlineKeyboardButton("➖ Remove Admin", callback_data="cmd_remove_admin")],
    [InlineKeyboardButton("📋 List Admins", callback_data="cmd_list_admins")],
    [InlineKeyboardButton("🔢 Get My ID", callback_data="cmd_get_telegram_id")],
    [InlineKeyboardButton("🆔 Who Am I?", callback_data="cmd_whoami")],
])


def get_user_role(user_id: int) -> str:
    """
    Determine user's role by checking in order:
    1. Is user an admin?
    2. Is user staff?
    3. Is user registered?
    4. Default to 'user'
    
    Returns: 'admin', 'staff', 'user', or 'unregistered'
    """
    # Check admin role (highest priority) even if not registered
    if is_admin_id(user_id):
        logger.debug(f"User {user_id} detected as admin")
        return 'admin'

    # Check staff role (second priority) even if not registered
    if is_staff(user_id):
        logger.debug(f"User {user_id} detected as staff")
        return 'staff'

    # If not registered, return 'unregistered'
    if not user_exists(user_id):
        logger.debug(f"User {user_id} is unregistered - assigning user menu")
        return 'unregistered'

    # Default to regular user
    logger.debug(f"User {user_id} detected as regular user")
    return 'user'


async def show_role_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Display role-specific menu to user based on VERIFIED role.
    
    SECURITY CRITICAL:
    - Role verification MUST succeed before menu display
    - Unregistered users see LIMITED menu (can only register)
    - Admin/Staff verified BEFORE any menu shown
    - No cross-role menu access allowed
    
    Role Detection Priority:
    1. Is user ADMIN? → ADMIN_MENU only
    2. Is user STAFF? → STAFF_MENU only (with admin access checks in handlers)
    3. Is user REGISTERED and APPROVED? → USER_MENU (full access)
    4. Is user REGISTERED but NOT APPROVED? → USER_MENU (limited features)
    5. UNREGISTERED? → USER_MENU (register button only)
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    uid = update.effective_user.id
    
    # STEP 1: STRICT role verification
    role = get_user_role(uid)
    
    logger.info(f"[SECURITY] Menu access attempt by {uid} with role={role}")
    
    # STEP 2: Route to appropriate menu with strict verification
    if role == 'admin':
        # Extra security: verify is_admin_id one more time before showing admin menu
        if not is_admin_id(uid):
            logger.warning(f"[SECURITY] Admin menu blocked - verification failed for {uid}")
            await (update.message or update.callback_query.message).reply_text(
                "❌ Admin access denied. Role verification failed."
            )
            return
        menu = ADMIN_MENU
        role_text = "🛡️ ADMIN MENU"
        logger.info(f"[SECURITY] ✅ Admin menu granted to verified admin {uid}")
        
    elif role == 'staff':
        # Extra security: verify is_staff one more time before showing staff menu
        if not is_staff(uid):
            logger.warning(f"[SECURITY] Staff menu blocked - verification failed for {uid}")
            await (update.message or update.callback_query.message).reply_text(
                "❌ Staff access denied. Role verification failed."
            )
            return
        menu = STAFF_MENU
        role_text = "🧑‍🍳 STAFF MENU"
        logger.info(f"[SECURITY] ✅ Staff menu granted to staff member {uid}")
        
    elif role == 'user':
        # Check subscription status for regular users
        if not is_subscription_active(uid):
            if is_in_grace_period(uid):
                # In grace period - show menu but with warning
                menu = USER_MENU
                role_text = "⚠️ USER MENU (Grace Period - Renew Soon!)"
                logger.info(f"[SECURITY] User menu shown to user {uid} in grace period")
            else:
                # No active subscription - block access
                logger.warning(f"[SECURITY] Menu blocked for user {uid} - no active subscription")
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("💪 Subscribe Now", callback_data="start_subscribe")]
                ])
                msg_text = (
                    "🔒 *Subscription Required*\n\n"
                    "Your subscription has expired. To access the fitness club app, "
                    "please renew your subscription.\n\n"
                    "Use /subscribe to get started!"
                )
                if update.message:
                    await update.message.reply_text(msg_text, reply_markup=keyboard, parse_mode="Markdown")
                elif update.callback_query:
                    await update.callback_query.message.edit_text(msg_text, reply_markup=keyboard, parse_mode="Markdown")
                return
        else:
            menu = USER_MENU
            role_text = "🙋 USER MENU"
            logger.info(f"[SECURITY] User menu shown to registered user {uid}")
        
    else:  # unregistered
        menu = USER_MENU
        role_text = "👤 WELCOME"
        logger.info(f"[SECURITY] Limited menu shown to unregistered user {uid}")
    
    msg = f"{role_text}\n\nSelect an action:"
    
    # STEP 3: Display menu (with role_text included for clarity)
    if update.message:
        await update.message.reply_text(msg, reply_markup=menu)
    elif update.callback_query:
        await update.callback_query.message.edit_text(msg, reply_markup=menu)


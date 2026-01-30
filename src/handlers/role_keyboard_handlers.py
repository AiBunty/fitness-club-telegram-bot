import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.utils.auth import is_admin_id, is_staff
from src.database.user_operations import user_exists
from src.database.subscription_operations import is_subscription_active, is_in_grace_period
from src.utils.access_gate import get_user_access_state, check_access_gate, STATE_NEW_USER, STATE_REGISTERED_NO_SUBSCRIPTION, STATE_EXPIRED_SUBSCRIBER, STATE_ACTIVE_SUBSCRIBER

logger = logging.getLogger(__name__)

# User menu: logging & progress
USER_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔔 Notifications", callback_data="cmd_notifications")],
    [InlineKeyboardButton("🏆 Challenges", callback_data="cmd_challenges")],
    [InlineKeyboardButton("⚖️ Log Weight", callback_data="cmd_weight")],
    [InlineKeyboardButton("💧 Log Water", callback_data="cmd_water")],
    [InlineKeyboardButton("🍽️ Log Meal", callback_data="cmd_meal")],
    [InlineKeyboardButton("🏋️ Gym Check-in", callback_data="cmd_checkin")],
    [InlineKeyboardButton("✅ Daily Habits", callback_data="cmd_habits")],
    [InlineKeyboardButton("⏰ Reminder Settings", callback_data="cmd_reminders")],
    [InlineKeyboardButton("📱 My QR Code", callback_data="cmd_qrcode")],
    [InlineKeyboardButton("🥤 Check Shake Credits", callback_data="cmd_check_shake_credits")],
    [InlineKeyboardButton("🥛 Order Shake", callback_data="cmd_order_shake")],
    [InlineKeyboardButton("💾 Buy Shake Credits", callback_data="cmd_buy_shake_credits")],
    [InlineKeyboardButton("🛒 Store", callback_data="cmd_store")],
    [InlineKeyboardButton("💰 Points Chart", callback_data="cmd_points_chart")],
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
    [InlineKeyboardButton("📝 Edit Welcome Message", callback_data="cmd_edit_welcome_message")],
    [InlineKeyboardButton("🤖 Follow-up Settings", callback_data="cmd_followup_settings")],
    [InlineKeyboardButton("🍽️ Manual Shake Deduction", callback_data="cmd_manual_shake_deduction")],
    [InlineKeyboardButton("💳 Pending Shake Purchases", callback_data="cmd_pending_shake_purchases")],
    [InlineKeyboardButton("🧾 Invoices", callback_data="cmd_invoices")],
    [InlineKeyboardButton("🧾 GST Settings", callback_data="cmd_gst_settings")],
    [InlineKeyboardButton("🏬 Create Store Items", callback_data="cmd_create_store_items")],
    [InlineKeyboardButton("💳 Record Payment", callback_data="ar_record_payment")],
    [InlineKeyboardButton("💳 Credit Summary", callback_data="ar_credit_summary")],
    [InlineKeyboardButton("📤 Export Overdue", callback_data="ar_export_overdue")],
    [InlineKeyboardButton("📊 Notifications", callback_data="cmd_notifications")],
    [InlineKeyboardButton("👥 Manage Users", callback_data="cmd_list_users")],
    [InlineKeyboardButton("👥 Manage Staff", callback_data="admin_manage_staff")],
    [InlineKeyboardButton("🛡 Manage Admins", callback_data="admin_manage_admins")],
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
    
    Returns: 'admin', 'staff', or 'user'
    """
    # Check admin role (highest priority) even if not registered
    if is_admin_id(user_id):
        logger.debug(f"User {user_id} detected as admin")
        return 'admin'

    # Check staff role (second priority) even if not registered
    if is_staff(user_id):
        logger.debug(f"User {user_id} detected as staff")
        return 'staff'

    # Default to regular user
    logger.debug(f"User {user_id} detected as regular user")
    return 'user'


async def show_role_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Display role-specific menu to user based on VERIFIED role.

    SECURITY CRITICAL:
    - Unregistered users must be blocked (no limited menu)
    - Subscription gating is enforced by access_gate (LOCAL_DB skips subscription)
    - Admin/Staff verified BEFORE any menu shown
    - No cross-role menu access allowed
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    uid = update.effective_user.id
    
    # STEP 0: CENTRAL GATE — block unregistered/expired users here
    state, _ = get_user_access_state(uid)
    if state != STATE_ACTIVE_SUBSCRIBER:
        if state == STATE_NEW_USER:
            logger.warning(f"[ACCESS] blocked NEW_USER telegram_id={uid} reason=unregistered")
        elif state == STATE_REGISTERED_NO_SUBSCRIPTION:
            logger.warning(f"[ACCESS] blocked REGISTERED_NO_SUBSCRIPTION telegram_id={uid}")
        elif state == STATE_EXPIRED_SUBSCRIBER:
            logger.warning(f"[ACCESS] blocked EXPIRED_SUBSCRIBER telegram_id={uid}")
        # Send user-facing message
        await check_access_gate(update, context, require_subscription=True)
        logger.info(f"[ACCESS] menu_render_skipped telegram_id={uid}")
        return

    # STEP 1: STRICT role verification (only for ACTIVE state)
    role = get_user_role(uid)
    logger.info(f"[ACCESS] menu_access_attempt telegram_id={uid} role={role}")
    
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
        # Gate already ensured ACTIVE; show full user menu
        menu = USER_MENU
        role_text = "🙋 USER MENU"
        logger.info(f"[ACCESS] user_menu_render telegram_id={uid}")
    
    msg = f"{role_text}\n\nSelect an action:"
    
    # STEP 3: Display menu (with role_text included for clarity)
    if update.message:
        await update.message.reply_text(msg, reply_markup=menu)
    elif update.callback_query:
        await update.callback_query.message.edit_text(msg, reply_markup=menu)


async def show_manage_staff_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Manage Staff submenu (uses existing cmd_* callbacks)."""
    # Ensure only admins can access
    uid = update.callback_query.from_user.id if update.callback_query else update.effective_user.id
    if not is_admin_id(uid):
        await (update.message or update.callback_query.message).reply_text("❌ Admin access denied.")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Staff", callback_data="cmd_add_staff")],
        [InlineKeyboardButton("➖ Remove Staff", callback_data="cmd_remove_staff")],
        [InlineKeyboardButton("📋 List Staff", callback_data="cmd_list_staff")],
        [InlineKeyboardButton("⬅ Back", callback_data="cmd_admin_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text("👥 Manage Staff\n\nChoose an action:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("👥 Manage Staff\n\nChoose an action:", reply_markup=reply_markup)


async def show_manage_admins_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Manage Admins submenu (uses existing cmd_* callbacks)."""
    uid = update.callback_query.from_user.id if update.callback_query else update.effective_user.id
    if not is_admin_id(uid):
        await (update.message or update.callback_query.message).reply_text("❌ Admin access denied.")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Admin", callback_data="cmd_add_admin")],
        [InlineKeyboardButton("➖ Remove Admin", callback_data="cmd_remove_admin")],
        [InlineKeyboardButton("📋 List Admins", callback_data="cmd_list_admins")],
        [InlineKeyboardButton("⬅ Back", callback_data="cmd_admin_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text("🛡 Manage Admins\n\nChoose an action:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("🛡 Manage Admins\n\nChoose an action:", reply_markup=reply_markup)


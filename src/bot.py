from datetime import time as dt_time
import logging
from logging.handlers import RotatingFileHandler
import sys
import os
import asyncio
from telegram import BotCommand, MenuButtonCommands, Update
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from src.handlers.store_user_handlers import get_store_conversation_handler
from src.handlers.store_admin_handlers import get_store_admin_conversation_handler
from src.handlers.store_excel_handlers import get_store_excel_conversation_handler
from src.database.store_operations import create_or_update_product  # For migration check
from src.config import TELEGRAM_BOT_TOKEN
from src.database.connection import test_connection
from src.handlers.user_handlers import (
    start_command, begin_registration, get_name, get_phone, get_age, 
    get_weight, get_gender, get_profile_pic, cancel_registration, registration_timeout,
    menu_command, cmd_qrcode, NAME, PHONE, AGE, WEIGHT, GENDER, PROFILE_PIC,
    handle_location_for_checkin, handle_greeting
)
from src.handlers.role_keyboard_handlers import (
    show_role_menu
)
from src.handlers.callback_handlers import handle_callback_query
from src.handlers.debug_handlers import raw_update_logger
from src.handlers.activity_handlers import (
    cmd_weight, get_weight_input, WEIGHT_VALUE,
    cmd_water, get_water, WATER_CUPS,
    cmd_meal, get_meal_photo, MEAL_PHOTO,
    cmd_habits, get_habits_confirm, HABITS_CONFIRM,
    cmd_checkin, get_checkin_method, get_checkin_photo, CHECKIN_METHOD, CHECKIN_PHOTO,
    cancel_activity
)
from src.handlers.admin_handlers import (
    cmd_pending_attendance, cmd_pending_shakes,
    callback_review_attendance, callback_review_shakes,
    callback_approve_attend, callback_reject_attend,
    callback_ready_shake, callback_cancel_shake,
    cmd_add_staff, cmd_remove_staff, cmd_list_staff, handle_staff_id_input,
    cmd_add_admin, cmd_remove_admin, cmd_list_admins,
    callback_approve_user, callback_reject_user, cmd_pending_users,
    cmd_manual_shake_deduction, get_manual_shake_deduction_handler,
    cmd_qr_attendance_link, cmd_override_attendance, cmd_download_qr_code
)
from src.handlers.analytics_handlers import (
    cmd_admin_dashboard, handle_analytics_callback,
    callback_revenue_stats, callback_member_stats, 
    callback_engagement_stats, callback_challenge_stats,
    callback_top_activities, callback_admin_dashboard
)
from src.handlers.admin_dashboard_handlers import (
    cmd_admin_panel, cmd_member_list, cmd_manage_users, cmd_export_excel,
    callback_back_to_admin_panel, get_manage_users_conversation_handler, get_template_conversation_handler, get_followup_conversation_handler
)
from src.handlers.payment_handlers import (
    cmd_challenges, callback_pay_fee,
    get_payment_amount, get_payment_method, confirm_payment,
    callback_join_challenge, callback_challenge_leaderboard,
    callback_close, cancel_payment, PAYMENT_AMOUNT, PAYMENT_METHOD, 
    PAYMENT_CONFIRM
)
from src.handlers.notification_handlers import (
    cmd_notifications, callback_view_notification, callback_delete_notification,
    callback_mark_all_read, callback_notification_back, callback_close_notifications,
    callback_admin_pending_subs, callback_admin_pending_payments, callback_admin_my_notifs
)
from src.handlers.challenge_handlers import (
    cmd_challenges, cmd_my_challenges, callback_challenge_view,
    callback_challenge_join, callback_challenge_progress, 
    callback_challenge_leaderboard, callback_challenge_back, 
    callback_challenge_close, register_challenge_callbacks
)
from src.handlers.admin_challenge_handlers import (
    cmd_admin_challenges, callback_create_challenge, process_challenge_name,
    callback_challenge_type, process_start_date, process_end_date,
    callback_challenge_pricing, process_entry_amount, process_challenge_desc,
    callback_confirm_create, callback_cancel_create, callback_view_active_challenges,
    callback_payment_status, callback_challenge_stats, get_admin_challenge_handler
)
from src.handlers.misc_handlers import cmd_whoami
from src.handlers.broadcast_handlers import (
    get_broadcast_conversation_handler, cmd_followup_settings,
    view_broadcast_history, send_followup_to_inactive_users,
    cmd_tune_followup_settings, callback_tune_followup_interval
)
from src.handlers.payment_request_handlers import (
    payment_request_conversation, approval_conversation,
    cmd_pending_requests, callback_review_request, callback_reject_request
)
from src.handlers.report_handlers import (
    cmd_reports_menu, callback_report_overview, callback_report_active,
    callback_report_inactive, callback_report_expiring, callback_report_today,
    callback_report_top_performers, callback_report_inactive_users,
    callback_report_eod, callback_export_active, callback_export_inactive,
    callback_report_export, callback_move_expired
)
from src.handlers.subscription_handlers import (
    cmd_subscribe, cmd_my_subscription, cmd_admin_subscriptions,
    callback_admin_approve_sub, callback_approve_sub_standard,
    callback_custom_amount, callback_select_end_date, callback_reject_sub,
    get_subscription_conversation_handler, get_admin_approval_conversation_handler,
    callback_admin_reject_upi, callback_admin_reject_cash
)
from src.handlers.ar_handlers import (
    get_ar_conversation_handler, ar_export_overdue, ar_credit_summary
)
from src.handlers.admin_settings_handlers import (
    cmd_admin_settings, get_admin_settings_handler
)
from src.handlers.reminder_settings_handlers import (
    cmd_reminders, get_reminder_conversation_handler
)
from src.utils.scheduled_jobs import (
    send_eod_report, check_expired_memberships,
    send_water_reminder_hourly, send_weight_reminder_morning, send_habits_reminder_evening,
    send_shake_credit_reminders
)
from src.utils.monitoring import (
    check_overdue_reminder_spike, check_bulk_expiry_candidates, send_alert_to_admin
)
from src.utils.subscription_scheduler import (
    send_expiry_reminders, send_grace_period_reminders,
    send_followup_reminders, lock_expired_subscriptions
)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging with rotating file handler to prevent disk space issues
# Max 10MB per file, keep 5 backup files = max 60MB total
file_handler = RotatingFileHandler(
    'logs/fitness_bot.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)


def _get_commands_for_role(role: str) -> list:
    """Get bot commands list based on user role.
    
    Args:
        role: One of 'user', 'staff', or 'admin'
        
    Returns:
        List of BotCommand objects for the given role
    """
    # User commands - available to all users
    user_commands = [
        BotCommand("start", "Welcome & info"),
        BotCommand("register", "Begin registration"),
        BotCommand("menu", "Open main menu"),
        BotCommand("qrcode", "Get gym login QR code"),
        BotCommand("weight", "Log weight"),
        BotCommand("water", "Log water intake"),
        BotCommand("reminders", "Reminder Settings"),
        BotCommand("meal", "Log meal photo"),
        BotCommand("checkin", "Gym check-in"),
        BotCommand("habits", "Daily habits"),
        BotCommand("challenges", "Browse challenges"),
        BotCommand("my_challenges", "My challenges"),
        BotCommand("notifications", "My notifications"),
        BotCommand("whoami", "Show my ID & role"),
        BotCommand("subscribe", "Subscribe to gym membership"),
        BotCommand("my_subscription", "View subscription status"),
            BotCommand("store", "Shop gym products"),
    ]
    
    # Staff commands - staff-specific management
    staff_commands = [
        BotCommand("pending_attendance", "Review attendance"),
        BotCommand("pending_shakes", "Review shakes"),
        BotCommand("add_staff", "Assign staff"),
        BotCommand("remove_staff", "Remove staff"),
        BotCommand("list_staff", "List staff"),
    ]
    
    # Admin commands - admin-only operations
    admin_commands = [
        BotCommand("admin_panel", "Admin Control Panel"),
        BotCommand("admin_dashboard", "Admin dashboard"),
        BotCommand("admin_subscriptions", "Manage subscriptions"),
        BotCommand("add_admin", "Assign admin"),
        BotCommand("remove_admin", "Remove admin"),
        BotCommand("list_admins", "List admins"),
        BotCommand("broadcast", "Send broadcast message"),
        BotCommand("followup_settings", "Follow-up settings"),
        BotCommand("pending_requests", "Review payment requests"),
        BotCommand("reports", "Admin reports & analytics"),
            BotCommand("store_admin", "Manage store orders"),
            BotCommand("store_excel", "Bulk upload products"),
    ]
    
    if role == "admin":
        return user_commands + staff_commands + admin_commands
    elif role == "staff":
        return user_commands + staff_commands
    else:  # user or default
        return user_commands


async def _set_bot_commands(application: Application) -> None:
    """Expose a bot-wide command menu so users see buttons in Telegram UI.
    
    Sets the default/global commands visible to users. Individual users will
    get their role-specific command list set when they interact with /start.
    """
    # Set default global commands (user-level) that all users will see initially
    try:
        commands = _get_commands_for_role("user")
        await application.bot.set_my_commands(commands)
        logger.info("Global commands set successfully")
    except Exception as e:
        logger.warning(f"Could not set global commands (non-critical): {e}")
    
    # Set the menu button to show commands
    try:
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonCommands()
        )
        logger.info("Menu button set to show commands")
    except Exception as e:
        logger.warning(f"Could not set menu button: {e}")
    
    # Delete any existing webhook to ensure clean polling start
    # Drop pending updates here to disconnect any other bot instances
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted and pending updates cleared")
    except Exception as e:
        logger.warning(f"Could not delete webhook: {e}")


async def set_commands_for_user(user_id: int, bot) -> None:
    """Dynamically set bot commands for a specific user based on their role.
    
    This function determines the user's role and sets the appropriate
    command list so they only see commands relevant to their role.
    
    Args:
        user_id: Telegram user ID
        bot: Telegram bot instance
    """
    try:
        from src.utils.auth import is_admin, is_staff
        from telegram import BotCommandScopeChat
        
        # Determine user role
        if is_admin(user_id):
            role = "admin"
        elif is_staff(user_id):
            role = "staff"
        else:
            role = "user"
        
        # Get appropriate command list
        commands = _get_commands_for_role(role)
        
        # Set commands for this specific user's chat
        scope = BotCommandScopeChat(user_id)
        await bot.set_my_commands(commands, scope=scope)
        
        logger.info(f"Set {role} commands for user {user_id}")
    except Exception as e:
        logger.error(f"Error setting commands for user {user_id}: {e}")


def main():

    logger.info("Testing database connection...")
    # Allow skipping DB test for local debugging by setting SKIP_DB_TEST=1
    if os.environ.get('SKIP_DB_TEST') != '1':
        if not test_connection():
            logger.error("Database connection failed!")
            sys.exit(1)
    else:
        logger.info("SKIP_DB_TEST=1 set — skipping DB connection test")
    
    logger.info("Database OK! Starting bot...")
    
    # Reduce socket timeout for faster initialization
    import socket
    socket.setdefaulttimeout(5)
    
    logger.info("[APP] Building Telegram Application with token...")
    # Disable SSL verification as workaround for Windows SSL timeout issues
    import ssl
    import certifi
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    logger.info("[APP] Telegram Application built successfully")

    # Register global command menu so Telegram shows command buttons.
    application.post_init = _set_bot_commands
    
    # User registry tracking (pre-handler to catch all messages)
    async def track_user_on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Track user in registry for invoice search - runs on every message.
        
        CRITICAL: Must NOT consume update - always allow propagation.
        """
        # Skip if not a Message update (e.g., CallbackQuery should never reach here)
        if not update.message:
            logger.debug("[TRACKER] Skipping non-message update")
            return False
        
        if not update.effective_user:
            return False
        
        # Track user but DON'T consume the update
        try:
            from src.utils.user_registry import track_user
            track_user(
                user_id=update.effective_user.id,
                first_name=update.effective_user.first_name or '',
                last_name=update.effective_user.last_name or '',
                username=update.effective_user.username or ''
            )
            logger.debug(f"[TRACKER] message tracked user_id={update.effective_user.id}")
        except Exception as e:
            logger.debug(f"[TRACKER] Error: {e}")
        
        # CRITICAL: Return False to allow other handlers to process this update
        return False
    
    application.add_handler(MessageHandler(filters.ALL, track_user_on_message), group=-1)
    
    # Registration conversation
    # Registration conversation (triggered via /register or Register button)
    registration_handler = ConversationHandler(
        entry_points=[
            CommandHandler('register', begin_registration),
            CallbackQueryHandler(begin_registration, pattern="^register$")
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            PROFILE_PIC: [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), get_profile_pic)],
        },
        fallbacks=[CommandHandler('cancel', cancel_registration)],
        conversation_timeout=600,  # 10 minutes timeout to prevent stuck states
        name="registration_conversation"
    )
    
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(registration_handler)
    application.add_handler(CommandHandler('menu', menu_command))
    application.add_handler(CommandHandler('roles', show_role_menu))
    application.add_handler(CommandHandler('qrcode', cmd_qrcode))
    application.add_handler(CommandHandler('whoami', cmd_whoami))
    # Location handler for geofenced studio QR check-in
    application.add_handler(MessageHandler(filters.LOCATION, handle_location_for_checkin))
    # Greeting handler: respond to Hi/Hello with personalized menu
    application.add_handler(MessageHandler(
        filters.Regex(r"(?i)^(hi|hello|hey|greetings)[\s!]*$"),
        handle_greeting
    ))
    
    # Activity logging conversations
    weight_handler = ConversationHandler(
        entry_points=[
            CommandHandler('weight', cmd_weight),
            CallbackQueryHandler(cmd_weight, pattern="^cmd_weight$"),
            CallbackQueryHandler(cmd_weight, pattern="^edit_weight$")  # Add edit_weight callback
        ],
        states={
            WEIGHT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight_input)],
        },
        fallbacks=[CommandHandler('cancel', cancel_activity)]
    )
    
    water_handler = ConversationHandler(
        entry_points=[
            CommandHandler('water', cmd_water),
            CallbackQueryHandler(cmd_water, pattern="^cmd_water$")
        ],
        states={
            WATER_CUPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_water)],
        },
        fallbacks=[CommandHandler('cancel', cancel_activity)]
    )
    
    meal_handler = ConversationHandler(
        entry_points=[
            CommandHandler('meal', cmd_meal),
            CallbackQueryHandler(cmd_meal, pattern="^cmd_meal$")
        ],
        states={
            MEAL_PHOTO: [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), get_meal_photo)],
        },
        fallbacks=[CommandHandler('cancel', cancel_activity)]
    )
    
    habits_handler = ConversationHandler(
        entry_points=[
            CommandHandler('habits', cmd_habits),
            CallbackQueryHandler(cmd_habits, pattern="^cmd_habits$")
        ],
        states={
            HABITS_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_habits_confirm)],
        },
        fallbacks=[CommandHandler('cancel', cancel_activity)]
    )
    
    checkin_handler = ConversationHandler(
        entry_points=[
            CommandHandler('checkin', cmd_checkin),
            CallbackQueryHandler(cmd_checkin, pattern="^checkin$")
        ],
        states={
            CHECKIN_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_checkin_method)],
            CHECKIN_PHOTO: [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), get_checkin_photo)],
        },
        fallbacks=[CommandHandler('cancel', cancel_activity)]
    )
    
    # Payment conversation
    payment_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(callback_pay_fee, pattern="^pay_fee$")],
        states={
            PAYMENT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_payment_amount)],
            PAYMENT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_payment_method)],
            PAYMENT_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_payment)],
        },
        fallbacks=[CommandHandler('cancel', cancel_payment)]
    )
    
    # ==================== CRITICAL: CONVERSATION HANDLERS FIRST ====================
    # ALL ConversationHandlers MUST be at the TOP to prevent generic callback interception
    # Order: User Management → Registration → Invoice → AR → Subscriptions → Store
    
    logger.info("[BOT] Registering ConversationHandlers (PRIORITY ORDER)")
    
    # User Management Conversation (HIGHEST PRIORITY - manages callbacks like manage_*)
    application.add_handler(get_manage_users_conversation_handler())
    application.add_handler(get_template_conversation_handler())
    application.add_handler(get_followup_conversation_handler())
    logger.info("[BOT] ✅ User Management handlers registered")
    
    # Registration and Approval Conversations
    application.add_handler(get_subscription_conversation_handler())
    application.add_handler(get_admin_approval_conversation_handler())
    logger.info("[BOT] ✅ Registration handlers registered")
    
    # Invoice v2 (re-enabled with lazy PDF import)
    # CRITICAL: Registered BEFORE GST/Store to ensure callback priority (cmd_invoices, inv2_*)
    from src.invoices_v2.handlers import get_invoice_v2_handler, handle_pay_bill, handle_reject_bill
    application.add_handler(get_invoice_v2_handler())
    application.add_handler(CallbackQueryHandler(handle_pay_bill, pattern=r"^inv2_pay_[A-Z0-9]+$"))
    application.add_handler(CallbackQueryHandler(handle_reject_bill, pattern=r"^inv2_reject_[A-Z0-9]+$"))
    logger.info("[BOT] ✅ Invoice v2 handlers registered (BEFORE GST/Store)")
    
    # Accounts Receivable (split-payment) conversation
    application.add_handler(get_ar_conversation_handler())
    logger.info("[BOT] ✅ AR handlers registered")
    
    # GST & Store items handlers
    from src.handlers.admin_gst_store_handlers import get_store_and_gst_handlers
    gst_conv, store_conv = get_store_and_gst_handlers()
    application.add_handler(gst_conv)
    application.add_handler(store_conv)
    logger.info("[BOT] ✅ GST/Store handlers registered")
    
    # Store user-facing handlers
    from src.handlers.store_user_handlers import cmd_store
    application.add_handler(CommandHandler('store', cmd_store))
    application.add_handler(get_store_conversation_handler())
    application.add_handler(get_store_admin_conversation_handler())
    application.add_handler(get_store_excel_conversation_handler())
    logger.info("[BOT] ✅ Store user handlers registered")
    
    # Broadcast handlers
    application.add_handler(get_broadcast_conversation_handler())
    logger.info("[BOT] ✅ Broadcast handlers registered")
    
    # Payment request handlers
    application.add_handler(payment_request_conversation)
    application.add_handler(approval_conversation)
    logger.info("[BOT] ✅ Payment request handlers registered")
    
    # ==================== ACTIVITY TRACKING HANDLERS ====================
    application.add_handler(weight_handler)
    application.add_handler(water_handler)
    application.add_handler(meal_handler)
    application.add_handler(habits_handler)
    application.add_handler(checkin_handler)
    application.add_handler(payment_handler)
    
    # ==================== ADMIN COMMAND HANDLERS ====================
    application.add_handler(CommandHandler('pending_attendance', cmd_pending_attendance))
    application.add_handler(CommandHandler('pending_shakes', cmd_pending_shakes))
    application.add_handler(CommandHandler('pending_users', cmd_pending_users))
    application.add_handler(CommandHandler('add_staff', cmd_add_staff))
    application.add_handler(CommandHandler('remove_staff', cmd_remove_staff))
    application.add_handler(CommandHandler('list_staff', cmd_list_staff))
    application.add_handler(CommandHandler('add_admin', cmd_add_admin))
    application.add_handler(CommandHandler('remove_admin', cmd_remove_admin))
    application.add_handler(CommandHandler('list_admins', cmd_list_admins))
    application.add_handler(get_manual_shake_deduction_handler())
    application.add_handler(CommandHandler('qr_attendance_link', cmd_qr_attendance_link))
    application.add_handler(CommandHandler('override_attendance', cmd_override_attendance))
    application.add_handler(CommandHandler('download_qr_code', cmd_download_qr_code))
    application.add_handler(CommandHandler('admin_panel', cmd_admin_panel))
    application.add_handler(CommandHandler('my_subscription', cmd_my_subscription))
    application.add_handler(CommandHandler('admin_subscriptions', cmd_admin_subscriptions))
    application.add_handler(get_admin_settings_handler())
    application.add_handler(get_reminder_conversation_handler())

    # DEBUG: log raw incoming updates without blocking conversation handlers
    application.add_handler(MessageHandler(filters.ALL, raw_update_logger), group=1)
    
    # ==================== SUBSCRIPTION & PAYMENT CALLBACKS ====================

    application.add_handler(CallbackQueryHandler(callback_admin_approve_sub, pattern="^admin_sub_approve$"))
    application.add_handler(CallbackQueryHandler(callback_approve_sub_standard, pattern="^sub_approve_"))
    application.add_handler(CallbackQueryHandler(callback_reject_sub, pattern="^sub_reject_"))
    application.add_handler(CallbackQueryHandler(callback_custom_amount, pattern="^sub_custom_"))
    application.add_handler(CallbackQueryHandler(callback_select_end_date, pattern="^date_"))
    
    # UPI/Cash rejection handlers (approval is now in conversation handler)
    application.add_handler(CallbackQueryHandler(callback_admin_reject_upi, pattern="^admin_reject_upi_"))
    application.add_handler(CallbackQueryHandler(callback_admin_reject_cash, pattern="^admin_reject_cash_"))
    
    # Numeric messages for staff ID assignment/removal (AFTER ConversationHandler)
    application.add_handler(MessageHandler(filters.Regex('^\\d{6,}$'), handle_staff_id_input))
    # User approval callbacks
    application.add_handler(CallbackQueryHandler(callback_approve_user, pattern=r'^approve_user_\d+$'))
    application.add_handler(CallbackQueryHandler(callback_reject_user, pattern=r'^reject_user_\d+$'))
    application.add_handler(CallbackQueryHandler(cmd_admin_panel, pattern="^admin_dashboard_menu$"))
    application.add_handler(CallbackQueryHandler(cmd_member_list, pattern="^admin_members_list"))
    application.add_handler(CallbackQueryHandler(cmd_export_excel, pattern="^admin_export_excel$"))
    application.add_handler(CallbackQueryHandler(callback_back_to_admin_panel, pattern="^admin_dashboard_menu$"))
    
    # Phase 3 handlers
    application.add_handler(CommandHandler('challenges', cmd_challenges))
    application.add_handler(CommandHandler('my_challenges', cmd_my_challenges))
    application.add_handler(CommandHandler('notifications', cmd_notifications))
    application.add_handler(CommandHandler('admin_dashboard', cmd_admin_dashboard))
    
    # Followup settings
    application.add_handler(CommandHandler('followup_settings', cmd_followup_settings))
    application.add_handler(CallbackQueryHandler(cmd_followup_settings, pattern="^cmd_followup_settings$"))
    application.add_handler(CallbackQueryHandler(cmd_tune_followup_settings, pattern="^tune_followup_settings$"))
    application.add_handler(CallbackQueryHandler(callback_tune_followup_interval, pattern="^tune_(7day|14day|30day)$"))
    application.add_handler(CallbackQueryHandler(view_broadcast_history, pattern="^view_followup_log$"))
    
    # Payment request command handlers
    application.add_handler(CommandHandler('pending_requests', cmd_pending_requests))
    application.add_handler(CallbackQueryHandler(callback_review_request, pattern=r'^review_request_\d+$'))
    application.add_handler(CallbackQueryHandler(callback_reject_request, pattern=r'^reject_req_\d+$'))
    
    # Report handlers
    application.add_handler(CommandHandler('reports', cmd_reports_menu))
    application.add_handler(CallbackQueryHandler(cmd_reports_menu, pattern="^cmd_reports_menu$"))
    application.add_handler(CallbackQueryHandler(callback_report_overview, pattern="^report_overview$"))
    application.add_handler(CallbackQueryHandler(callback_report_active, pattern="^report_active$"))
    application.add_handler(CallbackQueryHandler(callback_report_inactive, pattern="^report_inactive$"))
    application.add_handler(CallbackQueryHandler(callback_report_expiring, pattern="^report_expiring$"))
    application.add_handler(CallbackQueryHandler(callback_report_today, pattern="^report_today$"))
    application.add_handler(CallbackQueryHandler(callback_report_top_performers, pattern="^report_top_performers$"))
    application.add_handler(CallbackQueryHandler(callback_report_inactive_users, pattern="^report_inactive_users$"))
    application.add_handler(CallbackQueryHandler(callback_report_eod, pattern="^report_eod$"))
    application.add_handler(CallbackQueryHandler(callback_export_active, pattern="^export_active$"))
    application.add_handler(CallbackQueryHandler(callback_export_inactive, pattern="^export_inactive$"))
    application.add_handler(CallbackQueryHandler(callback_report_export, pattern="^report_export$"))
    application.add_handler(CallbackQueryHandler(callback_move_expired, pattern="^report_move_expired$"))
    
    # Analytics dashboard handlers (FIXED: Register all callbacks directly)
    application.add_handler(CallbackQueryHandler(callback_revenue_stats, pattern="^dashboard_revenue$"))
    application.add_handler(CallbackQueryHandler(callback_member_stats, pattern="^dashboard_members$"))
    application.add_handler(CallbackQueryHandler(callback_engagement_stats, pattern="^dashboard_engagement$"))
    application.add_handler(CallbackQueryHandler(callback_challenge_stats, pattern="^dashboard_challenges$"))
    application.add_handler(CallbackQueryHandler(callback_top_activities, pattern="^dashboard_activities$"))
    application.add_handler(CallbackQueryHandler(callback_admin_dashboard, pattern="^admin_dashboard$"))
    
    # ==================== GENERIC CALLBACK HANDLER (LAST PRIORITY) ====================
    # Exclude ALL conversation-managed callbacks to prevent interception:
    # - manage_* (User Management: toggle_ban, delete_user, etc.)
    # - admin_invoice (Invoice v2 creation)
    # - cmd_invoices, inv2_*, inv_* (Invoice callbacks)
    # - sub_*, admin_sub_* (Subscriptions)
    # - pay_method, admin_approve, admin_reject (Payments)
    application.add_handler(CallbackQueryHandler(
        handle_callback_query, 
        pattern="^(?!pay_method|admin_approve|admin_reject|sub_|admin_sub_|edit_weight|cancel|cmd_invoices|inv_|inv2_|manage_|admin_invoice)"
    ))
    logger.info("[BOT] ✅ Generic callback handler registered (LAST - with exclusions)")
    application.add_handler(CallbackQueryHandler(handle_analytics_callback))
    application.add_handler(CallbackQueryHandler(callback_view_notification, pattern="^notif_"))
    application.add_handler(CallbackQueryHandler(callback_delete_notification, pattern="^delete_notif_"))
    application.add_handler(CallbackQueryHandler(callback_mark_all_read, pattern="^mark_all_read$"))
    application.add_handler(CallbackQueryHandler(callback_notification_back, pattern="^notif_back$"))
    application.add_handler(CallbackQueryHandler(callback_close_notifications, pattern="^close_notif$"))
    application.add_handler(CallbackQueryHandler(callback_admin_pending_subs, pattern="^admin_pending_subs$"))
    application.add_handler(CallbackQueryHandler(callback_admin_pending_payments, pattern="^admin_pending_payments$"))
    # AR export overdue list
    application.add_handler(CallbackQueryHandler(ar_export_overdue, pattern="^ar_export_overdue$"))
    application.add_handler(CallbackQueryHandler(ar_credit_summary, pattern="^ar_credit_summary$"))
    application.add_handler(CallbackQueryHandler(callback_admin_my_notifs, pattern="^admin_my_notifs$"))
    application.add_handler(CallbackQueryHandler(callback_challenge_view, pattern="^challenge_view_"))
    application.add_handler(CallbackQueryHandler(callback_challenge_join, pattern="^challenge_join_"))
    application.add_handler(CallbackQueryHandler(callback_challenge_progress, pattern="^challenge_progress_"))
    application.add_handler(CallbackQueryHandler(callback_challenge_leaderboard, pattern="^challenge_board_"))
    application.add_handler(CallbackQueryHandler(callback_challenge_back, pattern="^challenge_back$"))
    application.add_handler(CallbackQueryHandler(callback_challenge_close, pattern="^challenge_close$"))
    application.add_handler(CallbackQueryHandler(callback_close, pattern="^close$"))
    
    # Phase 6: Admin Challenge Creation Handlers
    application.add_handler(CommandHandler('admin_challenges', cmd_admin_challenges))
    application.add_handler(get_admin_challenge_handler())
    application.add_handler(CallbackQueryHandler(callback_create_challenge, pattern="^admin_create_challenge$"))
    application.add_handler(CallbackQueryHandler(callback_view_active_challenges, pattern="^admin_view_active_challenges$"))
    application.add_handler(CallbackQueryHandler(callback_payment_status, pattern="^admin_payment_status$"))
    application.add_handler(CallbackQueryHandler(callback_challenge_stats, pattern="^admin_challenge_stats$"))
    application.add_handler(CallbackQueryHandler(callback_confirm_create, pattern="^confirm_create_challenge$"))
    application.add_handler(CallbackQueryHandler(callback_cancel_create, pattern="^cancel_create_challenge$"))
    
    # Phase 7: Challenge callbacks from challenge_handlers.py
    register_challenge_callbacks(application)
    
    # Quick action handlers for reminders (from inline reminder messages)
    from src.handlers.reminder_settings_handlers import (
        callback_quick_log_water, callback_quick_set_water_timer, 
        callback_quick_turn_off_water_reminder, callback_quick_water_interval,
        callback_quick_water_interval_custom, handle_custom_water_interval_input
    )
    application.add_handler(CallbackQueryHandler(callback_quick_log_water, pattern="^quick_log_water$"))
    application.add_handler(CallbackQueryHandler(callback_quick_set_water_timer, pattern="^quick_set_water_timer$"))
    application.add_handler(CallbackQueryHandler(callback_quick_turn_off_water_reminder, pattern="^quick_turn_off_water_reminder$"))
    application.add_handler(CallbackQueryHandler(callback_quick_water_interval, pattern="^quick_water_interval_"))
    application.add_handler(CallbackQueryHandler(callback_quick_water_interval_custom, pattern="^quick_water_interval_custom$"))
    
    # Global text handler moved to group=1 to allow conversation handlers (group=0) to process first
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_water_interval_input), group=1)
    
    # Schedule daily jobs
    job_queue = application.job_queue
    
    # Daily follow-up for inactive users at 9 AM
    job_queue.run_daily(
        send_followup_to_inactive_users,
        time=dt_time(hour=9, minute=0),  # 9:00 AM every day
        name="inactive_user_followup"
    )
    logger.info("Scheduled daily follow-up job at 9:00 AM")
    
    # EOD Report at 23:55 (11:55 PM)
    job_queue.run_daily(
        send_eod_report,
        time=dt_time(hour=23, minute=55),  # 11:55 PM every day
        name="eod_report"
    )
    logger.info("Scheduled EOD report at 23:55")
    
    # Check expired memberships at 00:01 (12:01 AM)
    job_queue.run_daily(
        check_expired_memberships,
        time=dt_time(hour=0, minute=1),  # 12:01 AM every day
        name="check_expired_memberships"
    )
    logger.info("Scheduled expiry check at 00:01")
    
    # Per-user water & weight reminders (bootstrap)
    try:
        from src.utils.scheduled_jobs import schedule_all_user_reminders
        # During local debugging we may skip scheduling user reminders which
        # execute DB queries at startup. Honor SKIP_DB_TEST, SKIP_DB_MIGRATIONS, or SKIP_SCHEDULING.
        if os.environ.get('SKIP_DB_TEST') == '1' or os.environ.get('SKIP_DB_MIGRATIONS') == '1' or os.environ.get('SKIP_SCHEDULING') == '1':
            logger.info("Skipping scheduling of user reminders (SKIP_DB_TEST/SKIP_DB_MIGRATIONS/SKIP_SCHEDULING set)")
        else:
            schedule_all_user_reminders(application)
    except Exception as e:
        logger.warning(f"Per-user reminder bootstrap failed: {e}")
    
    # Habits reminder every evening at 8 PM
    job_queue.run_daily(
        send_habits_reminder_evening,
        time=dt_time(hour=20, minute=0),  # 8:00 PM every day
        name="habits_reminder_evening"
    )
    logger.info("Scheduled evening habits reminder at 8:00 PM")
    
    # Shake credit payment reminders every day at 11 AM
    job_queue.run_daily(
        send_shake_credit_reminders,
        time=dt_time(hour=11, minute=0),  # 11:00 AM every day
        name="shake_credit_payment_reminders"
    )
    logger.info("Scheduled shake credit payment reminders at 11:00 AM")

    # Receivables reminders every day at 11:05 AM (placeholder hook)
    try:
        from src.utils.scheduled_jobs import send_receivables_reminders
        job_queue.run_daily(
            send_receivables_reminders,
            time=dt_time(hour=11, minute=5),
            name="receivables_reminders"
        )
        logger.info("Scheduled receivables reminders at 11:05 AM")
    except Exception as e:
        logger.warning(f"Receivables reminder hook not registered: {e}")
    
    # Monitoring checks (run shortly after receivables reminders)
    def _monitoring_checks(context):
        try:
            # Spike detection for overdue shake reminders (recent window)
            spike = check_overdue_reminder_spike(minutes_window=10, threshold=50)
            if spike.get('count', 0) >= 50:
                send_alert_to_admin(context.bot, f"ALERT: overdue_reminder spike detected: {spike['count']} records in last 10 minutes")

            # Bulk expiry candidate detection (today)
            from datetime import date
            today = date.today()
            bulk = check_bulk_expiry_candidates(today, threshold=500)
            if bulk.get('count', 0) >= 500:
                send_alert_to_admin(context.bot, f"ALERT: bulk expiry candidates detected: {bulk['count']} users")
        except Exception as exc:
            logger.error(f"Monitoring checks failed: {exc}", exc_info=True)

    try:
        job_queue.run_daily(
            _monitoring_checks,
            time=dt_time(hour=11, minute=10),
            name="monitoring_checks"
        )
        logger.info("Scheduled monitoring checks at 11:10 AM")
    except Exception as e:
        logger.warning(f"Monitoring job not scheduled: {e}")
    
    # Subscription expiry reminders at 9 AM
    job_queue.run_daily(
        lambda context: send_expiry_reminders(context.bot),
        time=dt_time(hour=9, minute=0),  # 9:00 AM every day
        name="subscription_expiry_reminders"
    )
    logger.info("Scheduled subscription expiry reminders at 9:00 AM")
    
    # Grace period reminders at 10 AM
    job_queue.run_daily(
        lambda context: send_grace_period_reminders(context.bot),
        time=dt_time(hour=10, minute=0),  # 10:00 AM every day
        name="grace_period_reminders"
    )
    logger.info("Scheduled grace period reminders at 10:00 AM")
    
    # Follow-up reminders every 3 days at 11 AM  
    job_queue.run_repeating(
        lambda context: send_followup_reminders(context.bot),
        interval=259200,  # Every 3 days (259200 seconds)
        first=39600,  # First run at 11:00 AM (11*3600)
        name="followup_reminders"
    )
    logger.info("Scheduled follow-up reminders every 3 days at 11:00 AM")
    
    # Lock expired subscriptions at 00:05 (12:05 AM)
    job_queue.run_daily(
        lambda context: lock_expired_subscriptions(context.bot),
        time=dt_time(hour=0, minute=5),  # 12:05 AM every day
        name="lock_expired_subscriptions"
    )
    logger.info("Scheduled expired subscription locking at 00:05")
    
    # Expire events just after midnight
    try:
        from src.utils.scheduled_jobs import hide_expired_events
        job_queue.run_daily(
            hide_expired_events,
            time=dt_time(hour=0, minute=10),
            name="hide_expired_events"
        )
        logger.info("Scheduled event expiry job at 00:10")
    except Exception as e:
        logger.warning(f"Event expiry job not scheduled: {e}")
    
    # Add global error handler for unhandled exceptions
    async def error_handler(update, context):
        """Log errors, handle RetryAfter, and ignore BadRequest from expired queries"""
        if context.error is None:
            return
        
        # Handle Telegram rate limiting
        from telegram.error import RetryAfter
        if isinstance(context.error, RetryAfter):
            retry_after = context.error.retry_after
            logger.warning(f"Rate limit hit. Retry after {retry_after} seconds")
            await asyncio.sleep(retry_after)
            return
        
        # Ignore BadRequest errors from expired callback queries
        if "BadRequest" in str(type(context.error).__name__):
            logger.debug(f"Ignoring BadRequest error (likely expired query): {context.error}")
            return
        
        logger.error(f"An error occurred: {context.error}", exc_info=context.error)
    
    application.add_error_handler(error_handler)
    
    # ================================================================
    # FLASK WEB SERVER FOR QR ATTENDANCE
    # ================================================================
    # Start Flask web server on main thread (waitress WSGI server)
    # This allows QR attendance endpoints while polling continues
    if os.environ.get('SKIP_FLASK') != '1':
        try:
            import threading
            import time
            from src.web.app import create_app
            from waitress import serve
            from src.utils.admin_notifications import set_telegram_app
            
            # Set telegram app reference for admin notifications
            set_telegram_app(application)
            logger.info("Telegram app reference set for admin notifications")
            
            # Create Flask app
            flask_app = create_app()
            logger.info("Flask app created for QR attendance")
            
            # Start Flask on separate thread using waitress
            def run_flask():
                logger.info("Starting Flask web server on :5000...")
                try:
                    serve(flask_app, host='0.0.0.0', port=5000, _quiet=True)
                except Exception as e:
                    logger.error(f"Flask server error: {e}", exc_info=True)
            
            flask_thread = threading.Thread(target=run_flask, daemon=True)
            flask_thread.start()
            logger.info("Flask thread started (daemon)")
            
            # Give Flask 1 second to start before polling
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Flask startup interrupted")
            
        except ImportError:
            logger.warning("Flask or waitress not installed - QR attendance disabled")
        except Exception as e:
            logger.error(f"Error starting Flask: {e}", exc_info=True)
            logger.warning("Continuing bot without Flask web server")
    else:
        logger.info("Skipping Flask web server (SKIP_FLASK=1)")
    
    logger.info("Bot starting...")
    logger.info("Bot starting...")
    logger.info(f"Running polling with allowed_updates: {['message', 'callback_query']}")
    
    # ================================================================
    # START POLLING
    # ================================================================
    # Manually control the polling loop to keep bot running
    import signal
    import asyncio
    
    # Flag to control the polling loop
    running = True
    
    def signal_handler(sig, frame):
        nonlocal running
        logger.info("[BOT] Received shutdown signal")
        running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("[BOT] Starting polling...")
        
        # Use run_polling which should block indefinitely
        application.run_polling(
            allowed_updates=['message', 'callback_query'],
            stop_signals=None  # Don't let PTB handle signals, we'll handle manually
        )
        
        logger.info("[BOT] Polling completed - bot will restart via wrapper script")
        
    except KeyboardInterrupt:
        logger.info("[BOT] Interrupted by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"[BOT] Error in polling: {type(e).__name__}: {e}", exc_info=True)
    finally:
        logger.info("[BOT] Bot shutdown complete")

if __name__ == '__main__':
    main()

from src.handlers.store_user_handlers import get_store_conversation_handler
from src.handlers.store_admin_handlers import get_store_admin_conversation_handler
from src.handlers.store_excel_handlers import get_store_excel_conversation_handler
from src.database.store_operations import create_or_update_product  # For migration check

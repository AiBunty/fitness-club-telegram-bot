import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.database.notifications_operations import (
    get_user_notifications, mark_notification_read, mark_all_notifications_read,
    delete_notification
)
from src.utils.guards import check_approval
from src.utils.auth import is_admin

logger = logging.getLogger(__name__)

async def cmd_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user notifications + admin pending items"""
    # Check if approved first
    if not await check_approval(update, context):
        return
    
    user_id = update.effective_user.id
    
    # Handle both command and callback contexts
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    # For admins, show pending items first
    if is_admin(user_id):
        from src.database.subscription_operations import get_pending_subscription_requests
        from src.database.payment_request_operations import get_pending_payment_requests
        
        pending_subs = get_pending_subscription_requests()
        pending_payments = get_pending_payment_requests()
        
        keyboard = []
        
        if pending_subs:
            keyboard.append([InlineKeyboardButton(
                f"📋 Pending Subscriptions ({len(pending_subs)})", 
                callback_data="admin_pending_subs"
            )])
        
        if pending_payments:
            keyboard.append([InlineKeyboardButton(
                f"💳 Pending Payment Requests ({len(pending_payments)})", 
                callback_data="admin_pending_payments"
            )])
        
        if keyboard:
            keyboard.append([InlineKeyboardButton("📬 My Notifications", callback_data="admin_my_notifs")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = "🔔 *Admin Notifications*\n\n"
            text += "You have pending items that need attention:"
            
            await message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return
    
    notifications = get_user_notifications(user_id, unread_only=False, limit=20)
    
    if not notifications:
        await message.reply_text("📬 No notifications.")
        return
    
    keyboard = []
    for notif in notifications[:10]:
        status = "🆕" if not notif['is_read'] else "✓"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {notif['title'][:40]}",
                callback_data=f"notif_{notif['notification_id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("✅ Mark All Read", callback_data="mark_all_read"),
        InlineKeyboardButton("❌ Close", callback_data="close_notif")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"📬 *Notifications* ({len(notifications)} total)\n\n"
    text += "Tap a notification to view details."
    
    await message.reply_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_view_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View notification details"""
    query = update.callback_query
    
    notif_id = int(query.data.split("_")[1])
    
    notifications = get_user_notifications(query.from_user.id, unread_only=False)
    
    notif = None
    for n in notifications:
        if n['notification_id'] == notif_id:
            notif = n
            break
    
    if not notif:
        await query.answer("❌ Notification not found.", show_alert=True)
        return
    
    # Mark as read
    mark_notification_read(notif_id)
    
    message = f"📨 *{notif['title']}*\n\n"
    message += f"{notif['description']}\n\n"
    message += f"_Received: {notif['created_at']}_"
    
    keyboard = [
        [InlineKeyboardButton("🗑 Delete", callback_data=f"delete_notif_{notif_id}")],
        [InlineKeyboardButton("📬 Back", callback_data="notif_back")]
    ]
    
    if notif['link_data']:
        keyboard.insert(0, [InlineKeyboardButton("🔗 View", callback_data=f"notif_link_{notif_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_delete_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete notification"""
    query = update.callback_query
    
    notif_id = int(query.data.split("_")[2])
    
    delete_notification(notif_id)
    
    await query.answer("✅ Notification deleted.", show_alert=False)
    await cmd_notifications(update, context)

async def callback_mark_all_read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark all notifications as read"""
    query = update.callback_query
    user_id = query.from_user.id
    
    mark_all_notifications_read(user_id)
    
    await query.answer("✅ All marked as read.", show_alert=False)
    
    notifications = get_user_notifications(user_id, unread_only=False, limit=20)
    
    keyboard = []
    for notif in notifications[:10]:
        keyboard.append([
            InlineKeyboardButton(
                f"✓ {notif['title'][:40]}",
                callback_data=f"notif_{notif['notification_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ Close", callback_data="close_notif")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"📬 *Notifications* ({len(notifications)} total)\n\n_All marked as read_"
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_notification_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to notifications list"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    notifications = get_user_notifications(user_id, unread_only=False, limit=20)
    
    keyboard = []
    for notif in notifications[:10]:
        status = "🆕" if not notif['is_read'] else "✓"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {notif['title'][:40]}",
                callback_data=f"notif_{notif['notification_id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("✅ Mark All Read", callback_data="mark_all_read"),
        InlineKeyboardButton("❌ Close", callback_data="close_notif")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"📬 *Notifications* ({len(notifications)} total)\n\n"
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_close_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close notifications"""
    query = update.callback_query
    await query.answer()
    await query.delete_message()


async def callback_admin_pending_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending subscription requests"""
    query = update.callback_query
    await query.answer()
    
    from src.handlers.subscription_handlers import show_pending_subscriptions_list
    await show_pending_subscriptions_list(update, context)


async def callback_admin_pending_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending payment requests"""
    query = update.callback_query
    await query.answer()
    
    from src.handlers.payment_request_handlers import cmd_pending_requests
    await cmd_pending_requests(update, context)


async def callback_admin_my_notifs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show personal notifications"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    notifications = get_user_notifications(user_id, unread_only=False, limit=20)
    
    if not notifications:
        await query.edit_message_text("📬 No personal notifications.")
        return
    
    keyboard = []
    for notif in notifications[:10]:
        status = "🆕" if not notif['is_read'] else "✓"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {notif['title'][:40]}",
                callback_data=f"notif_{notif['notification_id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("✅ Mark All Read", callback_data="mark_all_read"),
        InlineKeyboardButton("← Back", callback_data="cmd_notifications")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"📬 *My Notifications* ({len(notifications)} total)\n\n"
    text += "Tap a notification to view details."
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

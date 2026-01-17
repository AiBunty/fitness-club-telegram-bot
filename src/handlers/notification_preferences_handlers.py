import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.database.notification_channels_operations import (
    get_user_channels, add_notification_channel, toggle_channel, delete_channel,
    get_notification_preferences, update_notification_preferences, CHANNEL_TYPES
)

logger = logging.getLogger(__name__)

async def cmd_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show notification settings menu"""
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("📧 Email Settings", callback_data="notif_settings_email")],
        [InlineKeyboardButton("📱 SMS Settings", callback_data="notif_settings_sms")],
        [InlineKeyboardButton("🔔 Preferences", callback_data="notif_settings_prefs")],
        [InlineKeyboardButton("❌ Close", callback_data="notif_settings_close")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "⚙️ *Notification Settings*\n\n"
    message += "Manage how you receive notifications:\n\n"
    message += "📧 **Email** - Get updates via email\n"
    message += "📱 **SMS** - Get text message alerts\n"
    message += "🔔 **Preferences** - Choose what to notify you about"
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

async def callback_email_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show email settings"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    channels = get_user_channels(user_id)
    email_channels = [c for c in channels if c['channel_type'] == 'email']
    
    keyboard = []
    
    # Show existing email channels
    for channel in email_channels:
        status = "✅" if channel['is_active'] else "❌"
        verified = "✓" if channel['verified'] else "⚠️"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {channel['channel_address']} {verified}",
                callback_data=f"email_toggle_{channel['channel_id']}"
            ),
            InlineKeyboardButton("🗑", callback_data=f"email_delete_{channel['channel_id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("➕ Add Email", callback_data="email_add")])
    keyboard.append([InlineKeyboardButton("📱 Back", callback_data="notif_settings_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "📧 *Email Settings*\n\n"
    
    if email_channels:
        message += "Your email addresses:\n"
        for i, channel in enumerate(email_channels, 1):
            status = "Active" if channel['is_active'] else "Inactive"
            verified = "Verified" if channel['verified'] else "Not Verified"
            message += f"{i}. {channel['channel_address']} ({status}, {verified})\n"
    else:
        message += "No email addresses added yet.\n"
    
    message += "\nAdd an email to receive notifications via email."
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_sms_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show SMS settings"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    channels = get_user_channels(user_id)
    sms_channels = [c for c in channels if c['channel_type'] == 'sms']
    
    keyboard = []
    
    # Show existing SMS channels
    for channel in sms_channels:
        status = "✅" if channel['is_active'] else "❌"
        verified = "✓" if channel['verified'] else "⚠️"
        # Hide full number for privacy
        masked_number = channel['channel_address'][-4:].rjust(len(channel['channel_address']), '*')
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {masked_number} {verified}",
                callback_data=f"sms_toggle_{channel['channel_id']}"
            ),
            InlineKeyboardButton("🗑", callback_data=f"sms_delete_{channel['channel_id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("➕ Add SMS", callback_data="sms_add")])
    keyboard.append([InlineKeyboardButton("📱 Back", callback_data="notif_settings_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "📱 *SMS Settings*\n\n"
    
    if sms_channels:
        message += "Your phone numbers:\n"
        for i, channel in enumerate(sms_channels, 1):
            status = "Active" if channel['is_active'] else "Inactive"
            verified = "Verified" if channel['verified'] else "Not Verified"
            masked_number = channel['channel_address'][-4:].rjust(len(channel['channel_address']), '*')
            message += f"{i}. {masked_number} ({status}, {verified})\n"
    else:
        message += "No phone numbers added yet.\n"
    
    message += "\nAdd a phone number to receive SMS notifications."
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_preferences_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show notification preferences"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    prefs = get_notification_preferences(user_id)
    
    keyboard = []
    
    # Create toggles for each notification type
    notification_types = {
        'points_awarded': '✨ Points Awarded',
        'attendance_approved': '✅ Attendance Approved',
        'payment_due': '💳 Payment Due',
        'membership_expired': '❌ Membership Expired',
        'achievement_unlocked': '🏆 Achievement Unlocked',
        'challenge_reminder': '🔔 Challenge Reminder',
        'leaderboard_update': '📊 Leaderboard Update',
        'daily_reminder': '📱 Daily Reminder'
    }
    
    for key, label in notification_types.items():
        status = "✅" if prefs.get(key, False) else "❌"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {label}",
                callback_data=f"pref_toggle_{key}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("📱 Back", callback_data="notif_settings_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "🔔 *Notification Preferences*\n\n"
    message += "Choose which notifications you want to receive:\n\n"
    
    for key, label in notification_types.items():
        status = "✅ Enabled" if prefs.get(key, False) else "❌ Disabled"
        message += f"{label}: {status}\n"
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_toggle_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle a notification preference"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    pref_type = query.data.split("_")[2]
    
    prefs = get_notification_preferences(user_id)
    prefs[pref_type] = not prefs.get(pref_type, False)
    
    update_notification_preferences(user_id, prefs)
    
    await query.answer(f"✅ Preference updated", show_alert=False)
    
    # Refresh preferences screen
    await callback_preferences_settings(update, context)

async def callback_email_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for adding email address"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    context.user_data['adding_email'] = True
    
    await query.edit_message_text(
        text="📧 *Add Email Address*\n\n"
             "Please send your email address to add it to your notification channels.\n\n"
             "_Send /cancel to abandon_",
        parse_mode="Markdown"
    )

async def callback_sms_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for adding phone number"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    context.user_data['adding_sms'] = True
    
    await query.edit_message_text(
        text="📱 *Add Phone Number*\n\n"
             "Please send your phone number (Indian format: 10 digits) to add SMS notifications.\n\n"
             "_Send /cancel to abandon_",
        parse_mode="Markdown"
    )

async def callback_toggle_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle channel active/inactive"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    parts = query.data.split("_")
    channel_type = parts[0]  # email or sms
    channel_id = int(parts[2])
    
    channels = get_user_channels(user_id)
    channel = next((c for c in channels if c['channel_id'] == channel_id), None)
    
    if channel:
        toggle_channel(channel_id, not channel['is_active'])
        new_status = "enabled" if not channel['is_active'] else "disabled"
        await query.answer(f"✅ Channel {new_status}", show_alert=False)
        
        # Refresh settings
        if channel_type == 'email':
            await callback_email_settings(update, context)
        else:
            await callback_sms_settings(update, context)

async def callback_delete_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a notification channel"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    parts = query.data.split("_")
    channel_type = parts[0]  # email or sms
    channel_id = int(parts[2])
    
    delete_channel(channel_id)
    await query.answer("✅ Channel deleted", show_alert=False)
    
    # Refresh settings
    if channel_type == 'email':
        await callback_email_settings(update, context)
    else:
        await callback_sms_settings(update, context)

async def callback_settings_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to settings menu"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📧 Email Settings", callback_data="notif_settings_email")],
        [InlineKeyboardButton("📱 SMS Settings", callback_data="notif_settings_sms")],
        [InlineKeyboardButton("🔔 Preferences", callback_data="notif_settings_prefs")],
        [InlineKeyboardButton("❌ Close", callback_data="notif_settings_close")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "⚙️ *Notification Settings*\n\n"
    message += "Manage how you receive notifications:\n\n"
    message += "📧 **Email** - Get updates via email\n"
    message += "📱 **SMS** - Get text message alerts\n"
    message += "🔔 **Preferences** - Choose what to notify you about"
    
    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def callback_settings_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close settings"""
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    context.user_data.clear()

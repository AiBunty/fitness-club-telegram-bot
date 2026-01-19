"""
User and admin handlers for Events: list events, register, and admin notifications
This initial implementation supports:
- Listing active events to users
- Register button (free: immediate confirm, paid: create receivable and notify admin)
- Admin receives a notification with approve button to confirm registration
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from src.database.event_operations import get_active_events, register_for_event, get_event
from src.database.payment_approvals import confirm_event_registration
from src.config import SUPER_ADMIN_USER_ID

logger = logging.getLogger(__name__)


async def cmd_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List active events to the user"""
    events = get_active_events()
    if not events:
        await update.message.reply_text("No active events right now.")
        return

    for ev in events[:10]:
        text = f"*{ev['title']}*\n\n{ev.get('description','')}\n"
        if ev.get('is_paid'):
            text += f"\nPrice: ₹{float(ev.get('price') or 0):.2f}\n"
        else:
            text += "\nFree event\n"

        keyboard = [
            [InlineKeyboardButton("Register", callback_data=f"event_register:{ev['event_id']}")]
        ]

        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


async def callback_event_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    event_id = int(query.data.split(":")[1])

    event = get_event(event_id)
    if not event:
        await query.edit_message_text("❌ Event not found")
        return

    reg = register_for_event(user_id, event_id)
    if not reg:
        await query.edit_message_text("❌ Could not register you for this event. Try again later.")
        return

    if not event.get('is_paid'):
        await query.edit_message_text("✅ You are successfully registered for this event. See you there!")
        return

    # Paid event -> notify admin for approval and show pending message
    await query.edit_message_text("✅ Registration created and awaiting payment/approval. Admin will confirm shortly.")

    # Notify super admin with approve button
    try:
        if SUPER_ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Approve Registration", callback_data=f"event_reg_approve:{reg['registration_id']}")]]
            await context.bot.send_message(
                chat_id=int(SUPER_ADMIN_USER_ID),
                text=(f"🔔 New event registration pending\nEvent: {event['title']}\nUser: {user_id}\nRegistration ID: {reg['registration_id']}"),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.debug(f"Could not notify admin about event registration {reg.get('registration_id')}: {e}")


async def callback_event_reg_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id
    reg_id = int(query.data.split(":")[1])

    result = confirm_event_registration(reg_id, admin_id)
    if result:
        await query.edit_message_text(f"✅ Registration {reg_id} confirmed.")
    else:
        await query.edit_message_text(f"❌ Failed to confirm registration {reg_id}.")


def get_event_handlers():
    return [
        CommandHandler('events', cmd_events),
        CallbackQueryHandler(callback_event_register, pattern='^event_register:'),
        CallbackQueryHandler(callback_event_reg_approve, pattern='^event_reg_approve:'),
    ]

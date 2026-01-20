import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from typing import List, Dict
from datetime import datetime

from src.utils.auth import is_admin
from src.utils.invoice import generate_invoice_pdf
from src.utils.invoice_store import save_invoice
from src.config import GYM_PROFILE
from src.database.ar_operations import create_receivable

logger = logging.getLogger(__name__)

INV_ENTER_USER, INV_ADD_ITEM_NAME, INV_ADD_ITEM_AMOUNT, INV_REVIEW = range(4)


async def cmd_create_invoice_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start invoice creation: present user selection options (Search, Manual entry, Cancel)."""
    query = update.callback_query
    if query:
        await query.answer()
        admin_id = query.from_user.id
    else:
        admin_id = update.effective_user.id

    if not is_admin(admin_id):
        if query:
            await query.edit_message_text("❌ Admin access only.")
        else:
            await update.message.reply_text("❌ Admin access only.")
        return ConversationHandler.END

    context.user_data['invoice'] = {'admin_id': admin_id, 'items': []}

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search User", callback_data="inv_search_user")],
        [InlineKeyboardButton("⌨️ Enter Telegram ID Manually", callback_data="inv_manual_entry")],
        [InlineKeyboardButton("⬅ Cancel", callback_data="inv_cancel")],
    ])

    if query:
        await query.edit_message_text("👤 Select User for Invoice", reply_markup=kb)
    else:
        await update.message.reply_text("👤 Select User for Invoice", reply_markup=kb)
    return INV_ENTER_USER


async def inv_enter_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(update.message.text.strip())
        context.user_data['invoice']['user_id'] = uid
        await update.message.reply_text("✏️ Enter item name (first item):")
        return INV_ADD_ITEM_NAME
    except Exception:
        await update.message.reply_text("❌ Please enter a valid numeric Telegram ID.")
        return INV_ENTER_USER


async def inv_search_user_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔎 Type name, username, or part of name:")
    return 'INV_SEARCH_QUERY'


async def inv_search_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Admin typed search term
    try:
        term = update.message.text.strip()
        from src.database.user_operations import search_users
        results = search_users(term, limit=10, offset=0)
        if not results:
            await update.message.reply_text("No users found. Try a different query.")
            return 'INV_SEARCH_QUERY'

        # Build list with Select buttons
        buttons = []
        for row in results:
            uid = row.get('user_id')
            uname = row.get('telegram_username') or ''
            fullname = row.get('full_name') or ''
            text = f"{fullname} ({'@'+uname if uname else ''})\nID: {uid}"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Select", callback_data=f"inv_select_{uid}")]])
            await update.message.reply_text(text, reply_markup=kb)

        # Add pagination note if needed
        if len(results) == 10:
            await update.message.reply_text("Showing first 10 results. Refine search or try pagination later.")

        return INV_REVIEW
    except Exception as e:
        await update.message.reply_text("Error searching users. Try again.")
        return INV_ENTER_USER


async def inv_select_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        uid = int(query.data.split("_")[-1])
        from src.database.user_operations import get_user
        user = get_user(uid)
        if not user:
            await query.edit_message_text("❌ User not found or no longer exists.")
            return ConversationHandler.END

        # Store selected user id and confirm
        context.user_data['invoice']['user_id'] = uid
        await query.edit_message_text(f"User selected: {user.get('full_name','Unknown')} ({uid})")

        # Continue to item entry
        await context.bot.send_message(chat_id=query.from_user.id, text="✏️ Enter item name (first item):")
        return INV_ADD_ITEM_NAME
    except Exception as e:
        await query.edit_message_text("❌ Error selecting user. Try again.")
        return ConversationHandler.END


async def inv_add_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("❌ Item name cannot be empty. Try again:")
        return INV_ADD_ITEM_NAME
    context.user_data['invoice']['current_item'] = {'name': name}
    await update.message.reply_text("💵 Enter amount for this item:")
    return INV_ADD_ITEM_AMOUNT


async def inv_add_item_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amt = float(update.message.text.strip())
        if amt <= 0:
            await update.message.reply_text("❌ Amount must be positive. Try again:")
            return INV_ADD_ITEM_AMOUNT
        item = context.user_data['invoice'].pop('current_item')
        item['amount'] = amt
        context.user_data['invoice']['items'].append(item)

        # Show review and options
        items = context.user_data['invoice']['items']
        lines = "\n".join([f"• {i['name']}: ₹{i['amount']:.2f}" for i in items])
        total = sum(i['amount'] for i in items)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Another Item", callback_data="inv_add_another")],
            [InlineKeyboardButton("📤 Send Bill for Payment", callback_data="inv_send")],
            [InlineKeyboardButton("❌ Cancel", callback_data="inv_cancel")],
        ])
        await update.message.reply_text(f"🧾 Current Items:\n{lines}\n\nTotal: ₹{total:.2f}", reply_markup=kb)
        return INV_REVIEW
    except Exception:
        await update.message.reply_text("❌ Enter a valid amount (e.g., 1500).")
        return INV_ADD_ITEM_AMOUNT


async def inv_review_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == 'inv_add_another':
        await query.edit_message_text("✏️ Enter item name:")
        return INV_ADD_ITEM_NAME
    elif data == 'inv_send':
        inv = context.user_data['invoice']
        user_id = inv['user_id']
        items: List[Dict] = inv.get('items', [])
        total = sum(i['amount'] for i in items)

        # Generate invoice id (integer timestamp)
        invoice_id = int(datetime.utcnow().timestamp())
        invoice_no = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{invoice_id % 10000:04d}"
        payload = {
            'invoice_id': invoice_id,
            'invoice_no': invoice_no,
            'date': datetime.utcnow().strftime('%d %b %Y'),
            'billed_to': {'name': '', 'telegram_id': user_id},
            'items': items,
            'total': total,
            'status': 'UNPAID'
        }

        # Save invoice to lightweight store
        save_invoice(invoice_id, payload)

        # Create receivable record referencing invoice id
        receivable = create_receivable(user_id, 'invoice', invoice_id, bill_amount=total, discount_amount=0.0, final_amount=total)

        # Generate PDF and send to user
        pdf_buf = generate_invoice_pdf(payload, GYM_PROFILE)
        try:
            await context.bot.send_document(chat_id=user_id, document=pdf_buf, filename=f"invoice_{invoice_no}.pdf")
        except Exception as e:
            logger.debug(f"Could not send invoice PDF to user {user_id}: {e}")

        # Send text summary with buttons
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Pay Bill", callback_data=f"invoice_pay_{invoice_id}"), InlineKeyboardButton("❌ Reject Bill", callback_data=f"invoice_reject_{invoice_id}")]
        ])
        await query.edit_message_text(f"✅ Invoice {invoice_no} sent to user {user_id}", reply_markup=None)
        await context.bot.send_message(chat_id=user_id, text=f"You have received Invoice {invoice_no} for ₹{total:.2f}", reply_markup=keyboard)

        return ConversationHandler.END
    else:
        await query.edit_message_text("❌ Invoice creation cancelled.")
        return ConversationHandler.END


def get_invoice_conversation_handler():
    return ConversationHandler(
        entry_points=[
            # Triggered from admin menu via callback
            # CallbackQueryHandler(cmd_create_invoice_start, pattern="^cmd_create_invoice$")
        ],
        states={
            INV_ENTER_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, inv_enter_user)],
            INV_ADD_ITEM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, inv_add_item_name)],
            INV_ADD_ITEM_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, inv_add_item_amount)],
            INV_REVIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, inv_review_actions)],
        },
        fallbacks=[],
        per_message=False
    )

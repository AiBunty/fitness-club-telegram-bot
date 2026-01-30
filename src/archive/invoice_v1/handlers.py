import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputFile
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from src.invoices import state
from src.invoices.utils import search_users, format_invoice_text
from src.invoices.store import create_invoice
from src.invoices.pdf import generate_invoice_pdf_bytes
from src.invoices.store import get_invoice, delete_invoice, mark_invoice_paid

logger = logging.getLogger(__name__)


def _menu_keyboard():
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton('➕ Create Invoice', callback_data='inv_create')],
        [InlineKeyboardButton('❌ Cancel', callback_data='inv_cancel')]
    ])
    return kb


async def invoice_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    # lazy import to avoid importing DB-heavy modules at module import time
    from src.utils.auth import is_admin_id
    logger.info(f"[INVOICE] entry_point admin_id={user_id}")
    await query.answer()
    if not is_admin_id(user_id):
        await query.edit_message_text('❌ Admins only.')
        return
    await query.edit_message_text('🧾 Invoice Menu', reply_markup=_menu_keyboard())
    return


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text('Cancelled.')
    return ConversationHandler.END


async def inv_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['invoice_flow'] = {'items': []}
    await query.edit_message_text('Search user by Name / Username / Telegram ID:')
    return state.SEARCH_USER


async def handle_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # message with search term
    term = update.message.text.strip()
    results = search_users(term)
    if not results:
        await update.message.reply_text('❌ No users found. Try again.')
        return state.SEARCH_USER

    kb = []
    for u in results:
        title = f"{u.get('full_name')} | @{u.get('username','')} | {u.get('user_id')}"
        kb.append([InlineKeyboardButton(title, callback_data=f"inv_user_{u.get('user_id')}")])
    kb.append([InlineKeyboardButton('❌ Cancel', callback_data='inv_cancel')])
    await update.message.reply_text('Select user:', reply_markup=InlineKeyboardMarkup(kb))
    return state.SELECT_USER


async def handle_user_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = int(data.split('_')[-1])
    context.user_data['invoice_flow']['user_id'] = user_id
    logger.info(f"[INVOICE] user_selected admin={query.from_user.id} user_id={user_id}")
    await query.edit_message_text('Enter Item Name:')
    return state.ITEM_NAME


async def item_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text('❌ Name required. Try again:')
        return state.ITEM_NAME
    context.user_data.setdefault('invoice_flow', {}).setdefault('current_item', {})['name'] = name
    await update.message.reply_text('Enter Rate (number > 0):')
    return state.ITEM_RATE


async def item_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rate = float(update.message.text.strip())
        if rate <= 0:
            raise ValueError()
    except Exception:
        await update.message.reply_text('❌ Invalid rate. Enter a number > 0:')
        return state.ITEM_RATE
    context.user_data['invoice_flow']['current_item']['rate'] = rate
    await update.message.reply_text('Enter Quantity (integer > 0):')
    return state.ITEM_QTY


async def item_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        qty = int(update.message.text.strip())
        if qty <= 0:
            raise ValueError()
    except Exception:
        await update.message.reply_text('❌ Invalid quantity. Enter integer > 0:')
        return state.ITEM_QTY
    context.user_data['invoice_flow']['current_item']['qty'] = qty
    await update.message.reply_text('Enter Discount % (0-80):')
    return state.ITEM_DISC


async def item_disc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        disc = float(update.message.text.strip())
        if disc < 0 or disc > 80:
            raise ValueError()
    except Exception:
        await update.message.reply_text('❌ Invalid discount. Enter 0–80:')
        return state.ITEM_DISC
    item = context.user_data['invoice_flow'].pop('current_item')
    item['disc'] = disc
    base = item['rate'] * item['qty']
    discount = base * (disc/100)
    taxable = base - discount
    item['line_total'] = round(taxable, 2)
    context.user_data['invoice_flow']['items'].append(item)
    logger.info(f"[INVOICE] item_added admin={update.effective_user.id} item={item.get('name')} qty={item.get('qty')} rate={item.get('rate')}")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton('➕ Add Another Item', callback_data='inv_add_another')],
        [InlineKeyboardButton('➡ Finish Items', callback_data='inv_finish_items')],
        [InlineKeyboardButton('❌ Cancel', callback_data='inv_cancel')]
    ])
    await update.message.reply_text('Item recorded. Add another or finish.', reply_markup=kb)
    return state.ITEM_AFTER


async def item_after_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'inv_add_another':
        await query.edit_message_text('Enter Item Name:')
        return state.ITEM_NAME
    else:
        # finish items
        await query.edit_message_text('Enter Shipping / Delivery Charges (0 if none):')
        return state.SHIPPING


async def handle_shipping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ship = float(update.message.text.strip())
        if ship < 0:
            raise ValueError()
    except Exception:
        await update.message.reply_text('❌ Invalid shipping. Enter 0 or positive number:')
        return state.SHIPPING
    context.user_data['invoice_flow']['shipping'] = ship
    # Calculate totals
    items = context.user_data['invoice_flow']['items']
    subtotal = sum([it.get('line_total', 0) for it in items])
    # For simplicity GST = 18% of subtotal
    gst = round(subtotal * 0.18, 2)
    total = round(subtotal + gst + ship, 2)
    context.user_data['invoice_flow'].update({'subtotal': subtotal, 'gst': gst, 'total': total})

    text = f"Items subtotal: {subtotal}\nShipping: {ship}\nGST (18%): {gst}\n\nFinal Total: {total}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton('📤 Send Invoice', callback_data='inv_send')],
        [InlineKeyboardButton('❌ Cancel', callback_data='inv_cancel')]
    ])
    await update.message.reply_text(text, reply_markup=kb)
    return state.CONFIRM_SEND


async def handle_send_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    flow = context.user_data.get('invoice_flow', {})
    payload = {
        'user_id': flow.get('user_id'),
        'items': flow.get('items', []),
        'subtotal': flow.get('subtotal', 0),
        'gst': flow.get('gst', 0),
        'shipping': flow.get('shipping', 0),
        'total': flow.get('total', 0)
    }
    invoice = create_invoice(payload)
    logger.info(f"[INVOICE] invoice_sent id={invoice.get('invoice_id')} admin={query.from_user.id}")

    # Generate PDF and send to user
    pdf_bio = generate_invoice_pdf_bytes(invoice)
    caption = format_invoice_text(invoice)

    # Send to user
    try:
        await context.bot.send_document(chat_id=invoice.get('user_id'), document=InputFile(pdf_bio, filename=f"{invoice.get('invoice_id')}.pdf"), caption=caption)
    except Exception as e:
        logger.error(f"[INVOICE] failed to send invoice to user {invoice.get('user_id')}: {e}")

    # Send to all admins
    try:
        from src.utils.auth import list_admin_ids
        admin_ids = list_admin_ids()
        for aid in admin_ids:
            try:
                await context.bot.send_document(chat_id=aid, document=InputFile(pdf_bio, filename=f"{invoice.get('invoice_id')}.pdf"), caption=caption)
            except Exception as e:
                logger.error(f"[INVOICE] failed to send invoice copy to admin {aid}: {e}")
    except Exception as e:
        logger.error(f"[INVOICE] could not enumerate admin ids: {e}")

    await query.edit_message_text(f"Invoice {invoice.get('invoice_id')} created and sent.")
    return ConversationHandler.END


async def admin_resend_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_')
    invoice_id = parts[-1]
    inv = get_invoice(invoice_id)
    if not inv:
        await query.edit_message_text(f"❌ Invoice {invoice_id} not found")
        return
    pdf_bio = generate_invoice_pdf_bytes(inv)
    caption = format_invoice_text(inv)
    try:
        await context.bot.send_document(chat_id=inv.get('user_id'), document=InputFile(pdf_bio, filename=f"{invoice_id}.pdf"), caption=caption)
        logger.info(f"[INVOICE] invoice_resent id={invoice_id} by_admin={query.from_user.id}")
        await query.edit_message_text(f"✅ Invoice {invoice_id} resent to user.")
    except Exception as e:
        logger.error(f"[INVOICE] failed to resend invoice {invoice_id}: {e}")
        await query.edit_message_text(f"❌ Failed to resend invoice {invoice_id}.")


async def admin_delete_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    invoice_id = query.data.split('_')[-1]
    ok = delete_invoice(invoice_id)
    if ok:
        await query.edit_message_text(f"🗑️ Invoice {invoice_id} deleted.")
    else:
        await query.edit_message_text(f"❌ Invoice {invoice_id} not found.")


async def invoice_payment_approved_hook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hook triggered when payment is approved externally. Callback data: inv_paid_<INV-ID>"""
    query = update.callback_query
    await query.answer()
    invoice_id = query.data.split('_')[-1]
    ok = mark_invoice_paid(invoice_id)
    if not ok:
        await query.edit_message_text(f"❌ Invoice {invoice_id} not found.")
        return
    inv = get_invoice(invoice_id)
    # Generate receipt and send
    pdf_bio = generate_invoice_pdf_bytes(inv)
    caption = format_invoice_text(inv)
    try:
        await context.bot.send_document(chat_id=inv.get('user_id'), document=InputFile(pdf_bio, filename=f"{invoice_id}_receipt.pdf"), caption=f"Receipt for {invoice_id}")
        # notify admins
        from src.utils.auth import list_admin_ids
        for aid in list_admin_ids():
            try:
                await context.bot.send_document(chat_id=aid, document=InputFile(pdf_bio, filename=f"{invoice_id}_receipt.pdf"), caption=f"Receipt for {invoice_id}")
            except Exception as e:
                logger.error(f"[INVOICE] failed to send receipt to admin {aid}: {e}")
        logger.info(f"[INVOICE] receipt_sent id={invoice_id}")
        await query.edit_message_text(f"✅ Invoice {invoice_id} marked as PAID and receipt sent.")
    except Exception as e:
        logger.error(f"[INVOICE] failed to send receipt for {invoice_id}: {e}")
        await query.edit_message_text(f"❌ Failed to send receipt for {invoice_id}.")


def get_invoice_conversation_handler():
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(invoice_entry, pattern='^cmd_invoices$'), CallbackQueryHandler(inv_create_start, pattern='^inv_create$')],
        states={
            state.SEARCH_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_search)],
            state.SELECT_USER: [CallbackQueryHandler(handle_user_select, pattern='^inv_user_')],
            state.ITEM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, item_name)],
            state.ITEM_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, item_rate)],
            state.ITEM_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, item_qty)],
            state.ITEM_DISC: [MessageHandler(filters.TEXT & ~filters.COMMAND, item_disc)],
            state.ITEM_AFTER: [CallbackQueryHandler(item_after_choice, pattern='^inv_(add_another|finish_items)$')],
            state.SHIPPING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_shipping)],
            state.CONFIRM_SEND: [CallbackQueryHandler(handle_send_invoice, pattern='^inv_send$')]
        },
        fallbacks=[CallbackQueryHandler(_cancel, pattern='^inv_cancel$')],
        conversation_timeout=600,
        per_chat=True,
        per_user=True
    )
    return conv

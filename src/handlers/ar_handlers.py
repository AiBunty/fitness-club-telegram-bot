import logging
from typing import List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters

from src.utils.auth import is_admin
from src.database.ar_operations import (
    create_receivable, create_transactions, update_receivable_status,
    get_receivable_breakdown, get_overdue_receivables
)

logger = logging.getLogger(__name__)

# Conversation states
AR_ENTER_USER, AR_ENTER_BILL, AR_ADD_LINE_METHOD, AR_ADD_LINE_AMOUNT, AR_REVIEW_LINES = range(5)


async def ar_start_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    context.user_data['ar'] = {'admin_id': admin_id, 'lines': []}
    text = "👤 Enter the user's Telegram ID to record payment:"
    if query:
        await query.edit_message_text(text)
    else:
        await update.message.reply_text(text)
    return AR_ENTER_USER


async def ar_enter_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid_str = update.message.text.strip()
        uid = int(uid_str)
        context.user_data['ar']['user_id'] = uid
        await update.message.reply_text("💵 Enter the total bill amount (after discount):")
        return AR_ENTER_BILL
    except Exception:
        await update.message.reply_text("❌ Please enter a valid numeric Telegram ID.")
        return AR_ENTER_USER


async def ar_enter_bill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amt = float(update.message.text.strip())
        if amt <= 0:
            await update.message.reply_text("❌ Amount must be greater than 0. Try again:")
            return AR_ENTER_BILL
        context.user_data['ar']['final_amount'] = amt
        # Start adding lines
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💵 Cash", callback_data="ar_method_cash"), InlineKeyboardButton("📱 UPI", callback_data="ar_method_upi")],
            [InlineKeyboardButton("💳 Card", callback_data="ar_method_card"), InlineKeyboardButton("🏦 Bank", callback_data="ar_method_bank")],
            [InlineKeyboardButton("❌ Cancel", callback_data="ar_cancel")]
        ])
        await update.message.reply_text("➕ Select first payment method:", reply_markup=kb)
        return AR_ADD_LINE_METHOD
    except Exception:
        await update.message.reply_text("❌ Enter a valid amount (e.g., 7000).")
        return AR_ENTER_BILL


async def ar_select_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.replace("ar_method_", "")
    context.user_data['ar']['current_method'] = method
    await query.edit_message_text(f"💰 Enter amount for {method.upper()}:")
    return AR_ADD_LINE_AMOUNT


async def ar_add_line_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amt = float(update.message.text.strip())
        if amt <= 0:
            await update.message.reply_text("❌ Amount must be greater than 0. Try again:")
            return AR_ADD_LINE_AMOUNT
        line = {
            'method': context.user_data['ar']['current_method'],
            'amount': amt,
            'reference': None,
        }
        context.user_data['ar']['lines'].append(line)
        # Review current lines
        total = sum(l['amount'] for l in context.user_data['ar']['lines'])
        remaining = max(context.user_data['ar']['final_amount'] - total, 0)
        lines_text = "\n".join([f"• {l['method'].upper()}: ₹{l['amount']:.2f}" for l in context.user_data['ar']['lines']])
        text = (
            f"🧾 Current lines:\n{lines_text or '—'}\n\n"
            f"Subtotal: ₹{total:.2f}\nRemaining: ₹{remaining:.2f}\n\n"
            "Choose next action:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Another Payment", callback_data="ar_add_line")],
            [InlineKeyboardButton("✅ Confirm & Save", callback_data="ar_confirm_all")],
            [InlineKeyboardButton("❌ Cancel", callback_data="ar_cancel")]
        ])
        await update.message.reply_text(text, reply_markup=kb)
        return AR_REVIEW_LINES
    except Exception:
        await update.message.reply_text("❌ Enter a valid amount.")
        return AR_ADD_LINE_AMOUNT


async def ar_review_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == 'ar_add_line':
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💵 Cash", callback_data="ar_method_cash"), InlineKeyboardButton("📱 UPI", callback_data="ar_method_upi")],
            [InlineKeyboardButton("💳 Card", callback_data="ar_method_card"), InlineKeyboardButton("🏦 Bank", callback_data="ar_method_bank")],
            [InlineKeyboardButton("❌ Cancel", callback_data="ar_cancel")]
        ])
        await query.edit_message_text("➕ Select payment method:", reply_markup=kb)
        return AR_ADD_LINE_METHOD
    elif data == 'ar_confirm_all':
        admin_id = context.user_data['ar']['admin_id']
        user_id = context.user_data['ar']['user_id']
        final_amount = context.user_data['ar']['final_amount']
        lines = context.user_data['ar']['lines']
        if not lines:
            await query.edit_message_text("❌ No payments added.")
            return ConversationHandler.END
        # Create receivable and transactions
        receivable = create_receivable(user_id, 'subscription', None, bill_amount=final_amount, discount_amount=0.0, final_amount=final_amount)
        rid = receivable.get('receivable_id')
        create_transactions(rid, lines, admin_id)
        updated = update_receivable_status(rid)
        breakdown = get_receivable_breakdown(rid)
        methods = breakdown.get('methods', {})
        method_text = "\n".join([f"• {m.upper()}: ₹{tot:.2f}" for m, tot in methods.items()])
        await query.edit_message_text(
            f"✅ Saved payment for user {user_id}\n\n"
            f"Final Bill: ₹{final_amount:.2f}\n"
            f"Status: {updated.get('status','pending').upper()}\n\n"
            f"Breakdown:\n{method_text or '—'}"
        )
        # If this receivable corresponds to an invoice and is fully paid, generate and send a receipt
        try:
            from src.database.ar_operations import get_receivable_by_source
            from src.utils.invoice_store import load_invoice
            from src.utils.invoice import generate_receipt_pdf
            rec = receivable or {}
            if rec.get('receivable_type') == 'invoice' and updated.get('status') == 'paid':
                source_id = rec.get('source_id')
                inv = load_invoice(source_id)
                if inv:
                    # Build receipt payload
                    receipt = {
                        'receipt_no': f"RCT-{datetime.now().strftime('%Y%m%d')}-{rid}",
                        'date': datetime.now().strftime('%d %b %Y'),
                        'billed_to': inv.get('billed_to', {}),
                        'methods': methods,
                        'total_paid': breakdown.get('received_total', 0.0),
                        'balance': breakdown.get('balance', 0.0),
                        'invoice_ref': inv.get('invoice_no')
                    }
                    pdf_buf = generate_receipt_pdf(receipt, __import__('src.config', fromlist=['GYM_PROFILE']).GYM_PROFILE)
                    try:
                        await context.bot.send_document(chat_id=user_id, document=pdf_buf, filename=f"receipt_{receipt['receipt_no']}.pdf")
                        await context.bot.send_message(chat_id=user_id, text="✅ Payment received. Receipt sent.")
                    except Exception as e:
                        logger.debug(f"Could not send receipt PDF to user {user_id}: {e}")
        except Exception:
            logger.debug("No invoice receipt generated or an error occurred.")
        return ConversationHandler.END
    elif data == 'ar_cancel':
        await query.edit_message_text("❌ Payment recording cancelled.")
        return ConversationHandler.END


async def ar_export_overdue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    admin_id = (query.from_user.id if query else update.effective_user.id)
    if not is_admin(admin_id):
        if query:
            await query.edit_message_text("❌ Admin access only.")
        else:
            await update.message.reply_text("❌ Admin access only.")
        return
    overdue = get_overdue_receivables()
    # Build CSV in-memory
    import io, csv
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["User Name", "Telegram ID", "Final Bill", "Cash", "UPI", "Card", "Bank", "Total Received", "Total Due", "Due Date"])
    for r in overdue:
        rid = r['receivable_id']
        breakdown = get_receivable_breakdown(rid)
        methods = breakdown.get('methods', {})
        total_recv = breakdown.get('received_total', 0.0)
        total_due = float(r['final_amount']) - float(total_recv)
        writer.writerow([
            r.get('full_name') or '', r.get('uid'), f"{float(r['final_amount']):.2f}",
            f"{float(methods.get('cash',0)): .2f}", f"{float(methods.get('upi',0)): .2f}",
            f"{float(methods.get('card',0)): .2f}", f"{float(methods.get('bank',0)): .2f}",
            f"{float(total_recv):.2f}", f"{float(total_due):.2f}", r.get('due_date')
        ])
    data = buffer.getvalue().encode('utf-8')
    buffer.close()
    from datetime import datetime
    filename = f"overdue_receivables_{datetime.now().strftime('%Y%m%d')}.csv"
    await (query.message.reply_document if query else update.message.reply_document)(
        document=data,
        filename=filename,
        caption="📤 Overdue receivables exported"
    )


async def ar_credit_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple credit summary placeholder: instruct admin to use export for details."""
    query = update.callback_query
    if query:
        await query.answer()
    admin_id = (query.from_user.id if query else update.effective_user.id)
    if not is_admin(admin_id):
        msg = "❌ Admin access only."
        if query:
            await query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return
    text = (
        "💳 Credit Summary\n\n"
        "Use 📤 Export Overdue to download detailed CSV with per-method breakdowns.\n"
        "A detailed dashboard view will be added subsequently."
    )
    if query:
        await query.edit_message_text(text)
    else:
        await update.message.reply_text(text)


def get_ar_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(ar_start_record, pattern="^ar_record_payment$")
        ],
        states={
            AR_ENTER_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ar_enter_user)],
            AR_ENTER_BILL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ar_enter_bill)],
            AR_ADD_LINE_METHOD: [CallbackQueryHandler(ar_select_method, pattern="^ar_method_")],
            AR_ADD_LINE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ar_add_line_amount)],
            AR_REVIEW_LINES: [CallbackQueryHandler(ar_review_actions, pattern="^(ar_add_line|ar_confirm_all|ar_cancel)$")],
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
        conversation_timeout=600,  # 10 minutes timeout to prevent stuck states
        per_message=False,
        per_chat=True,  # CRITICAL: Isolate per chat for 200+ users
        per_user=True   # CRITICAL: Isolate per user for admin concurrency
    )

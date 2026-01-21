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
from src.utils.invoice_store import load_invoice
from src.utils.role_notifications import get_moderator_chat_ids

logger = logging.getLogger(__name__)

# Admin guardrails
MAX_DISCOUNT_PERCENT = 80  # Maximum allowed discount percentage

INV_ENTER_USER, INV_ADD_ITEM_NAME, INV_ADD_ITEM_RATE, INV_ADD_ITEM_QUANTITY, INV_ADD_ITEM_DISCOUNT, INV_SHIPPING, INV_REVIEW, INV_SEARCH_QUERY, INV_ITEM_CHOICE, INV_STORE_SEARCH = range(10)


async def cmd_create_invoice_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start invoice creation: present user selection options (Search, Manual entry, Cancel)."""
    logger.info(f"[INVOICE] create_invoice_start ENTERED")
    query = update.callback_query
    if query:
        logger.info(f"[INVOICE] query callback exists")
        await query.answer()
        admin_id = query.from_user.id
        logger.info(f"[CALLBACK] invoice button received from admin={admin_id}")
    else:
        logger.info(f"[INVOICE] query callback is None")
        admin_id = update.effective_user.id
        logger.info(f"[INVOICE] create_invoice handler entered from admin={admin_id}")

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
    try:
        logger.info(f"[INVOICE] inv_search_user_prompt invoked by admin_id={query.from_user.id}")
    except Exception:
        logger.debug("[INVOICE] inv_search_user_prompt invoked (no admin id)")
    await query.edit_message_text("🔎 Type name, username, or part of name:")
    return INV_SEARCH_QUERY


async def inv_search_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Admin typed search term
    logger.info(f"[INVOICE_SEARCH] query_received from user={update.effective_user.id}")
    try:
        term = update.message.text.strip()
        from src.database.user_operations import search_users
        from src.utils.user_registry import search_registry
        
        logger.info(f"[INVOICE_SEARCH] query='{term}'")
        
        # Try DB first
        results = search_users(term, limit=10, offset=0)
        logger.info(f"[INVOICE_SEARCH] db_matches_found={len(results) if results else 0}")
        
        # Fallback to JSON registry if DB returns nothing
        if not results:
            logger.info(f"[INVOICE_SEARCH] db_empty, trying json registry")
            results = search_registry(term, limit=10)
            logger.info(f"[INVOICE_SEARCH] json_matches_found={len(results) if results else 0}")
            if results:
                logger.info(f"[INVOICE_SEARCH] using_json_registry=true")
        
        if not results:
            logger.info("[INVOICE_SEARCH] no_results from db or registry")
            help_msg = (
                "❌ No users found.\n\n"
                "💡 **Search Tips:**\n"
                "• Try a different spelling or partial name\n"
                "• Search by Telegram username (with or without @)\n"
                "• Search by user ID (numeric)\n"
                "• Pending/unapproved users may not appear in some flows\n\n"
                "Try a different query or check user approval status."
            )
            await update.message.reply_text(help_msg, parse_mode='Markdown')
            return INV_SEARCH_QUERY

        # Build list with Select buttons
        logger.info(f"[INVOICE_SEARCH] sending {len(results)} result(s) to admin")
        buttons = []
        for row in results:
            uid = row.get('user_id')
            uname = row.get('telegram_username') or row.get('username') or ''
            fullname = row.get('full_name') or 'Unknown'
            approval = row.get('approval_status', 'unknown')
            
            # Format: Name (@username if exists) \n ID: 123456 | Status
            user_display = f"{fullname}"
            if uname:
                user_display += f" (@{uname})"
            user_display += f"\nID: {uid}"
            
            # Add approval status indicator
            if approval == 'pending':
                user_display += " ⏳ Pending"
            elif approval == 'rejected':
                user_display += " ❌ Rejected"
            elif approval == 'approved':
                user_display += " ✅ Approved"
            
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Select", callback_data=f"inv_select_{uid}")]])
            await update.message.reply_text(user_display, reply_markup=kb)

        # Add pagination note if needed
        if len(results) == 10:
            await update.message.reply_text("Showing first 10 results. Refine search or try pagination later.")

        return INV_SEARCH_QUERY
    except Exception as e:
        await update.message.reply_text("Error searching users. Try again.")
        return INV_SEARCH_QUERY


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
        logger.info(f"[INVOICE_SEARCH] user_selected user_id={uid} by admin={query.from_user.id}")
        await query.edit_message_text(f"User selected: {user.get('full_name','Unknown')} ({uid})")

        # Continue to item choice
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search Store Item", callback_data="inv_store_search")],
            [InlineKeyboardButton("✍️ Enter Custom Item", callback_data="inv_custom_item")],
        ])
        await context.bot.send_message(chat_id=query.from_user.id, text="Choose item entry method:", reply_markup=kb)
        return INV_ITEM_CHOICE
    except Exception as e:
        await query.edit_message_text("❌ Error selecting user. Try again.")
        return ConversationHandler.END


async def inv_add_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("❌ Item name cannot be empty. Try again:")
        return INV_ADD_ITEM_NAME
    context.user_data['invoice']['current_item'] = {'name': name}
    await update.message.reply_text("� Enter rate (per unit):")
    return INV_ADD_ITEM_RATE


async def inv_add_item_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rate input for current item."""
    try:
        rate = float(update.message.text.strip())
        if rate <= 0:
            await update.message.reply_text("❌ Rate must be positive. Try again:")
            return INV_ADD_ITEM_RATE
        context.user_data['invoice']['current_item']['rate'] = rate
        # Default GST from global if not already set (store items have their own)
        if 'gst' not in context.user_data['invoice']['current_item']:
            from src.utils.gst import get_gst_percent, is_gst_enabled
            if is_gst_enabled():
                context.user_data['invoice']['current_item']['gst'] = get_gst_percent()
            else:
                context.user_data['invoice']['current_item']['gst'] = 0
        await update.message.reply_text("🔢 Enter quantity:")
        return INV_ADD_ITEM_QUANTITY
    except Exception:
        await update.message.reply_text("❌ Enter a valid rate (e.g., 1500, 250.50):")
        return INV_ADD_ITEM_RATE


async def inv_add_item_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quantity input and calculate line total."""
    try:
        qty = int(update.message.text.strip())
        if qty <= 0:
            await update.message.reply_text("❌ Quantity must be positive. Try again:")
            return INV_ADD_ITEM_QUANTITY
        
        # Store quantity and ask for discount
        item = context.user_data['invoice']['current_item']
        item['quantity'] = qty
        await update.message.reply_text("💰 Enter discount % (0 if none):")
        return INV_ADD_ITEM_DISCOUNT
    except ValueError:
        await update.message.reply_text("❌ Quantity must be a whole number (e.g., 1, 5, 10):")
        return INV_ADD_ITEM_QUANTITY
    except Exception as e:
        logger.error(f"[INVOICE] Error in quantity handler: {e}")
        await update.message.reply_text("❌ Error processing quantity. Try again:")
        return INV_ADD_ITEM_QUANTITY


async def inv_add_item_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle discount and calculate taxable amount and GST."""
    try:
        disc = float(update.message.text.strip())
        
        # Validation: discount must be 0-100% and <= MAX_DISCOUNT_PERCENT
        if disc < 0:
            await update.message.reply_text("❌ Discount cannot be negative. Please re-enter:")
            return INV_ADD_ITEM_DISCOUNT
        
        if disc > 100:
            await update.message.reply_text("❌ Discount cannot exceed 100%. Please re-enter:")
            return INV_ADD_ITEM_DISCOUNT
        
        if disc > MAX_DISCOUNT_PERCENT:
            await update.message.reply_text(
                f"❌ Discount exceeds allowed limit ({MAX_DISCOUNT_PERCENT}%). Please re-enter:"
            )
            logger.warning(f"[INVOICE] Admin attempted high discount: {disc}%")
            return INV_ADD_ITEM_DISCOUNT
        
        # Log edge cases
        if disc == 100:
            logger.info(f"[INVOICE] 100% discount applied to item")
        elif disc >= 50:
            logger.info(f"[INVOICE] High discount applied: {disc}%")
        
        item = context.user_data['invoice']['current_item']
        rate = item['rate']
        qty = item['quantity']
        gst_pct = item.get('gst', 0)
        
        # Calculate taxable amount
        base = rate * qty
        discount_amt = (base * disc) / 100
        taxable = base - discount_amt
        
        # Apply GST if enabled
        from src.utils.gst import is_gst_enabled, get_gst_mode
        if is_gst_enabled() and gst_pct > 0:
            mode = get_gst_mode()
            logger.info(f"[INVOICE] GST calculation: mode={mode}, percent={gst_pct}, taxable={taxable:.2f}")
            if mode == 'inclusive':
                # GST is already in price, extract it
                gst_amt = taxable - (taxable / (1 + gst_pct / 100))
                line_total = taxable
            else:
                # Exclusive: add GST on top
                gst_amt = (taxable * gst_pct) / 100
                line_total = taxable + gst_amt
        else:
            gst_amt = 0
            line_total = taxable
        
        # Store calculated values
        item['discount_percent'] = disc
        item['taxable_amount'] = taxable
        item['gst_percent'] = gst_pct
        item['gst_amount'] = gst_amt
        item['line_total'] = line_total
        
        context.user_data['invoice']['items'].append(item)
        context.user_data['invoice'].pop('current_item')
        
        # Confirm item added
        await update.message.reply_text(
            f"✅ Item Added:\n"
            f"{item['name']}\n"
            f"Rate: ₹{rate:.2f} × {qty}\n"
            f"Discount: {disc}%\n"
            f"Taxable: ₹{taxable:.2f}\n"
            f"GST ({gst_pct}%): ₹{gst_amt:.2f}\n"
            f"Line Total: ₹{line_total:.2f}"
        )

        # Show current items and next action
        items = context.user_data['invoice']['items']
        lines = "\n".join([f"• {i['name']}: ₹{i['line_total']:.2f}" for i in items])
        subtotal = sum(i['line_total'] for i in items)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Another Item", callback_data="inv_add_another")],
            [InlineKeyboardButton("➡️ Finish Items", callback_data="inv_finish_items")],
            [InlineKeyboardButton("❌ Cancel", callback_data="inv_cancel")],
        ])
        await update.message.reply_text(
            f"🧾 Current Items:\n{lines}\n\nSubtotal: ₹{subtotal:.2f}",
            reply_markup=kb
        )
        return INV_REVIEW
    except ValueError:
        await update.message.reply_text("❌ Enter a valid discount (e.g., 0, 10, 25):")
        return INV_ADD_ITEM_DISCOUNT
    except Exception as e:
        logger.error(f"[INVOICE] Error in discount handler: {e}")
        await update.message.reply_text("❌ Error processing discount. Try again:")
        return INV_ADD_ITEM_DISCOUNT


async def inv_item_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle item entry choice: store search or custom."""
    query = update.callback_query
    await query.answer()
    if query.data == 'inv_store_search':
        await query.edit_message_text("🔍 Search store item by name:")
        return INV_STORE_SEARCH
    else:  # inv_custom_item
        await query.edit_message_text("✏️ Enter item name:")
        return INV_ADD_ITEM_NAME


async def inv_store_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search store items and display results."""
    term = update.message.text.strip()
    from src.utils.store_items import find_items
    results = find_items(term, limit=10)
    if not results:
        await update.message.reply_text('No items found. Try another name or enter custom item.')
        return INV_STORE_SEARCH
    for it in results:
        text = (f"{it.get('name')}\nHSN: {it.get('hsn','')}\n"
                f"MRP: ₹{float(it.get('mrp',0)):.2f}\nGST: {it.get('gst',0)}%")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton('✅ Select', callback_data=f"inv_store_select_{it.get('name')}_{it.get('hsn','')}")]])
        await update.message.reply_text(text, reply_markup=kb)
    return INV_STORE_SEARCH


async def inv_store_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle store item selection."""
    query = update.callback_query
    await query.answer()
    raw = query.data[len('inv_store_select_'):]
    try:
        name, hsn = raw.rsplit('_', 1)
    except Exception:
        name = raw
        hsn = ''
    from src.utils.store_items import load_store_items
    items = load_store_items()
    chosen = None
    for it in items:
        if it.get('name') == name and str(it.get('hsn','')) == hsn:
            chosen = it
            break
    if not chosen:
        await query.edit_message_text('❌ Item not found')
        return ConversationHandler.END
    context.user_data['invoice']['current_item'] = {
        'name': chosen.get('name'),
        'rate': float(chosen.get('mrp',0)),
        'gst': float(chosen.get('gst',0))
    }
    await query.edit_message_text(f"Item selected: {chosen.get('name')}\nRate: ₹{float(chosen.get('mrp',0)):.2f}")
    await context.bot.send_message(chat_id=query.from_user.id, text='🔢 Enter quantity:')
    return INV_ADD_ITEM_QUANTITY


async def inv_finish_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finish adding items and ask for shipping."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🚚 Enter shipping/delivery charge (0 if none):")
    return INV_SHIPPING


async def inv_add_shipping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle shipping and show final summary."""
    try:
        ship = float(update.message.text.strip())
        if ship < 0:
            await update.message.reply_text("❌ Shipping cannot be negative. Try again:")
            return INV_SHIPPING
        context.user_data['invoice']['shipping'] = ship
        
        # Calculate final total
        items = context.user_data['invoice']['items']
        items_total = sum(i['line_total'] for i in items)
        gst_total = sum(i.get('gst_amount', 0) for i in items)
        final_total = items_total + ship
        
        # Show final summary
        lines = "\n".join([f"• {i['name']}: ₹{i['line_total']:.2f}" for i in items])
        summary = (
            f"📋 *Final Invoice Summary*\n\n"
            f"{lines}\n\n"
            f"Items Total: ₹{items_total:.2f}\n"
            f"Shipping: ₹{ship:.2f}\n"
        )
        if gst_total > 0:
            summary += f"GST Included: ₹{gst_total:.2f}\n"
        summary += f"\n💵 *Final Amount: ₹{final_total:.2f}*"
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Send Bill for Payment", callback_data="inv_send")],
            [InlineKeyboardButton("✏️ Edit Items", callback_data="inv_edit")],
            [InlineKeyboardButton("❌ Cancel", callback_data="inv_cancel")],
        ])
        await update.message.reply_text(summary, reply_markup=kb, parse_mode='Markdown')
        return INV_REVIEW
    except ValueError:
        await update.message.reply_text("❌ Enter a valid amount (e.g., 50, 100):")
        return INV_SHIPPING
    except Exception as e:
        logger.error(f"[INVOICE] Error in shipping handler: {e}")
        await update.message.reply_text("❌ Error processing shipping. Try again:")
        return INV_SHIPPING


async def inv_review_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == 'inv_add_another':
        # Show item choice again
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search Store Item", callback_data="inv_store_search")],
            [InlineKeyboardButton("✍️ Enter Custom Item", callback_data="inv_custom_item")],
        ])
        await query.edit_message_text("Choose item entry method:", reply_markup=kb)
        return INV_ITEM_CHOICE
    elif data == 'inv_finish_items':
        await inv_finish_items(update, context)
        return INV_SHIPPING
    elif data == 'inv_edit':
        # Clear items and restart
        context.user_data['invoice']['items'] = []
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search Store Item", callback_data="inv_store_search")],
            [InlineKeyboardButton("✍️ Enter Custom Item", callback_data="inv_custom_item")],
        ])
        await query.edit_message_text("Choose item entry method:", reply_markup=kb)
        return INV_ITEM_CHOICE
    elif data == 'inv_send':
        inv = context.user_data['invoice']
        user_id = inv['user_id']
        items: List[Dict] = inv.get('items', [])
        shipping = float(inv.get('shipping', 0))
        
        # Calculate totals
        items_total = sum(i['line_total'] for i in items)
        gst_total = sum(i.get('gst_amount', 0) for i in items)
        final_total = items_total + shipping

        # Generate invoice id (integer timestamp)
        invoice_id = int(datetime.utcnow().timestamp())
        invoice_no = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{invoice_id % 10000:04d}"
        
        from src.database.user_operations import get_user
        user = get_user(user_id)
        
        payload = {
            'invoice_id': invoice_id,
            'invoice_no': invoice_no,
            'date': datetime.utcnow().strftime('%d %b %Y'),
            'billed_to': {'name': user.get('full_name','') if user else '', 'telegram_id': user_id},
            'items': items,
            'shipping': shipping,
            'gst_amount': gst_total,
            'total': final_total,
            'status': 'UNPAID'
        }

        # Save invoice to lightweight store
        save_invoice(invoice_id, payload)

        # Create receivable record referencing invoice id
        receivable = create_receivable(user_id, 'invoice', invoice_id, bill_amount=final_total, discount_amount=0.0, final_amount=final_total)

        # Generate PDF and send to user
        pdf_buf = generate_invoice_pdf(payload, GYM_PROFILE)
        try:
            await context.bot.send_document(chat_id=user_id, document=pdf_buf, filename=f"invoice_{invoice_no}.pdf")
        except Exception as e:
            logger.debug(f"Could not send invoice PDF to user {user_id}: {e}")

        # Send text summary with buttons
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Pay Bill", callback_data=f"invoice_pay_{invoice_id}"),
             InlineKeyboardButton("❌ Reject Bill", callback_data=f"invoice_reject_{invoice_id}")]
        ])
        await query.edit_message_text(f"✅ Invoice {invoice_no} sent to user {user_id}", reply_markup=None)
        await context.bot.send_message(chat_id=user_id, text=f"You have received Invoice {invoice_no} for ₹{final_total:.2f}", reply_markup=keyboard)

        return ConversationHandler.END
    else:
        await query.edit_message_text("❌ Invoice creation cancelled.")
        return ConversationHandler.END


async def invoice_pay_clicked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user's click on Pay Bill: acknowledge and start existing payment request flow."""
    query = update.callback_query
    invoice_id = None
    try:
        data = query.data
        invoice_id = int(data.split("_")[-1])
    except Exception:
        pass
    logger.info(f"[INVOICE] Pay Bill clicked invoice_id={invoice_id}")
    try:
        await query.answer()
        logger.info("[INVOICE] Callback acknowledged")
    except Exception:
        # Don't fail if answering old callback
        logger.debug("[INVOICE] Failed to answer callback (likely expired)")

    # Start existing user payment request flow to keep logic unchanged
    try:
        from src.handlers.payment_request_handlers import cmd_request_payment
        # Inform the user and then invoke the flow
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=(
                "💳 Select Payment Method\n\n"
                "To proceed, submit a payment request with amount and screenshot."
            )
        )
        await cmd_request_payment(update, context)
    except Exception as e:
        logger.error(f"[INVOICE] Error starting payment request flow: {e}")
        await context.bot.send_message(chat_id=query.from_user.id, text="⚠️ Couldn't start payment flow. Please use /request_payment.")


async def invoice_reject_clicked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user's click on Reject Bill: acknowledge, mark rejected, notify admin, confirm to user."""
    query = update.callback_query
    user_id = query.from_user.id
    invoice_id = None
    try:
        invoice_id = int(query.data.split("_")[-1])
    except Exception:
        pass
    logger.info(f"[INVOICE] Reject Bill clicked invoice_id={invoice_id}")
    try:
        await query.answer()
        logger.info("[INVOICE] Callback acknowledged")
    except Exception:
        logger.debug("[INVOICE] Failed to answer callback (likely expired)")

    # Update invoice status to REJECTED (lightweight store)
    try:
        inv = load_invoice(invoice_id)
        if inv:
            inv['status'] = 'REJECTED'
            save_invoice(invoice_id, inv)
    except Exception as e:
        logger.debug(f"[INVOICE] Could not update invoice status to REJECTED: {e}")

    # Notify admins
    try:
        for chat_id in get_moderator_chat_ids(include_staff=True):
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"⚠️ User {user_id} rejected Invoice #{invoice_id}.\n"
                        "Actions: Delete/Resend/Edit from admin panel."
                    )
                )
            except Exception as e:
                logger.debug(f"[INVOICE] Failed notifying admin {chat_id}: {e}")
    except Exception:
        logger.debug("[INVOICE] Admin notification skipped.")

    # Confirm to user
    try:
        await context.bot.send_message(chat_id=user_id, text="✅ Invoice rejected successfully.")
    except Exception:
        logger.debug("[INVOICE] Failed sending user confirmation for rejection")


def get_invoice_conversation_handler():
    from telegram.ext import CallbackQueryHandler
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cmd_create_invoice_start, pattern="^cmd_invoices$")
        ],
        states={
            INV_ENTER_USER: [
                CallbackQueryHandler(inv_search_user_prompt, pattern="^inv_search_user$"),
                CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^inv_manual_entry$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, inv_enter_user)
            ],
            INV_SEARCH_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, inv_search_query_handler),
                CallbackQueryHandler(inv_select_user, pattern="^inv_select_")
            ],
            INV_ITEM_CHOICE: [
                CallbackQueryHandler(inv_item_choice, pattern="^inv_(store_search|custom_item)$")
            ],
            INV_STORE_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, inv_store_search),
                CallbackQueryHandler(inv_store_select, pattern="^inv_store_select_")
            ],
            INV_ADD_ITEM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, inv_add_item_name)],
            INV_ADD_ITEM_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, inv_add_item_rate)],
            INV_ADD_ITEM_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, inv_add_item_quantity)],
            INV_ADD_ITEM_DISCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, inv_add_item_discount)],
            INV_SHIPPING: [MessageHandler(filters.TEXT & ~filters.COMMAND, inv_add_shipping)],
            INV_REVIEW: [
                CallbackQueryHandler(inv_review_actions, pattern="^inv_(add_another|finish_items|send|edit|cancel)$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^inv_cancel$")
        ],
        per_message=False
    )

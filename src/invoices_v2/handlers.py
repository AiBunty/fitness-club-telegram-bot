"""
Invoice v2 - Conversation Handlers (Complete Flow)
"""
import json
import logging
import os
from datetime import datetime
from uuid import uuid4
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)

from src.invoices_v2.state import InvoiceV2State
from src.invoices_v2.store import search_item, load_items
from src.invoices_v2.utils import search_users, get_gst_config, calculate_gst, format_user_display
from src.utils.auth import is_admin


logger = logging.getLogger(__name__)

INVOICES_FILE = "data/invoices_v2.json"


def ensure_invoices_file():
    """Ensure invoices file exists"""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(INVOICES_FILE):
        with open(INVOICES_FILE, "w") as f:
            json.dump([], f, indent=2)


def load_invoices():
    """Load all invoices"""
    ensure_invoices_file()
    try:
        with open(INVOICES_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_invoices(invoices):
    """Save invoices"""
    ensure_invoices_file()
    with open(INVOICES_FILE, "w") as f:
        json.dump(invoices, f, indent=2)


def save_invoice(invoice_data: dict) -> str:
    """
    Save invoice and return invoice_id
    """
    invoices = load_invoices()
    invoice_id = str(uuid4())[:8].upper()
    
    invoice_data["invoice_id"] = invoice_id
    invoice_data["created_at"] = datetime.now().isoformat()
    
    invoices.append(invoice_data)
    save_invoices(invoices)
    
    logger.info(f"[INVOICE_V2] invoice_created invoice_id={invoice_id} user_id={invoice_data.get('user_id')}")
    return invoice_id


# ============================================================================
# ENTRY POINT: Admin clicks "🧾 Invoices"
# ============================================================================

async def cmd_invoices_v2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: Clear state, show invoice menu"""
    query = update.callback_query
    admin_id = query.from_user.id if query else update.effective_user.id
    
    # CRITICAL: Answer callback immediately to stop Telegram loading spinner
    if query:
        await query.answer()
        logger.info(f"[INVOICE_V2] entry_point callback_received admin={admin_id} callback_data={query.data}")
    else:
        logger.info(f"[INVOICE_V2] entry_point command_received admin={admin_id}")

    # CRITICAL: Clear any stale states before starting Invoice flow
    # NOTE: Do NOT call clear_stale_states() as it returns ConversationHandler.END and kills this flow!
    # Instead, manually clear user_data and continue
    if context.user_data:
        logger.info(f"[INVOICE_V2] Clearing stale states: {list(context.user_data.keys())}")
        context.user_data.clear()
    
    if not is_admin(admin_id):
        await update.effective_user.send_message("❌ Admin access required")
        return ConversationHandler.END
    
    logger.info(f"[INVOICE_V2] entry_point_success admin={admin_id}")
    
    # Initialize invoice state
    context.user_data["invoice_v2_data"] = {
        "selected_user": None,
        "items": [],
        "shipping": 0,
    }
    
    text = "📄 *Invoice Menu*\n\nCreate a new invoice:"
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("➕ Create Invoice", callback_data="inv2_create_start")
    ]])
    
    if query:
        await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.effective_user.send_message(text, reply_markup=kb, parse_mode="Markdown")
    
    return InvoiceV2State.SEARCH_USER


# ============================================================================
# STEP 1: User Search
# ============================================================================

async def search_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt admin to search for user"""
    query = update.callback_query
    admin_id = query.from_user.id if query else update.effective_user.id
    
    if query:
        await query.answer()
    
    logger.info(f"[INVOICE_V2] search_user_start admin={admin_id}")
    
    text = "🔍 Search user by *Name*, *Username*, or *Telegram ID*:"
    
    if query:
        await query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.effective_user.send_message(text, parse_mode="Markdown")
    
    return InvoiceV2State.SEARCH_USER


async def handle_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user search query"""
    query = update.message.text
    admin_id = update.effective_user.id
    
    logger.info(f"[INVOICE_V2] handle_user_search CALLED state=SEARCH_USER admin={admin_id} query={query}")
    
    results = search_users(query, limit=10)
    
    logger.info(f"[INVOICE_V2] user_search_results count={len(results)}")
    
    if not results:
        await update.effective_user.send_message("❌ No users found. Try again:")
        return InvoiceV2State.SEARCH_USER
    
    # Show results with selection buttons
    text = f"Found {len(results)} user(s):\n\n"
    
    kb_buttons = []
    for i, user in enumerate(results):
        display = format_user_display(user)
        text += f"{i+1}. {display}\n"
        
        # Store user in context for selection
        callback_data = f"inv2_select_user_{i}"
        kb_buttons.append([InlineKeyboardButton(f"{i+1}. {display}", callback_data=callback_data)])
        
        # Store users in context
        if "invoice_v2_search_results" not in context.user_data:
            context.user_data["invoice_v2_search_results"] = {}
        context.user_data["invoice_v2_search_results"][i] = user
    
    kb_buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="inv2_cancel")])
    
    await update.effective_user.send_message(text, reply_markup=InlineKeyboardMarkup(kb_buttons))
    return InvoiceV2State.SELECT_USER


async def handle_user_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user selection from search results"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    await query.answer()
    
    # Extract index from callback_data
    callback_data = query.data  # inv2_select_user_0, inv2_select_user_1, etc.
    index = int(callback_data.split("_")[-1])
    
    search_results = context.user_data.get("invoice_v2_search_results", {})
    selected_user = search_results.get(index)
    
    if not selected_user:
        await query.answer("❌ User not found")
        return InvoiceV2State.SELECT_USER
    
    # Save selected user
    context.user_data["invoice_v2_data"]["selected_user"] = selected_user
    
    logger.info(f"[INVOICE_V2] user_selected admin={admin_id} user_id={selected_user.get('telegram_id')}")
    
    # Move to item mode
    user_display = format_user_display(selected_user)
    text = f"✅ Selected: *{user_display}*\n\nNow, add items to invoice:"
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search Store Item", callback_data="inv2_search_store")],
        [InlineKeyboardButton("✍️ Add Custom Item", callback_data="inv2_custom_item")],
        [InlineKeyboardButton("❌ Cancel Invoice", callback_data="inv2_cancel")]
    ])
    
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    return InvoiceV2State.ITEM_MODE


# ============================================================================
# STEP 2: Item Mode Selection
# ============================================================================

async def handle_item_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle item mode selection (search or custom)"""
    query = update.callback_query
    data = query.data
    
    await query.answer()
    
    if data == "inv2_search_store":
        await query.edit_message_text("🔍 Search item by *NAME* or *SERIAL NUMBER*:", parse_mode="Markdown")
        return InvoiceV2State.SEARCH_STORE_ITEM
    
    elif data == "inv2_custom_item":
        await query.edit_message_text("✍️ Enter item *name*:", parse_mode="Markdown")
        return InvoiceV2State.CUSTOM_ITEM_NAME
    
    elif data == "inv2_cancel":
        await query.edit_message_text("❌ Invoice cancelled.")
        return ConversationHandler.END
    
    return InvoiceV2State.ITEM_MODE


# ============================================================================
# STORE ITEM SEARCH PATH
# ============================================================================

async def handle_store_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle store item search query"""
    query = update.message.text
    
    logger.info(f"[INVOICE_V2] store_search_query query={query}")
    
    results = search_item(query)
    
    if not results:
        await update.effective_user.send_message("❌ No items found. Try again:")
        return InvoiceV2State.SEARCH_STORE_ITEM
    
    # Show results
    text = f"Found {len(results)} item(s):\n\n"
    
    kb_buttons = []
    for i, item in enumerate(results):
        serial = item.get("serial")
        name = item.get("name")
        mrp = item.get("mrp")
        gst = item.get("gst_percent")
        
        text += f"{i+1}. [#{serial}] {name} | ₹{mrp} (GST {gst}%)\n"
        
        callback_data = f"inv2_select_item_{i}"
        kb_buttons.append([InlineKeyboardButton(f"#{serial} - {name}", callback_data=callback_data)])
        
        if "invoice_v2_store_results" not in context.user_data:
            context.user_data["invoice_v2_store_results"] = {}
        context.user_data["invoice_v2_store_results"][i] = item
    
    kb_buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="inv2_cancel")])
    
    await update.effective_user.send_message(text, reply_markup=InlineKeyboardMarkup(kb_buttons))
    return InvoiceV2State.SELECT_STORE_ITEM


async def handle_store_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle store item selection"""
    query = update.callback_query
    
    await query.answer()
    
    if query.data == "inv2_cancel":
        await query.edit_message_text("❌ Invoice cancelled.")
        return ConversationHandler.END
    
    # Extract index
    index = int(query.data.split("_")[-1])
    store_results = context.user_data.get("invoice_v2_store_results", {})
    selected_item = store_results.get(index)
    
    if not selected_item:
        await query.answer("❌ Item not found")
        return InvoiceV2State.SELECT_STORE_ITEM
    
    # Auto-fill item data
    context.user_data["invoice_v2_current_item"] = {
        "name": selected_item.get("name"),
        "rate": selected_item.get("mrp"),
        "gst_percent": selected_item.get("gst_percent"),
        "serial": selected_item.get("serial")
    }
    
    logger.info(f"[INVOICE_V2] store_item_selected serial={selected_item.get('serial')}")
    
    # Ask for quantity
    text = f"📦 Item: *{selected_item.get('name')}*\nRate: ₹{selected_item.get('mrp')}\n\nEnter *Quantity*:"
    await query.edit_message_text(text, parse_mode="Markdown")
    
    return InvoiceV2State.ITEM_QUANTITY


# ============================================================================
# CUSTOM ITEM PATH
# ============================================================================

async def handle_custom_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom item name"""
    name = update.message.text
    
    context.user_data["invoice_v2_current_item"] = {"name": name}
    
    logger.info(f"[INVOICE_V2] custom_item_name name={name}")
    
    await update.effective_user.send_message("💰 Enter item *Rate* (₹):", parse_mode="Markdown")
    
    return InvoiceV2State.CUSTOM_ITEM_RATE


async def handle_custom_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom item rate"""
    try:
        rate = float(update.message.text)
        if rate <= 0:
            await update.effective_user.send_message("❌ Rate must be > 0. Try again:")
            return InvoiceV2State.CUSTOM_ITEM_RATE
    except ValueError:
        await update.effective_user.send_message("❌ Invalid amount. Try again:")
        return InvoiceV2State.CUSTOM_ITEM_RATE
    
    context.user_data["invoice_v2_current_item"]["rate"] = rate
    
    # For custom items, use global GST config
    gst_config = get_gst_config()
    context.user_data["invoice_v2_current_item"]["gst_percent"] = gst_config.get("percent", 18) if gst_config.get("enabled") else 0
    
    logger.info(f"[INVOICE_V2] custom_item_rate rate={rate}")
    
    await update.effective_user.send_message("📦 Enter *Quantity*:", parse_mode="Markdown")
    
    return InvoiceV2State.ITEM_QUANTITY


async def handle_item_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle item quantity"""
    try:
        qty = int(update.message.text)
        if qty <= 0:
            await update.effective_user.send_message("❌ Quantity must be > 0. Try again:")
            return InvoiceV2State.ITEM_QUANTITY
    except ValueError:
        await update.effective_user.send_message("❌ Invalid quantity. Try again:")
        return InvoiceV2State.ITEM_QUANTITY
    
    context.user_data["invoice_v2_current_item"]["quantity"] = qty
    
    logger.info(f"[INVOICE_V2] item_quantity qty={qty}")
    
    await update.effective_user.send_message("🏷️ Enter *Discount %* (0-80):", parse_mode="Markdown")
    
    return InvoiceV2State.ITEM_DISCOUNT


async def handle_item_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle item discount"""
    try:
        discount = float(update.message.text)
        if not (0 <= discount <= 80):
            await update.effective_user.send_message("❌ Discount must be 0-80%. Try again:")
            return InvoiceV2State.ITEM_DISCOUNT
    except ValueError:
        await update.effective_user.send_message("❌ Invalid discount. Try again:")
        return InvoiceV2State.ITEM_DISCOUNT
    
    context.user_data["invoice_v2_current_item"]["discount_percent"] = discount
    
    logger.info(f"[INVOICE_V2] item_discount discount={discount}%")
    
    # Calculate line total
    current_item = context.user_data["invoice_v2_current_item"]
    base = current_item["rate"] * current_item["quantity"]
    discount_amount = base * discount / 100
    taxable = base - discount_amount
    
    gst_config = get_gst_config()
    if gst_config.get("enabled"):
        gst_percent = current_item.get("gst_percent", 18)
        if gst_config.get("mode") == "inclusive":
            gst_amount = taxable * gst_percent / (100 + gst_percent)
        else:
            gst_amount = taxable * gst_percent / 100
    else:
        gst_amount = 0
    
    current_item["base"] = round(base, 2)
    current_item["discount_amount"] = round(discount_amount, 2)
    current_item["taxable"] = round(taxable, 2)
    current_item["gst_amount"] = round(gst_amount, 2)
    current_item["line_total"] = round(taxable + gst_amount, 2)
    
    # Show item summary
    text = f"""
✅ Item Summary:
━━━━━━━━━━━━━━━━
Name: {current_item['name']}
Rate: ₹{current_item['rate']}
Qty: {current_item['quantity']}
Discount: {discount}%
Taxable: ₹{current_item['taxable']}
GST: ₹{current_item['gst_amount']}
Line Total: ₹{current_item['line_total']}
━━━━━━━━━━━━━━━━

Add more items?
"""
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Another Item", callback_data="inv2_item_add_more")],
        [InlineKeyboardButton("➡️ Finish Items", callback_data="inv2_items_done")],
        [InlineKeyboardButton("❌ Cancel Invoice", callback_data="inv2_cancel")]
    ])
    
    await update.effective_user.send_message(text, reply_markup=kb, parse_mode="Markdown")
    
    return InvoiceV2State.ITEM_CONFIRM


async def handle_item_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle item confirmation (add more or finish)"""
    query = update.callback_query
    data = query.data
    
    await query.answer()
    
    current_item = context.user_data["invoice_v2_current_item"]
    
    if data == "inv2_item_add_more":
        # Add item to list
        context.user_data["invoice_v2_data"]["items"].append(current_item)
        context.user_data.pop("invoice_v2_current_item", None)
        
        logger.info(f"[INVOICE_V2] item_added name={current_item['name']}")
        
        # Back to item mode
        text = "Add more items?"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search Store Item", callback_data="inv2_search_store")],
            [InlineKeyboardButton("✍️ Add Custom Item", callback_data="inv2_custom_item")],
            [InlineKeyboardButton("➡️ Finish Items", callback_data="inv2_items_done")],
            [InlineKeyboardButton("❌ Cancel Invoice", callback_data="inv2_cancel")]
        ])
        
        await query.edit_message_text(text, reply_markup=kb)
        return InvoiceV2State.ITEM_MODE
    
    elif data == "inv2_items_done":
        # Add last item to list
        context.user_data["invoice_v2_data"]["items"].append(current_item)
        context.user_data.pop("invoice_v2_current_item", None)
        
        logger.info(f"[INVOICE_V2] item_added name={current_item['name']}")
        
        # Move to shipping
        await query.edit_message_text("🚚 Enter *Shipping/Delivery Charge* (₹, or 0):", parse_mode="Markdown")
        return InvoiceV2State.SHIPPING
    
    elif data == "inv2_cancel":
        await query.edit_message_text("❌ Invoice cancelled.")
        return ConversationHandler.END
    
    return InvoiceV2State.ITEM_CONFIRM


# ============================================================================
# STEP 3: Shipping
# ============================================================================

async def handle_shipping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle shipping charge"""
    try:
        shipping = float(update.message.text)
        if shipping < 0:
            await update.effective_user.send_message("❌ Shipping must be ≥ 0. Try again:")
            return InvoiceV2State.SHIPPING
    except ValueError:
        await update.effective_user.send_message("❌ Invalid amount. Try again:")
        return InvoiceV2State.SHIPPING
    
    context.user_data["invoice_v2_data"]["shipping"] = shipping
    
    logger.info(f"[INVOICE_V2] shipping_set shipping={shipping}")
    
    # Calculate totals
    invoice_data = context.user_data["invoice_v2_data"]
    items_subtotal = sum(item.get("line_total", 0) for item in invoice_data["items"])
    gst_total = sum(item.get("gst_amount", 0) for item in invoice_data["items"])
    final_total = items_subtotal + shipping
    
    invoice_data["items_subtotal"] = round(items_subtotal, 2)
    invoice_data["gst_total"] = round(gst_total, 2)
    invoice_data["final_total"] = round(final_total, 2)
    
    # Show final review
    text = "📋 *Final Invoice Summary*\n━━━━━━━━━━━━━━━━\n"
    
    selected_user = invoice_data["selected_user"]
    user_display = format_user_display(selected_user)
    text += f"User: {user_display}\n\n"
    
    text += "*Items:*\n"
    for i, item in enumerate(invoice_data["items"], 1):
        text += f"{i}. {item['name']} x{item['quantity']} = ₹{item['line_total']}\n"
    
    text += f"\nSubtotal: ₹{invoice_data['items_subtotal']}\n"
    text += f"Shipping: ₹{shipping}\n"
    text += f"GST Total: ₹{invoice_data['gst_total']}\n"
    text += f"*Final Total: ₹{invoice_data['final_total']}*\n"
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Send Invoice", callback_data="inv2_send")],
        [InlineKeyboardButton("❌ Cancel", callback_data="inv2_cancel")]
    ])
    
    await update.effective_user.send_message(text, reply_markup=kb, parse_mode="Markdown")
    
    return InvoiceV2State.FINAL_REVIEW


# ============================================================================
# STEP 4: Send Invoice
# ============================================================================

async def handle_send_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate and send invoice"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    await query.answer()
    
    if query.data == "inv2_cancel":
        await query.edit_message_text("❌ Invoice cancelled.")
        return ConversationHandler.END
    
    invoice_data = context.user_data["invoice_v2_data"]
    selected_user = invoice_data["selected_user"]
    user_id = selected_user["telegram_id"]
    user_name = format_user_display(selected_user)
    
    # Save invoice
    invoice_save_data = {
        "user_id": user_id,
        "user_name": user_name,
        "items": invoice_data["items"],
        "items_subtotal": invoice_data["items_subtotal"],
        "shipping": invoice_data["shipping"],
        "gst_total": invoice_data["gst_total"],
        "final_total": invoice_data["final_total"],
        "created_by": admin_id,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    
    invoice_id = save_invoice(invoice_save_data)
    
    # Generate PDF
    pdf_data = {
        "invoice_id": invoice_id,
        "date": invoice_save_data["date"],
        "user_name": user_name,
        "user_id": user_id,
        "items": invoice_data["items"],
        "items_subtotal": invoice_data["items_subtotal"],
        "shipping": invoice_data["shipping"],
        "gst_total": invoice_data["gst_total"],
        "final_total": invoice_data["final_total"]
    }
    
    # Lazy import to avoid reportlab regex compilation during bot startup
    from src.invoices_v2.pdf import generate_invoice_pdf

    pdf_buffer = generate_invoice_pdf(pdf_data)
    
    # Send to user
    user_text = f"""
✅ Invoice Generated

Invoice ID: `{invoice_id}`
Total Amount: ₹{invoice_data['final_total']}

Actions:
"""
    
    user_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Pay Bill", callback_data=f"inv2_pay_{invoice_id}")],
        [InlineKeyboardButton("❌ Reject Bill", callback_data=f"inv2_reject_{invoice_id}")]
    ])
    
    try:
        await context.bot.send_document(
            chat_id=user_id,
            document=InputFile(pdf_buffer, filename=f"invoice_{invoice_id}.pdf"),
            caption=user_text,
            reply_markup=user_kb,
            parse_mode="Markdown"
        )
        logger.info(f"[INVOICE_V2] invoice_sent_to_user invoice_id={invoice_id} user_id={user_id}")
    except Exception as e:
        logger.error(f"[INVOICE_V2] failed_to_send_to_user invoice_id={invoice_id} error={e}")
        await query.edit_message_text(f"❌ Failed to send invoice to user: {e}")
        return ConversationHandler.END
    
    # Send copy to admin(s)
    admin_text = f"📄 Invoice {invoice_id} generated for {user_name}\nAmount: ₹{invoice_data['final_total']}"
    
    admin_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Delete Invoice", callback_data=f"inv2_delete_{invoice_id}")],
        [InlineKeyboardButton("🔁 Resend to User", callback_data=f"inv2_resend_{invoice_id}")]
    ])
    
    # Reset PDF buffer
    pdf_buffer.seek(0)
    
    try:
        # Get admin user IDs from database or config
        # For now, just send to current admin
        await context.bot.send_document(
            chat_id=admin_id,
            document=InputFile(pdf_buffer, filename=f"invoice_{invoice_id}.pdf"),
            caption=admin_text,
            reply_markup=admin_kb,
            parse_mode="Markdown"
        )
        logger.info(f"[INVOICE_V2] invoice_sent_to_admin invoice_id={invoice_id} admin_id={admin_id}")
    except Exception as e:
        logger.error(f"[INVOICE_V2] failed_to_send_to_admin invoice_id={invoice_id} error={e}")
    
    # Confirm to admin
    await query.edit_message_text(f"✅ Invoice {invoice_id} sent to user and admin!")
    
    return ConversationHandler.END


# ============================================================================
# CANCEL HANDLER
# ============================================================================

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancel at any point"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ Invoice cancelled.")
    else:
        await update.effective_user.send_message("❌ Cancelled.")
    
    return ConversationHandler.END


# ============================================================================
# USER ACTIONS: Pay Bill & Reject Bill
# ============================================================================

async def handle_pay_bill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user clicking 'Pay Bill' on invoice"""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer()
    
    # Extract invoice_id from callback_data: inv2_pay_{invoice_id}
    invoice_id = query.data.split("_")[-1]
    
    logger.info(f"[INVOICE_V2] user_pay_clicked invoice_id={invoice_id} user_id={user_id}")
    
    # Find invoice
    invoices = load_invoices()
    invoice = next((inv for inv in invoices if inv.get("invoice_id") == invoice_id), None)
    
    if not invoice:
        await query.edit_message_text("❌ Invoice not found.")
        return
    
    # Route to existing payment flow
    # Store invoice_id in context for payment system
    context.user_data["pending_invoice_v2"] = invoice_id
    
    text = f"""
💳 *Payment for Invoice {invoice_id}*

Amount: ₹{invoice.get('final_total')}

Please choose payment method:
"""
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 UPI", callback_data="pay_method_upi")],
        [InlineKeyboardButton("💵 Cash", callback_data="pay_method_cash")],
        [InlineKeyboardButton("❌ Cancel", callback_data="pay_method_cancel")]
    ])
    
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


async def handle_reject_bill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user clicking 'Reject Bill' on invoice"""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer()
    
    # Extract invoice_id from callback_data: inv2_reject_{invoice_id}
    invoice_id = query.data.split("_")[-1]
    
    logger.info(f"[INVOICE_V2] user_reject_clicked invoice_id={invoice_id} user_id={user_id}")
    
    # Find invoice
    invoices = load_invoices()
    invoice = next((inv for inv in invoices if inv.get("invoice_id") == invoice_id), None)
    
    if not invoice:
        await query.edit_message_text("❌ Invoice not found.")
        return
    
    # Mark invoice as rejected
    invoice["status"] = "rejected"
    invoice["rejected_at"] = datetime.now().isoformat()
    save_invoices(invoices)
    
    # Notify user
    await query.edit_message_text(f"❌ Invoice {invoice_id} rejected.")
    
    # Notify admin(s)
    admin_id = invoice.get("created_by")
    if admin_id:
        admin_text = f"""
⚠️ Invoice Rejected

Invoice ID: {invoice_id}
User: {invoice.get('user_name')}
Amount: ₹{invoice.get('final_total')}

Actions:
"""
        
        admin_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Delete Invoice", callback_data=f"inv2_admin_delete_{invoice_id}")],
            [InlineKeyboardButton("🔁 Resend Invoice", callback_data=f"inv2_admin_resend_{invoice_id}")]
        ])
        
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=admin_kb,
                parse_mode="Markdown"
            )
            logger.info(f"[INVOICE_V2] reject_notified_admin invoice_id={invoice_id} admin_id={admin_id}")
        except Exception as e:
            logger.error(f"[INVOICE_V2] failed_notify_admin invoice_id={invoice_id} error={e}")


# ============================================================================
# BUILD CONVERSATION HANDLER
# ============================================================================

def get_invoice_v2_handler():
    """Create and return invoice v2 conversation handler"""
    logger.info("[INVOICE_V2] Registering Invoice v2 ConversationHandler with entry pattern ^cmd_invoices$")
    
    async def invoice_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Guard to ensure Invoice is not intercepting Management flows"""
        # CRITICAL: If user is in management flow, REJECT this message
        if context.user_data.get("is_in_management_flow"):
            logger.warning(f"[INVOICE_V2] Message received but user is in MANAGEMENT flow - rejecting")
            return False  # Tell ConversationHandler to skip this
        
        # Check if we have active invoice state
        if not context.user_data.get("invoice_v2_data"):
            logger.warning(f"[INVOICE_V2] Text received but no invoice_v2_data in context - may be stale")
            # Still return True to let handler process, but log warning
        
        return True  # Allow handler to proceed
    
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cmd_invoices_v2, pattern="^cmd_invoices$"),
        ],
        states={
            InvoiceV2State.SEARCH_USER: [
                CallbackQueryHandler(search_user_start, pattern="^inv2_create_start$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_search),
            ],
            InvoiceV2State.SELECT_USER: [
                CallbackQueryHandler(handle_user_select, pattern="^inv2_select_user_\\d+$"),
                CallbackQueryHandler(handle_cancel, pattern="^inv2_cancel$"),
            ],
            InvoiceV2State.ITEM_MODE: [
                CallbackQueryHandler(handle_item_mode, pattern="^inv2_(search_store|custom_item|cancel)$"),
            ],
            InvoiceV2State.SEARCH_STORE_ITEM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_store_search),
            ],
            InvoiceV2State.SELECT_STORE_ITEM: [
                CallbackQueryHandler(handle_store_select, pattern="^inv2_(select_item_\\d+|cancel)$"),
            ],
            InvoiceV2State.CUSTOM_ITEM_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_name),
            ],
            InvoiceV2State.CUSTOM_ITEM_RATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_rate),
            ],
            InvoiceV2State.ITEM_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item_quantity),
            ],
            InvoiceV2State.ITEM_DISCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item_discount),
            ],
            InvoiceV2State.ITEM_CONFIRM: [
                CallbackQueryHandler(handle_item_confirm, pattern="^inv2_(item_add_more|items_done|cancel)$"),
            ],
            InvoiceV2State.SHIPPING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_shipping),
            ],
            InvoiceV2State.FINAL_REVIEW: [
                CallbackQueryHandler(handle_send_invoice, pattern="^inv2_(send|cancel)$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(handle_cancel, pattern="^inv2_cancel$"),
        ],
        conversation_timeout=300,  # 5 minute timeout (MORE AGGRESSIVE) to prevent stuck states
        per_message=False,
        per_chat=True,  # CRITICAL: Isolate conversations per chat for 200+ users
        per_user=True,  # CRITICAL: Isolate conversations per user
        name="invoice_v2_conversation"  # Explicit name for debugging
    )

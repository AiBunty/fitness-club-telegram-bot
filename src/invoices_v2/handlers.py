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
from src.invoices_v2.search_items_db_only import (
    search_store_items_db_only,
    format_item_for_display,
    get_item_details_for_invoice
)
from src.invoices_v2.utils import search_users, get_gst_config, calculate_gst, format_user_display
from src.database.ar_operations import (
    create_receivable,
    create_transactions,
    get_receivable_by_source,
    update_receivable_status,
)
from src.utils.auth import is_admin
from src.handlers.admin_handlers import get_admin_users
from src.utils.flow_manager import (
    set_active_flow, clear_active_flow, check_flow_ownership,
    FLOW_INVOICE_V2_CREATE
)


logger = logging.getLogger(__name__)

INVOICES_FILE = "data/invoices_v2.json"


def ensure_payment_tracking_fields(invoice_data: dict) -> dict:
    """Ensure payment tracking fields exist for invoice JSON."""
    invoice_data.setdefault("paid_amount", 0)
    if not isinstance(invoice_data.get("payment_lines"), list):
        invoice_data["payment_lines"] = []
    return invoice_data


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
    ensure_payment_tracking_fields(invoice_data)
    
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

    # CRITICAL: Lock INVOICE_V2_CREATE flow to prevent interference from other flows
    set_active_flow(admin_id, FLOW_INVOICE_V2_CREATE)

    # CRITICAL: Clear any stale states before starting Invoice flow
    # NOTE: Do NOT call clear_stale_states() as it returns ConversationHandler.END and kills this flow!
    # Instead, manually clear user_data and continue
    if context.user_data:
        logger.info(f"[INVOICE_V2] Clearing stale states: {list(context.user_data.keys())}")
        context.user_data.clear()
    
    if not is_admin(admin_id):
        await update.effective_user.send_message("❌ Admin access required")
        clear_active_flow(admin_id, FLOW_INVOICE_V2_CREATE)
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
    admin_id = update.effective_user.id
    
    # CRITICAL: Check flow ownership
    if not check_flow_ownership(admin_id, FLOW_INVOICE_V2_CREATE):
        await update.effective_user.send_message("❌ Invalid context. Please use /menu to start over.")
        return ConversationHandler.END
    
    query = update.message.text
    
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
    
    # CRITICAL: Check flow ownership
    if not check_flow_ownership(admin_id, FLOW_INVOICE_V2_CREATE):
        await query.answer("❌ Invalid context.", show_alert=True)
        return ConversationHandler.END
    
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
    
    logger.info(f"[INVOICE_V2] user_selected admin={admin_id} user_id={selected_user.get('telegram_id') or selected_user.get('user_id')}")
    
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
    
    results = search_store_items_db_only(query)
    
    if not results:
        await update.effective_user.send_message("❌ No items found. Try again:")
        return InvoiceV2State.SEARCH_STORE_ITEM
    
    # Show results
    text = f"Found {len(results)} item(s):\n\n"
    
    kb_buttons = []
    for i, item in enumerate(results):
        serial = item.get("serial_no")
        name = item.get("item_name")
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
    item_details = get_item_details_for_invoice(selected_item)
    context.user_data["invoice_v2_current_item"] = {
        "name": item_details.get("item_name"),
        "rate": item_details.get("mrp"),
        "gst_percent": item_details.get("gst_percent"),
        "serial": selected_item.get("serial_no"),
        "store_item_id": item_details.get("store_item_id")
    }
    
    logger.info(f"[INVOICE_V2] store_item_selected serial={selected_item.get('serial_no')}")
    
    # Ask for quantity
    text = f"📦 Item: *{selected_item.get('item_name')}*\nRate: ₹{selected_item.get('mrp')}\n\nEnter *Quantity*:"
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
    
    # CRITICAL: Check flow ownership
    if not check_flow_ownership(admin_id, FLOW_INVOICE_V2_CREATE):
        await query.answer("❌ Invalid context.", show_alert=True)
        return ConversationHandler.END
    
    await query.answer()
    
    if query.data == "inv2_cancel":
        await query.edit_message_text("❌ Invoice cancelled.")
        clear_active_flow(admin_id, FLOW_INVOICE_V2_CREATE)
        return ConversationHandler.END
    
    invoice_data = context.user_data["invoice_v2_data"]
    selected_user = invoice_data["selected_user"]
    user_id = selected_user.get("telegram_id") or selected_user.get("user_id")
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
    
    user_send_error = None
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
        user_send_error = str(e)
        logger.error(f"[INVOICE_V2] failed_to_send_to_user invoice_id={invoice_id} error={e}")
    
    # Send copy to admin(s)
    admin_text = (
        f"📄 Invoice {invoice_id} generated for {user_name}\n"
        f"Amount: ₹{invoice_data['final_total']}\n"
        f"User delivery: {'✅ Sent' if not user_send_error else '❌ Failed'}"
    )
    
    admin_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Delete Invoice", callback_data=f"inv2_delete_{invoice_id}")],
        [InlineKeyboardButton("🔁 Resend to User", callback_data=f"inv2_resend_{invoice_id}")]
    ])
    
    admin_users = get_admin_users()
    admin_ids = [a.get("user_id") for a in admin_users if a.get("user_id")]
    if admin_id not in admin_ids:
        admin_ids.append(admin_id)

    for aid in admin_ids:
        try:
            pdf_buffer.seek(0)
            await context.bot.send_document(
                chat_id=aid,
                document=InputFile(pdf_buffer, filename=f"invoice_{invoice_id}.pdf"),
                caption=admin_text,
                reply_markup=admin_kb,
                parse_mode="Markdown"
            )
            logger.info(f"[INVOICE_V2] invoice_sent_to_admin invoice_id={invoice_id} admin_id={aid}")
        except Exception as e:
            logger.error(f"[INVOICE_V2] failed_to_send_to_admin invoice_id={invoice_id} admin_id={aid} error={e}")
    
    # Confirm to admin
    if user_send_error:
        await query.edit_message_text(
            f"⚠️ Invoice {invoice_id} created, but failed to send to user. Admins received a copy.\nError: {user_send_error}"
        )
    else:
        await query.edit_message_text(f"✅ Invoice {invoice_id} sent to user and all admins!")
    
    # CRITICAL: Clear invoice flow lock on successful completion
    clear_active_flow(admin_id, FLOW_INVOICE_V2_CREATE)
    
    return ConversationHandler.END


# ============================================================================
# CANCEL HANDLER
# ============================================================================

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancel at any point"""
    admin_id = (update.callback_query.from_user.id if update.callback_query 
                else update.effective_user.id)
    
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ Invoice cancelled.")
    else:
        await update.effective_user.send_message("❌ Cancelled.")
    
    # CRITICAL: Clear invoice flow lock
    clear_active_flow(admin_id, FLOW_INVOICE_V2_CREATE)
    
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
# INVOICE PAYMENT HANDLERS
# ============================================================================

async def handle_invoice_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment method selection for invoice (UPI/Cash)"""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer()
    
    payment_method_data = query.data  # pay_method_upi, pay_method_cash, or pay_method_cancel
    
    # Check if this is for an invoice
    invoice_id = context.user_data.get("pending_invoice_v2")
    
    if not invoice_id:
        await query.edit_message_text("❌ Invoice session expired. Please try again.")
        return
    
    # Load invoice
    invoices = load_invoices()
    invoice = next((inv for inv in invoices if inv.get("invoice_id") == invoice_id), None)
    if invoice:
        invoice = ensure_payment_tracking_fields(invoice)
    
    if not invoice:
        await query.edit_message_text("❌ Invoice not found.")
        return
    
    # Handle cancel
    if payment_method_data == "pay_method_cancel":
        await query.edit_message_text("❌ Payment cancelled.")
        context.user_data.pop("pending_invoice_v2", None)
        return
    
    # Extract payment method
    payment_method = payment_method_data.split("_")[-1]  # 'upi' or 'cash'
    
    logger.info(f"[INVOICE_V2] payment_method_selected invoice_id={invoice_id} user_id={user_id} method={payment_method}")
    
    if payment_method == "cash":
        # Handle cash payment
        await handle_invoice_cash_payment(query, context, invoice, invoice_id, user_id)
    
    elif payment_method == "upi":
        # Handle UPI payment
        await handle_invoice_upi_payment(query, context, invoice, invoice_id, user_id)
    
    else:
        await query.edit_message_text("❌ Invalid payment method")


async def handle_invoice_cash_payment(query, context, invoice, invoice_id, user_id):
    """Process cash payment for invoice"""
    ensure_payment_tracking_fields(invoice)
    # Update invoice with payment info
    invoice["payment_status"] = "pending_cash"
    invoice["payment_method"] = "cash"
    invoice["payment_initiated_at"] = datetime.now().isoformat()
    if not invoice.get("payment_lines"):
        invoice["payment_lines"] = [
            {
                "amount": invoice.get("final_total", 0),
                "payment_method": "cash",
                "reference": None,
                "confirmed_by_admin_id": None,
                "confirmed_at": None,
            }
        ]
    
    invoices = load_invoices()
    for idx, inv in enumerate(invoices):
        if inv.get("invoice_id") == invoice_id:
            invoices[idx] = invoice
            break
    save_invoices(invoices)
    
    # Notify user
    await query.edit_message_text(
        f"✅ *Cash Payment - Awaiting Confirmation*\n\n"
        f"Invoice ID: `{invoice_id}`\n"
        f"Amount: ₹{invoice['final_total']}\n"
        f"Payment Method: 💵 Cash\n\n"
        f"Your payment request has been submitted.\n"
        f"Please contact the admin or visit the gym to complete the payment.\n"
        f"You will be notified once confirmed. 🎉",
        parse_mode="Markdown"
    )
    
    # Notify admin
    admin_id = invoice.get("created_by")
    if admin_id:
        try:
            admin_text = (
                f"💵 *Cash Payment Request - Invoice*\n\n"
                f"Invoice ID: `{invoice_id}`\n"
                f"User: {invoice.get('user_name')}\n"
                f"Amount: ₹{invoice['final_total']}\n"
                f"Payment Method: 💵 Cash\n\n"
                f"*Action:* Verify cash received and confirm below."
            )
            
            admin_kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm Payment", callback_data=f"inv2_confirm_cash_{invoice_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"inv2_reject_cash_{invoice_id}")
                ]
            ])
            
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=admin_kb,
                parse_mode="Markdown"
            )
            logger.info(f"[INVOICE_V2] cash_payment_notified admin={admin_id} invoice_id={invoice_id}")
        except Exception as e:
            logger.error(f"[INVOICE_V2] failed_notify_admin_cash invoice_id={invoice_id} error={e}")
    
    # Clean up context
    context.user_data.pop("pending_invoice_v2", None)


async def handle_invoice_upi_payment(query, context, invoice, invoice_id, user_id):
    """Process UPI payment for invoice"""
    from src.utils.upi_qrcode import generate_upi_qr_code, get_upi_id
    
    amount = invoice['final_total']
    user_name = invoice.get('user_name', query.from_user.full_name)
    transaction_ref = f"INV{invoice_id}{int(datetime.now().timestamp())}"

    ensure_payment_tracking_fields(invoice)
    
    # Generate UPI QR code
    qr_bytes = generate_upi_qr_code(amount, user_name, transaction_ref)
    
    if not qr_bytes:
        await query.edit_message_text(
            "❌ Error generating UPI QR code. Please try cash payment instead."
        )
        return
    
    # Update invoice with payment info
    invoice["payment_status"] = "pending_upi"
    invoice["payment_method"] = "upi"
    invoice["payment_initiated_at"] = datetime.now().isoformat()
    invoice["transaction_ref"] = transaction_ref
    if not invoice.get("payment_lines"):
        invoice["payment_lines"] = [
            {
                "amount": invoice.get("final_total", 0),
                "payment_method": "upi",
                "reference": transaction_ref,
                "confirmed_by_admin_id": None,
                "confirmed_at": None,
            }
        ]
    
    invoices = load_invoices()
    for idx, inv in enumerate(invoices):
        if inv.get("invoice_id") == invoice_id:
            invoices[idx] = invoice
            break
    save_invoices(invoices)
    
    # Store in context for screenshot upload
    context.user_data['invoice_payment_screenshot'] = {
        'invoice_id': invoice_id,
        'transaction_ref': transaction_ref
    }
    
    # Get UPI ID
    upi_id = get_upi_id()
    
    # Send QR code to user
    keyboard = [
        [InlineKeyboardButton("📸 Upload Screenshot", callback_data=f"inv2_upload_screenshot_{invoice_id}")],
        [InlineKeyboardButton("⏭️ Skip for Now", callback_data=f"inv2_skip_screenshot_{invoice_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="inv2_payment_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    caption = (
        f"*📱 UPI Payment for Invoice*\n\n"
        f"Invoice ID: `{invoice_id}`\n"
        f"Amount: ₹{amount}\n"
        f"Reference: `{transaction_ref}`\n\n"
        f"*UPI ID:* `{upi_id}`\n"
        f"_(Tap to copy)_\n\n"
        f"*How to Pay:*\n"
        f"1️⃣ Scan the QR code below with any UPI app\n"
        f"2️⃣ OR Copy the UPI ID above and pay via PhonePe/GPay/Paytm\n"
        f"3️⃣ Enter amount: ₹{amount}\n\n"
        f"After payment, upload the screenshot for verification.\n"
        f"Or click 'Skip for Now' to submit without screenshot."
    )
    
    await query.message.reply_photo(
        photo=qr_bytes,
        caption=caption,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    # Delete the payment method selection message
    try:
        await query.message.delete()
    except:
        pass
    
    # Clean up context
    context.user_data.pop("pending_invoice_v2", None)
    
    logger.info(f"[INVOICE_V2] upi_qr_sent invoice_id={invoice_id} user_id={user_id} ref={transaction_ref}")


async def handle_invoice_screenshot_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle screenshot upload for invoice UPI payment"""
    query = update.callback_query
    invoice_id = query.data.split("_")[-1]
    
    await query.answer()
    await query.edit_message_caption(
        caption=query.message.caption + "\n\n📸 *Please send the payment screenshot now.*",
        parse_mode="Markdown"
    )


async def handle_invoice_screenshot_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle skipping screenshot upload for invoice"""
    query = update.callback_query
    user_id = query.from_user.id
    invoice_id = query.data.split("_")[-1]
    
    await query.answer()
    
    # Load invoice
    invoices = load_invoices()
    invoice = next((inv for inv in invoices if inv.get("invoice_id") == invoice_id), None)
    
    if not invoice:
        await query.edit_message_caption("❌ Invoice not found.")
        return
    
    # Update status to pending admin verification
    invoice["payment_status"] = "pending_verification"
    for idx, inv in enumerate(invoices):
        if inv.get("invoice_id") == invoice_id:
            invoices[idx] = invoice
            break
    save_invoices(invoices)
    
    # Notify user
    await query.edit_message_caption(
        caption=(
            f"✅ *Payment Submitted for Verification*\n\n"
            f"Invoice ID: `{invoice_id}`\n"
            f"Amount: ₹{invoice['final_total']}\n"
            f"Reference: `{invoice.get('transaction_ref')}`\n\n"
            f"Your payment will be verified by the admin.\n"
            f"You'll be notified once confirmed. 🎉"
        ),
        parse_mode="Markdown"
    )
    
    # Notify admin
    admin_id = invoice.get("created_by")
    if admin_id:
        try:
            admin_text = (
                f"💳 *UPI Payment Verification - Invoice*\n\n"
                f"Invoice ID: `{invoice_id}`\n"
                f"User: {invoice.get('user_name')}\n"
                f"Amount: ₹{invoice['final_total']}\n"
                f"Reference: `{invoice.get('transaction_ref')}`\n"
                f"Screenshot: Not provided\n\n"
                f"*Action:* Verify UPI transaction and confirm below."
            )
            
            admin_kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm Payment", callback_data=f"inv2_confirm_upi_{invoice_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"inv2_reject_upi_{invoice_id}")
                ]
            ])
            
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=admin_kb,
                parse_mode="Markdown"
            )
            logger.info(f"[INVOICE_V2] upi_verification_notified admin={admin_id} invoice_id={invoice_id}")
        except Exception as e:
            logger.error(f"[INVOICE_V2] failed_notify_admin_upi invoice_id={invoice_id} error={e}")
    
    # Clean up context
    context.user_data.pop("invoice_payment_screenshot", None)


async def handle_invoice_payment_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin confirms invoice payment (cash or UPI)"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    # Extract payment method and invoice_id: inv2_confirm_cash_ABC123 or inv2_confirm_upi_ABC123
    parts = query.data.split("_")
    payment_method = parts[2]  # 'cash' or 'upi'
    invoice_id = parts[3]
    
    await query.answer()
    
    # Load invoice
    invoices = load_invoices()
    invoice = next((inv for inv in invoices if inv.get("invoice_id") == invoice_id), None)
    if invoice:
        invoice = ensure_payment_tracking_fields(invoice)

    if not invoice:
        await query.edit_message_text("❌ Invoice not found.")
        return

    confirmation_ts = datetime.now().isoformat()

    # Mirror into AR ledger (create/fetch receivable, then add transaction) using payment_lines only
    user_id = invoice.get("user_id")
    amount = float(invoice.get("final_total", 0))
    due_date = invoice.get("due_date")

    source_id = None
    try:
        source_id = int(invoice_id)
    except Exception:
        source_id = None  # invoice_id may be non-numeric; keep AR safe

    payment_lines = invoice.get("payment_lines") or []
    pending_lines = []
    for line in payment_lines:
        method = line.get("payment_method") or line.get("method")
        amt = float(line.get("amount", 0)) if isinstance(line, dict) else 0
        if not method or amt <= 0:
            continue
        if line.get("confirmed_at"):
            continue
        pending_lines.append(
            {
                "method": method,
                "amount": amt,
                "reference": line.get("reference"),
            }
        )

    receivable = {}
    rid = None
    if user_id:
        receivable = get_receivable_by_source("invoice", source_id) if source_id is not None else {}
        if not receivable:
            receivable = create_receivable(
                user_id=user_id,
                receivable_type="invoice",
                source_id=source_id,
                bill_amount=amount,
                discount_amount=0.0,
                final_amount=amount,
                due_date=due_date,
            )

        rid = receivable.get("receivable_id") if receivable else None
        if rid:
            if pending_lines:
                create_transactions(rid, pending_lines, admin_user_id=admin_id)
            update_receivable_status(rid)
            invoice["receivable_id"] = rid

    confirmed_amount = 0
    for line in payment_lines:
        method = line.get("payment_method") or line.get("method")
        amt = float(line.get("amount", 0)) if isinstance(line, dict) else 0
        if not method or amt <= 0:
            continue
        if line.get("confirmed_at"):
            confirmed_amount += amt
            continue
        line["confirmed_by_admin_id"] = admin_id
        line["confirmed_at"] = confirmation_ts
        confirmed_amount += amt

    invoice["paid_amount"] = round(confirmed_amount, 2)
    if invoice["paid_amount"] >= invoice.get("final_total", 0):
        invoice["payment_status"] = "paid"
    elif invoice["paid_amount"] > 0:
        invoice["payment_status"] = "partial"
    else:
        invoice["payment_status"] = invoice.get("payment_status", "pending_verification")
    if invoice["paid_amount"] > 0:
        invoice["paid_at"] = confirmation_ts
        invoice["verified_by"] = admin_id
    
    for idx, inv in enumerate(invoices):
        if inv.get("invoice_id") == invoice_id:
            invoices[idx] = invoice
            break
    save_invoices(invoices)
    
    # Update admin message
    methods_summary = ", ".join(
        f"{line.get('payment_method') or line.get('method')} ₹{line.get('amount')}"
        for line in invoice.get("payment_lines", [])
        if line.get("confirmed_at")
    )
    confirmed_display = invoice.get("paid_amount", invoice.get("final_total", 0))
    await query.edit_message_text(
        f"✅ *Payment Confirmed*\n\n"
        f"Invoice ID: `{invoice_id}`\n"
        f"Amount: ₹{confirmed_display} of ₹{invoice.get('final_total', confirmed_display)}\n"
        f"Method(s): {methods_summary or payment_method.upper()}\n"
        f"Verified by: Admin {admin_id}\n"
        f"Confirmed at: {datetime.now().strftime('%d-%m-%Y %H:%M')}",
        parse_mode="Markdown"
    )
    
    # Notify user
    user_id = invoice.get("user_id")
    if user_id:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 *Payment Confirmed!*\n\n"
                    f"Invoice ID: `{invoice_id}`\n"
                    f"Amount: ₹{confirmed_display} of ₹{invoice.get('final_total', confirmed_display)}\n"
                    f"Method(s): {methods_summary or payment_method.upper()}\n\n"
                    f"Thank you for your payment! ✅"
                ),
                parse_mode="Markdown"
            )
            logger.info(f"[INVOICE_V2] payment_confirmed_notification_sent user_id={user_id} invoice_id={invoice_id}")
        except Exception as e:
            logger.error(f"[INVOICE_V2] failed_notify_user_payment_confirmed invoice_id={invoice_id} error={e}")
    
    logger.info(f"[INVOICE_V2] payment_confirmed invoice_id={invoice_id} method={payment_method} admin={admin_id}")


async def handle_invoice_payment_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin rejects invoice payment"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    # Extract payment method and invoice_id: inv2_reject_cash_ABC123 or inv2_reject_upi_ABC123
    parts = query.data.split("_")
    payment_method = parts[2]  # 'cash' or 'upi'
    invoice_id = parts[3]
    
    await query.answer()
    
    # Load invoice
    invoices = load_invoices()
    invoice = next((inv for inv in invoices if inv.get("invoice_id") == invoice_id), None)
    
    if not invoice:
        await query.edit_message_text("❌ Invoice not found.")
        return
    
    # Update invoice status
    invoice["payment_status"] = "payment_rejected"
    invoice["payment_rejected_at"] = datetime.now().isoformat()
    invoice["rejected_by"] = admin_id
    
    for idx, inv in enumerate(invoices):
        if inv.get("invoice_id") == invoice_id:
            invoices[idx] = invoice
            break
    save_invoices(invoices)
    
    # Update admin message
    await query.edit_message_text(
        f"❌ *Payment Rejected*\n\n"
        f"Invoice ID: `{invoice_id}`\n"
        f"Amount: ₹{invoice['final_total']}\n"
        f"Payment Method: {payment_method.upper()}\n"
        f"Rejected by: Admin {admin_id}",
        parse_mode="Markdown"
    )
    
    # Notify user
    user_id = invoice.get("user_id")
    if user_id:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"❌ *Payment Not Verified*\n\n"
                    f"Invoice ID: `{invoice_id}`\n"
                    f"Amount: ₹{invoice['final_total']}\n\n"
                    f"Your payment could not be verified.\n"
                    f"Please contact the admin for more details."
                ),
                parse_mode="Markdown"
            )
            logger.info(f"[INVOICE_V2] payment_rejected_notification_sent user_id={user_id} invoice_id={invoice_id}")
        except Exception as e:
            logger.error(f"[INVOICE_V2] failed_notify_user_payment_rejected invoice_id={invoice_id} error={e}")
    
    logger.info(f"[INVOICE_V2] payment_rejected invoice_id={invoice_id} method={payment_method} admin={admin_id}")


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

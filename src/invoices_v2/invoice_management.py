"""
Invoice v2 - Management Flow (Search / View / Delete / Resend)

This module is isolated from the creation flow to avoid interference.
Callbacks use the prefix "inv_manage_" to prevent conflicts with existing
"inv2_*" callbacks.
"""
import json
import os
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes, ConversationHandler

from src.invoices_v2.state import InvoiceV2State

logger = logging.getLogger(__name__)

INVOICES_FILE = "data/invoices_v2.json"


def _ensure_invoices_file() -> None:
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(INVOICES_FILE):
        with open(INVOICES_FILE, "w") as f:
            json.dump([], f, indent=2)


def load_invoices() -> List[Dict]:
    _ensure_invoices_file()
    try:
        with open(INVOICES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_invoices(invoices: List[Dict]) -> None:
    _ensure_invoices_file()
    with open(INVOICES_FILE, "w") as f:
        json.dump(invoices, f, indent=2)


def _parse_invoice_date(invoice: Dict) -> Optional[datetime]:
    date_str = invoice.get("date") or ""
    created_at = invoice.get("created_at") or ""
    for raw in (date_str, created_at):
        if not raw:
            continue
        try:
            if len(raw) == 10:
                return datetime.strptime(raw, "%Y-%m-%d")
            return datetime.fromisoformat(raw)
        except Exception:
            continue
    return None


def _invoice_summary(invoice: Dict) -> str:
    invoice_id = invoice.get("invoice_id", "N/A")
    user_name = invoice.get("user_name", "Unknown")
    total = invoice.get("final_total", 0)
    date_str = invoice.get("date") or ""
    return f"{invoice_id} | {user_name} | ₹{total} | {date_str}"


def _find_invoice(invoice_id: str) -> Optional[Dict]:
    invoices = load_invoices()
    for inv in invoices:
        if str(inv.get("invoice_id", "")).upper() == invoice_id.upper():
            return inv
    return None


def _delete_invoice(invoice_id: str) -> bool:
    invoices = load_invoices()
    before = len(invoices)
    invoices = [inv for inv in invoices if str(inv.get("invoice_id", "")).upper() != invoice_id.upper()]
    if len(invoices) == before:
        return False
    save_invoices(invoices)
    return True


def _update_invoice_shipping(invoice_id: str, shipping: float) -> bool:
    invoices = load_invoices()
    updated = False
    for inv in invoices:
        if str(inv.get("invoice_id", "")).upper() == invoice_id.upper():
            inv["shipping"] = shipping
            items_subtotal = float(inv.get("items_subtotal", 0) or 0)
            gst_total = float(inv.get("gst_total", 0) or 0)
            inv["final_total"] = round(items_subtotal + gst_total + shipping, 2)
            updated = True
            break
    if updated:
        save_invoices(invoices)
    return updated


def _recalculate_item(item: Dict) -> Dict:
    try:
        from src.invoices_v2.utils import get_gst_config
        gst_config = get_gst_config()
    except Exception:
        gst_config = {"enabled": True, "mode": "exclusive"}

    rate = float(item.get("rate", 0) or 0)
    qty = int(item.get("quantity", 1) or 1)
    discount_percent = float(item.get("discount_percent", 0) or 0)
    gst_percent = float(item.get("gst_percent", 0) or 0)

    base = rate * qty
    discount_amount = base * discount_percent / 100
    taxable = base - discount_amount

    if gst_config.get("enabled"):
        if gst_config.get("mode") == "inclusive":
            gst_amount = taxable * gst_percent / (100 + gst_percent)
        else:
            gst_amount = taxable * gst_percent / 100
    else:
        gst_amount = 0

    item["base"] = round(base, 2)
    item["discount_amount"] = round(discount_amount, 2)
    item["taxable"] = round(taxable, 2)
    item["gst_amount"] = round(gst_amount, 2)
    item["line_total"] = round(taxable + gst_amount, 2)
    return item


def _recalculate_invoice(inv: Dict) -> Dict:
    items = inv.get("items", []) or []
    items = [_recalculate_item(dict(item)) for item in items]
    inv["items"] = items
    items_subtotal = sum(item.get("line_total", 0) for item in items)
    gst_total = sum(item.get("gst_amount", 0) for item in items)
    shipping = float(inv.get("shipping", 0) or 0)
    inv["items_subtotal"] = round(items_subtotal, 2)
    inv["gst_total"] = round(gst_total, 2)
    inv["final_total"] = round(items_subtotal + shipping, 2)
    return inv


def _update_invoice_items(invoice_id: str, items: List[Dict]) -> bool:
    invoices = load_invoices()
    updated = False
    for inv in invoices:
        if str(inv.get("invoice_id", "")).upper() == invoice_id.upper():
            inv["items"] = items
            _recalculate_invoice(inv)
            updated = True
            break
    if updated:
        save_invoices(invoices)
    return updated


def _search_by_user(term: str) -> List[Dict]:
    invoices = load_invoices()
    term_lower = term.lower().strip()
    results = []
    for inv in invoices:
        user_name = str(inv.get("user_name", "")).lower()
        user_id = str(inv.get("user_id", ""))
        if term_lower in user_name or term_lower == user_id:
            results.append(inv)
    return results


def _search_by_invoice_id(term: str) -> List[Dict]:
    invoices = load_invoices()
    term_upper = term.upper().strip()
    return [inv for inv in invoices if str(inv.get("invoice_id", "")).upper().startswith(term_upper)]


def _search_by_range(days: int) -> List[Dict]:
    invoices = load_invoices()
    cutoff = datetime.now() - timedelta(days=days)
    results = []
    for inv in invoices:
        dt = _parse_invoice_date(inv)
        if dt and dt >= cutoff:
            results.append(inv)
    return results


def _search_by_month() -> List[Dict]:
    invoices = load_invoices()
    now = datetime.now()
    results = []
    for inv in invoices:
        dt = _parse_invoice_date(inv)
        if dt and dt.year == now.year and dt.month == now.month:
            results.append(inv)
    return results


def _build_results_keyboard(invoices: List[Dict]) -> InlineKeyboardMarkup:
    rows = []
    for inv in invoices[:15]:
        inv_id = inv.get("invoice_id", "")
        label = _invoice_summary(inv)
        rows.append([InlineKeyboardButton(label, callback_data=f"inv_manage_view_{inv_id}")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="inv_manage_menu")])
    return InlineKeyboardMarkup(rows)


def _clear_inv_manage_context(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context or not getattr(context, "user_data", None):
        return
    for key in list(context.user_data.keys()):
        if key.startswith("inv_manage_"):
            context.user_data.pop(key, None)


def _resolve_telegram_user_id(invoice: Dict) -> Optional[int]:
    if not invoice:
        return None

    direct = _resolve_telegram_user_id_from_record(invoice)
    if direct:
        return direct

    username = _extract_username(invoice.get("user_name", ""))
    if not username:
        return None

    try:
        from src.invoices_v2.utils import search_users
        matches = search_users(username, limit=5) or []
        username_lower = username.lower()
        for match in matches:
            match_username = (match.get("username") or "").lstrip("@").lower()
            if match_username == username_lower:
                resolved = _resolve_telegram_user_id_from_record(match)
                if resolved:
                    invoice_id = invoice.get("invoice_id")
                    if invoice_id:
                        _update_invoice_telegram_id(invoice_id, resolved)
                    logger.info(
                        f"[INVOICE_MANAGE] resolved telegram_id via username invoice_id={invoice_id} telegram_id={resolved}"
                    )
                    return resolved

        if len(matches) == 1:
            resolved = _resolve_telegram_user_id_from_record(matches[0])
            if resolved:
                invoice_id = invoice.get("invoice_id")
                if invoice_id:
                    _update_invoice_telegram_id(invoice_id, resolved)
                logger.info(
                    f"[INVOICE_MANAGE] resolved telegram_id via single match invoice_id={invoice_id} telegram_id={resolved}"
                )
                return resolved
    except Exception as e:
        logger.warning(f"[INVOICE_MANAGE] telegram_id lookup failed: {e}")

    return None


def _extract_username(user_name: str) -> Optional[str]:
    if not user_name:
        return None
    match = re.search(r"@([A-Za-z0-9_]{3,})", user_name)
    return match.group(1) if match else None


def _resolve_telegram_user_id_from_record(record: Dict) -> Optional[int]:
    if not record:
        return None
    for key in ("telegram_id", "user_id"):
        value = record.get(key)
        if value is None:
            continue
        try:
            value_int = int(value)
            if value_int > 0:
                return value_int
        except (TypeError, ValueError):
            continue
    return None


def _update_invoice_telegram_id(invoice_id: str, telegram_id: int) -> None:
    invoices = load_invoices()
    updated = False
    for inv in invoices:
        if str(inv.get("invoice_id", "")).upper() == invoice_id.upper():
            inv["telegram_id"] = telegram_id
            updated = True
            break
    if updated:
        save_invoices(invoices)


async def show_invoice_main_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    note: Optional[str] = None
) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    text = "📄 *Invoice Menu*\n\n"
    if note:
        text += f"{note}\n\n"
    text += "Choose an option:"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Create Invoice", callback_data="inv2_create_start")],
        [InlineKeyboardButton("🔍 Search / Manage", callback_data="inv_manage_menu")],
        [InlineKeyboardButton("📋 Recent Invoices", callback_data="inv_manage_recent")],
        [InlineKeyboardButton("❌ Cancel", callback_data="inv2_cancel")],
        [InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="cmd_admin_back")],
    ])
    if query:
        await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.effective_user.send_message(text, reply_markup=kb, parse_mode="Markdown")
    return InvoiceV2State.INVOICE_MENU


async def handle_manage_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    text = "🔍 *Search / Manage Invoices*\n\nChoose search type:"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 By User", callback_data="inv_manage_by_user")],
        [InlineKeyboardButton("🧾 By Invoice No", callback_data="inv_manage_by_invoice")],
        [InlineKeyboardButton("🕒 Last 3 Days", callback_data="inv_manage_last_3")],
        [InlineKeyboardButton("📅 Last 7 Days", callback_data="inv_manage_last_7")],
        [InlineKeyboardButton("🗓️ This Month", callback_data="inv_manage_month")],
        [InlineKeyboardButton("⬅️ Back", callback_data="inv_manage_back")],
        [InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="cmd_admin_back")],
    ])
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    return InvoiceV2State.MANAGE_MENU


async def handle_manage_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    if query.data == "inv_manage_back":
        return await show_invoice_main_menu(update, context)

    if query.data == "inv_manage_recent":
        invoices = load_invoices()[-10:][::-1]
        if not invoices:
            await query.edit_message_text("❌ No invoices found.")
            return InvoiceV2State.MANAGE_MENU
        await query.edit_message_text(
            "📋 *Recent Invoices*\n\nSelect an invoice:",
            reply_markup=_build_results_keyboard(invoices),
            parse_mode="Markdown"
        )
        return InvoiceV2State.SEARCH_RESULTS

    if query.data == "inv_manage_by_user":
        context.user_data["inv_manage_search_type"] = "user"
        await query.edit_message_text("🔍 Enter user name or Telegram ID:")
        return InvoiceV2State.SEARCH_INVOICES

    if query.data == "inv_manage_by_invoice":
        context.user_data["inv_manage_search_type"] = "invoice"
        await query.edit_message_text("🔍 Enter invoice number (e.g. 6542F131):")
        return InvoiceV2State.SEARCH_INVOICES

    if query.data == "inv_manage_last_3":
        invoices = _search_by_range(3)
    elif query.data == "inv_manage_last_7":
        invoices = _search_by_range(7)
    elif query.data == "inv_manage_month":
        invoices = _search_by_month()
    else:
        invoices = []

    if not invoices:
        await query.edit_message_text("❌ No invoices found for this range.")
        return InvoiceV2State.MANAGE_MENU

    await query.edit_message_text(
        "📋 *Search Results*\n\nSelect an invoice:",
        reply_markup=_build_results_keyboard(invoices),
        parse_mode="Markdown"
    )
    return InvoiceV2State.SEARCH_RESULTS


async def handle_manage_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    term = update.message.text.strip()
    search_type = context.user_data.get("inv_manage_search_type")

    if search_type == "user":
        invoices = _search_by_user(term)
    elif search_type == "invoice":
        invoices = _search_by_invoice_id(term)
    else:
        invoices = []

    if not invoices:
        await update.effective_user.send_message("❌ No invoices found. Try again or /menu.")
        return InvoiceV2State.MANAGE_MENU

    await update.effective_user.send_message(
        "📋 *Search Results*\n\nSelect an invoice:",
        reply_markup=_build_results_keyboard(invoices),
        parse_mode="Markdown"
    )
    return InvoiceV2State.SEARCH_RESULTS


async def handle_manage_view_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    invoice_id = query.data.replace("inv_manage_view_", "").strip()
    invoice = _find_invoice(invoice_id)
    if not invoice:
        await query.edit_message_text("❌ Invoice not found.")
        return InvoiceV2State.MANAGE_MENU

    details = (
        f"🧾 *Invoice {invoice_id}*\n"
        f"User: {invoice.get('user_name', 'Unknown')}\n"
        f"Amount: ₹{invoice.get('final_total', 0)}\n"
        f"Date: {invoice.get('date', 'N/A')}\n"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Resend to User", callback_data=f"inv_manage_resend_{invoice_id}")],
        [InlineKeyboardButton("✏️ Edit Shipping", callback_data=f"inv_manage_edit_{invoice_id}")],
        [InlineKeyboardButton("🧩 Edit Items", callback_data=f"inv_manage_items_{invoice_id}")],
        [InlineKeyboardButton("➕ Add Item", callback_data=f"inv_manage_add_{invoice_id}")],
        [InlineKeyboardButton("🗑️ Delete Invoice", callback_data=f"inv_manage_delete_{invoice_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="inv_manage_menu")],
    ])
    await query.edit_message_text(details, reply_markup=kb, parse_mode="Markdown")
    return InvoiceV2State.VIEW_INVOICE


async def handle_manage_delete_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    invoice_id = query.data.replace("inv_manage_delete_", "").strip()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Delete", callback_data=f"inv_manage_confirm_delete_{invoice_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="inv_manage_menu")],
    ])
    await query.edit_message_text(
        f"⚠️ Are you sure you want to delete invoice {invoice_id}?",
        reply_markup=kb
    )
    return InvoiceV2State.CONFIRM_DELETE


async def handle_manage_confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    invoice_id = query.data.replace("inv_manage_confirm_delete_", "").strip()
    if _delete_invoice(invoice_id):
        note = f"✅ Invoice {invoice_id} deleted."
    else:
        note = f"❌ Invoice {invoice_id} not found."
    _clear_inv_manage_context(context)
    return await show_invoice_main_menu(update, context, note=note)


async def handle_manage_resend_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    invoice_id = query.data.replace("inv_manage_resend_", "").strip()
    invoice = _find_invoice(invoice_id)
    if not invoice:
        await query.edit_message_text("❌ Invoice not found.")
        return InvoiceV2State.MANAGE_MENU

    user_id = _resolve_telegram_user_id(invoice)
    if not user_id:
        await query.edit_message_text("❌ Unable to resolve Telegram user ID for this invoice.")
        return InvoiceV2State.MANAGE_MENU

    from src.invoices_v2.pdf import generate_invoice_pdf
    pdf_buffer = generate_invoice_pdf({
        "invoice_id": invoice_id,
        "date": invoice.get("date"),
        "user_name": invoice.get("user_name"),
        "user_id": user_id,
        "items": invoice.get("items", []),
        "items_subtotal": invoice.get("items_subtotal", 0),
        "shipping": invoice.get("shipping", 0),
        "gst_total": invoice.get("gst_total", 0),
        "final_total": invoice.get("final_total", 0),
    })

    # Create inline buttons for user actions
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    user_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Pay Bill", callback_data=f"inv2_pay_{invoice_id}")],
        [InlineKeyboardButton("❌ Reject Bill", callback_data=f"inv2_reject_{invoice_id}")]
    ])

    try:
        await context.bot.send_document(
            chat_id=user_id,
            document=InputFile(pdf_buffer, filename=f"invoice_{invoice_id}.pdf"),
            caption=f"✅ Invoice {invoice_id} (Resent)",
            reply_markup=user_kb,
        )
        await query.edit_message_text(f"✅ Invoice {invoice_id} resent to user.")
    except Exception as e:
        logger.error(f"[INVOICE_MANAGE] resend_failed invoice_id={invoice_id} user_id={user_id} error={e}")
        error_text = str(e)
        if "Chat not found" in error_text:
            await query.edit_message_text(
                "❌ Failed to resend: Chat not found.\n"
                "User likely hasn’t started the bot or the Telegram ID is invalid. "
                "Ask them to /start, then retry."
            )
        else:
            await query.edit_message_text(f"❌ Failed to resend: {e}")

    return InvoiceV2State.MANAGE_MENU


async def handle_manage_edit_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    invoice_id = query.data.replace("inv_manage_edit_", "").strip()
    context.user_data["inv_manage_edit_id"] = invoice_id
    await query.edit_message_text(
        f"✏️ Enter new *shipping* amount for invoice {invoice_id}:",
        parse_mode="Markdown"
    )
    return InvoiceV2State.EDIT_INVOICE


async def handle_manage_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    invoice_id = context.user_data.get("inv_manage_edit_id")
    try:
        shipping = float(text)
        if shipping < 0:
            raise ValueError("Negative shipping")
    except Exception:
        await update.effective_user.send_message("❌ Invalid amount. Please enter a valid number.")
        return InvoiceV2State.EDIT_INVOICE

    if not invoice_id:
        await update.effective_user.send_message("❌ Missing invoice context. Please start again.")
        return InvoiceV2State.MANAGE_MENU

    if _update_invoice_shipping(invoice_id, shipping):
        await update.effective_user.send_message(f"✅ Invoice {invoice_id} updated. Shipping = ₹{shipping}")
    else:
        await update.effective_user.send_message(f"❌ Invoice {invoice_id} not found.")
    return InvoiceV2State.MANAGE_MENU


async def handle_manage_items_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    invoice_id = query.data.replace("inv_manage_items_", "").strip()
    invoice = _find_invoice(invoice_id)
    if not invoice:
        await query.edit_message_text("❌ Invoice not found.")
        return InvoiceV2State.MANAGE_MENU

    items = invoice.get("items", []) or []
    if not items:
        await query.edit_message_text("❌ No items in this invoice.")
        return InvoiceV2State.MANAGE_MENU

    rows = []
    for idx, item in enumerate(items):
        name = item.get("name", "Item")
        rows.append([InlineKeyboardButton(f"{idx + 1}. {name}", callback_data=f"inv_manage_item_{invoice_id}_{idx}")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="inv_manage_menu")])
    await query.edit_message_text(
        f"🧩 *Edit Items*\n\nSelect item to edit:",
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode="Markdown"
    )
    return InvoiceV2State.EDIT_ITEM_SELECT


async def handle_manage_item_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    parts = query.data.replace("inv_manage_item_", "").split("_")
    if len(parts) < 2:
        await query.edit_message_text("❌ Invalid item selection.")
        return InvoiceV2State.MANAGE_MENU

    invoice_id = parts[0]
    item_index = int(parts[1])
    invoice = _find_invoice(invoice_id)
    if not invoice:
        await query.edit_message_text("❌ Invoice not found.")
        return InvoiceV2State.MANAGE_MENU

    items = invoice.get("items", []) or []
    if item_index < 0 or item_index >= len(items):
        await query.edit_message_text("❌ Invalid item index.")
        return InvoiceV2State.MANAGE_MENU

    item = items[item_index]
    context.user_data["inv_manage_edit_invoice_id"] = invoice_id
    context.user_data["inv_manage_edit_item_index"] = item_index

    details = (
        f"🧾 *Edit Item*\n"
        f"Name: {item.get('name')}\n"
        f"Rate: {item.get('rate')}\n"
        f"Qty: {item.get('quantity')}\n"
        f"Discount %: {item.get('discount_percent', 0)}\n"
        f"GST %: {item.get('gst_percent', 0)}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Name", callback_data="inv_manage_field_name")],
        [InlineKeyboardButton("✏️ Rate", callback_data="inv_manage_field_rate")],
        [InlineKeyboardButton("✏️ Qty", callback_data="inv_manage_field_qty")],
        [InlineKeyboardButton("✏️ Discount %", callback_data="inv_manage_field_discount")],
        [InlineKeyboardButton("✏️ GST %", callback_data="inv_manage_field_gst")],
        [InlineKeyboardButton("🗑️ Remove Item", callback_data="inv_manage_item_remove")],
        [InlineKeyboardButton("⬅️ Back", callback_data=f"inv_manage_items_{invoice_id}")],
    ])
    await query.edit_message_text(details, reply_markup=kb, parse_mode="Markdown")
    return InvoiceV2State.EDIT_ITEM_FIELD


async def handle_manage_item_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    invoice_id = context.user_data.get("inv_manage_edit_invoice_id")
    item_index = context.user_data.get("inv_manage_edit_item_index")
    if query.data == "inv_manage_item_remove":
        invoice = _find_invoice(invoice_id)
        if not invoice:
            await query.edit_message_text("❌ Invoice not found.")
            return InvoiceV2State.MANAGE_MENU
        items = invoice.get("items", []) or []
        if item_index is None or item_index >= len(items):
            await query.edit_message_text("❌ Invalid item index.")
            return InvoiceV2State.MANAGE_MENU
        items.pop(item_index)
        _update_invoice_items(invoice_id, items)
        await query.edit_message_text("✅ Item removed.")
        return InvoiceV2State.MANAGE_MENU

    field_map = {
        "inv_manage_field_name": "name",
        "inv_manage_field_rate": "rate",
        "inv_manage_field_qty": "quantity",
        "inv_manage_field_discount": "discount_percent",
        "inv_manage_field_gst": "gst_percent",
    }
    field = field_map.get(query.data)
    if not field:
        await query.edit_message_text("❌ Invalid field.")
        return InvoiceV2State.MANAGE_MENU

    context.user_data["inv_manage_edit_field"] = field
    await query.edit_message_text(f"✏️ Enter new value for *{field}*:", parse_mode="Markdown")
    return InvoiceV2State.EDIT_ITEM_VALUE


async def handle_manage_item_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    invoice_id = context.user_data.get("inv_manage_edit_invoice_id")
    item_index = context.user_data.get("inv_manage_edit_item_index")
    field = context.user_data.get("inv_manage_edit_field")

    invoice = _find_invoice(invoice_id)
    if not invoice:
        await update.effective_user.send_message("❌ Invoice not found.")
        return InvoiceV2State.MANAGE_MENU

    items = invoice.get("items", []) or []
    if item_index is None or item_index >= len(items):
        await update.effective_user.send_message("❌ Invalid item index.")
        return InvoiceV2State.MANAGE_MENU

    if field == "name":
        items[item_index][field] = text
    else:
        try:
            value = float(text) if field in ("rate", "discount_percent", "gst_percent") else int(text)
        except Exception:
            await update.effective_user.send_message("❌ Invalid value. Try again.")
            return InvoiceV2State.EDIT_ITEM_VALUE
        items[item_index][field] = value

    _update_invoice_items(invoice_id, items)
    await update.effective_user.send_message("✅ Item updated.")
    return InvoiceV2State.MANAGE_MENU


async def handle_manage_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    invoice_id = query.data.replace("inv_manage_add_", "").strip()
    context.user_data["inv_manage_add_invoice_id"] = invoice_id
    context.user_data["inv_manage_add_item"] = {}
    await query.edit_message_text("➕ Enter item *name*:", parse_mode="Markdown")
    return InvoiceV2State.ADD_ITEM_NAME


async def handle_manage_add_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["inv_manage_add_item"]["name"] = update.message.text.strip()
    await update.effective_user.send_message("➕ Enter item *rate*:", parse_mode="Markdown")
    return InvoiceV2State.ADD_ITEM_RATE


async def handle_manage_add_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        rate = float(update.message.text.strip())
    except Exception:
        await update.effective_user.send_message("❌ Invalid rate. Try again.")
        return InvoiceV2State.ADD_ITEM_RATE
    context.user_data["inv_manage_add_item"]["rate"] = rate
    await update.effective_user.send_message("➕ Enter item *quantity*:", parse_mode="Markdown")
    return InvoiceV2State.ADD_ITEM_QTY


async def handle_manage_add_qty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        qty = int(update.message.text.strip())
        if qty <= 0:
            raise ValueError("qty")
    except Exception:
        await update.effective_user.send_message("❌ Invalid quantity. Try again.")
        return InvoiceV2State.ADD_ITEM_QTY
    context.user_data["inv_manage_add_item"]["quantity"] = qty
    await update.effective_user.send_message("➕ Enter item *discount %* (0-80):", parse_mode="Markdown")
    return InvoiceV2State.ADD_ITEM_DISCOUNT


async def handle_manage_add_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        discount = float(update.message.text.strip())
        if not (0 <= discount <= 80):
            raise ValueError("discount")
    except Exception:
        await update.effective_user.send_message("❌ Invalid discount. Try again.")
        return InvoiceV2State.ADD_ITEM_DISCOUNT
    context.user_data["inv_manage_add_item"]["discount_percent"] = discount
    await update.effective_user.send_message("➕ Enter item *GST %*:", parse_mode="Markdown")
    return InvoiceV2State.ADD_ITEM_GST


async def handle_manage_add_gst(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        gst = float(update.message.text.strip())
        if gst < 0:
            raise ValueError("gst")
    except Exception:
        await update.effective_user.send_message("❌ Invalid GST. Try again.")
        return InvoiceV2State.ADD_ITEM_GST
    context.user_data["inv_manage_add_item"]["gst_percent"] = gst

    invoice_id = context.user_data.get("inv_manage_add_invoice_id")
    invoice = _find_invoice(invoice_id)
    if not invoice:
        await update.effective_user.send_message("❌ Invoice not found.")
        return InvoiceV2State.MANAGE_MENU

    items = invoice.get("items", []) or []
    new_item = context.user_data.get("inv_manage_add_item", {})
    new_item.setdefault("quantity", 1)
    new_item.setdefault("discount_percent", 0)
    new_item.setdefault("gst_percent", 0)
    items.append(new_item)
    _update_invoice_items(invoice_id, items)

    await update.effective_user.send_message("✅ Item added.")
    return InvoiceV2State.MANAGE_MENU


async def handle_admin_delete_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    invoice_id = query.data.replace("inv2_delete_", "").strip()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Delete", callback_data=f"inv_manage_confirm_delete_{invoice_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="inv_manage_menu")],
    ])
    await query.edit_message_text(
        f"⚠️ Confirm delete invoice {invoice_id}?",
        reply_markup=kb
    )
    return ConversationHandler.END


async def handle_admin_resend_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    query.data = query.data.replace("inv2_resend_", "inv_manage_resend_")
    return await handle_manage_resend_invoice(update, context)

import logging
from src.utils.user_registry import search_registry

logger = logging.getLogger(__name__)


def search_users(term: str):
    logger.info(f"[INVOICE] user_search term='{term}'")
    return search_registry(term, limit=10)


def format_invoice_text(invoice: dict) -> str:
    lines = []
    lines.append(f"Invoice: {invoice.get('invoice_id')}")
    lines.append(f"Status: {invoice.get('status')}")
    lines.append(f"User ID: {invoice.get('user_id')}")
    lines.append("")
    lines.append("Items:")
    for it in invoice.get('items', []):
        lines.append(f"- {it.get('name')} | {it.get('qty')} × {it.get('rate')} = {it.get('line_total')}")
    lines.append("")
    lines.append(f"Subtotal: {invoice.get('subtotal')}")
    lines.append(f"GST: {invoice.get('gst')}")
    lines.append(f"Shipping: {invoice.get('shipping')}")
    lines.append(f"Total: {invoice.get('total')}")
    return "\n".join(lines)

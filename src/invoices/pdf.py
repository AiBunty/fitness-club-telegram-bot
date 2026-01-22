import logging
from io import BytesIO

logger = logging.getLogger(__name__)


def generate_invoice_pdf_bytes(invoice: dict) -> BytesIO:
    """Generate a PDF for invoice. Uses reportlab if available, else falls back to plain text named .pdf."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        bio = BytesIO()
        c = canvas.Canvas(bio, pagesize=A4)
        x = 40
        y = 800
        c.setFont('Helvetica-Bold', 14)
        c.drawString(x, y, f"Invoice: {invoice.get('invoice_id')}")
        y -= 24
        c.setFont('Helvetica', 10)
        for line in _invoice_lines(invoice):
            c.drawString(x, y, line)
            y -= 14
            if y < 40:
                c.showPage()
                y = 800
        c.save()
        bio.seek(0)
        logger.info(f"[INVOICE] pdf_generated id={invoice.get('invoice_id')}")
        return bio
    except Exception as e:
        logger.warning(f"[INVOICE] reportlab unavailable or failed: {e} — falling back to text PDF")
        # Fallback: generate simple byte stream with text and return as .pdf (Telegram will accept as file)
        bio = BytesIO()
        text = "\n".join(_invoice_lines(invoice))
        bio.write(text.encode('utf-8'))
        bio.seek(0)
        return bio


def _invoice_lines(invoice: dict):
    lines = []
    lines.append(f"Invoice: {invoice.get('invoice_id')}")
    lines.append(f"Status: {invoice.get('status')}")
    lines.append(f"User ID: {invoice.get('user_id')}")
    lines.append("")
    lines.append("Items:")
    for it in invoice.get('items', []):
        lines.append(f"- {it.get('name')} | {it.get('qty')} x {it.get('rate')} = {it.get('line_total')}")
    lines.append("")
    lines.append(f"Subtotal: {invoice.get('subtotal')}")
    lines.append(f"GST: {invoice.get('gst')}")
    lines.append(f"Shipping: {invoice.get('shipping')}")
    lines.append(f"Total: {invoice.get('total')}")
    return lines

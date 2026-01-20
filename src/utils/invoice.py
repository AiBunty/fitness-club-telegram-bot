import io
from typing import Dict, Any, List
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from datetime import datetime


def _draw_header(c: canvas.Canvas, profile: Dict[str, Any]):
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30 * mm, A4[1] - 30 * mm, profile.get('name', ''))
    c.setFont("Helvetica", 9)
    text = profile.get('address', '')
    y = A4[1] - 36 * mm
    for line in text.split('\n'):
        c.drawString(30 * mm, y, line)
        y -= 4 * mm
    phone = profile.get('phone')
    if phone:
        c.drawString(30 * mm, y, f"📞 {phone}")
        y -= 4 * mm
    gst = profile.get('gst')
    if gst:
        c.drawString(30 * mm, y, f"GST: {gst}")
        y -= 4 * mm


def generate_invoice_pdf(invoice: Dict[str, Any], profile: Dict[str, Any]) -> io.BytesIO:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    _draw_header(c, profile)

    # Invoice meta
    c.setFont("Helvetica-Bold", 12)
    c.drawString(140 * mm, A4[1] - 30 * mm, f"INVOICE #: {invoice.get('invoice_no')}")
    c.setFont("Helvetica", 9)
    c.drawString(140 * mm, A4[1] - 35 * mm, f"DATE: {invoice.get('date')}")

    # Billed to
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30 * mm, A4[1] - 60 * mm, "BILLED TO:")
    c.setFont("Helvetica", 9)
    billed = invoice.get('billed_to', {})
    y = A4[1] - 66 * mm
    c.drawString(30 * mm, y, f"Name: {billed.get('name','')}")
    y -= 5 * mm
    c.drawString(30 * mm, y, f"Telegram ID: {billed.get('telegram_id','')}")

    # Items table
    items: List[Dict[str, Any]] = invoice.get('items', [])
    table_data = [["Item", "Amount (₹)"]]
    for it in items:
        table_data.append([it.get('name', ''), f"{float(it.get('amount',0)):.2f}"])
    # Totals
    subtotal = sum(float(it.get('amount', 0)) for it in items)
    table_data.append(["Subtotal", f"{subtotal:.2f}"])
    table_data.append(["Total", f"{invoice.get('total', subtotal):.2f}"])

    table = Table(table_data, colWidths=[120 * mm, 40 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))

    w, h = table.wrapOn(c, A4[0] - 60 * mm, A4[1])
    table.drawOn(c, 30 * mm, A4[1] - 120 * mm - h)

    # Status and footer
    status = invoice.get('status', 'UNPAID').upper()
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30 * mm, A4[1] - 140 * mm - h, f"STATUS: {status}")

    # Timings footer
    c.setFont("Helvetica", 8)
    footer = profile.get('timings','')
    c.drawString(30 * mm, 20 * mm, footer)
    c.drawRightString(A4[0] - 30 * mm, 20 * mm, "This is a system-generated invoice")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def generate_receipt_pdf(receipt: Dict[str, Any], profile: Dict[str, Any]) -> io.BytesIO:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    _draw_header(c, profile)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(140 * mm, A4[1] - 30 * mm, f"RECEIPT #: {receipt.get('receipt_no')}")
    c.setFont("Helvetica", 9)
    c.drawString(140 * mm, A4[1] - 35 * mm, f"DATE: {receipt.get('date')}")

    billed = receipt.get('billed_to', {})
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30 * mm, A4[1] - 60 * mm, "Received From:")
    c.setFont("Helvetica", 9)
    c.drawString(30 * mm, A4[1] - 66 * mm, f"Name: {billed.get('name','')}")
    c.drawString(30 * mm, A4[1] - 72 * mm, f"Telegram ID: {billed.get('telegram_id','')}")

    # Payment breakdown
    methods = receipt.get('methods', {})
    y = A4[1] - 96 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30 * mm, y, "PAYMENT DETAILS")
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    for m, amt in methods.items():
        c.drawString(30 * mm, y, f"{m.upper():<20} ₹{float(amt):.2f}")
        y -= 5 * mm

    total = receipt.get('total_paid', 0)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30 * mm, y - 4 * mm, f"TOTAL PAID: ₹{float(total):.2f}")
    c.drawString(30 * mm, y - 12 * mm, f"BALANCE: ₹{float(receipt.get('balance',0)):.2f}")

    c.setFont("Helvetica", 8)
    c.drawString(30 * mm, 20 * mm, profile.get('timings',''))
    c.drawRightString(A4[0] - 30 * mm, 20 * mm, "Payment Received Successfully")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

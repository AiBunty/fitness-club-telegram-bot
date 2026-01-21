"""
Invoice v2 - PDF Generation (Invoice & Receipt)
"""
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors


def generate_invoice_pdf(invoice_data: dict) -> BytesIO:
    """
    Generate invoice PDF with 7-column table:
    | Item | Qty | Rate | Discount % | Taxable | GST | Total |
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=12,
        alignment=1  # center
    )
    style_normal = styles['Normal']
    style_small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=9)
    
    elements = []
    
    # Title
    elements.append(Paragraph("INVOICE", style_title))
    elements.append(Spacer(1, 0.1*inch))
    
    # Invoice header info
    header_info = [
        f"Invoice ID: {invoice_data.get('invoice_id', 'N/A')}",
        f"Date: {invoice_data.get('date', datetime.now().strftime('%Y-%m-%d'))}",
        f"User: {invoice_data.get('user_name', 'N/A')}",
        f"User ID: {invoice_data.get('user_id', 'N/A')}"
    ]
    
    for line in header_info:
        elements.append(Paragraph(line, style_small))
    
    elements.append(Spacer(1, 0.15*inch))
    
    # Items table
    table_data = [
        ["Item Name", "Qty", "Rate", "Discount %", "Taxable", "GST", "Total"]
    ]
    
    for item in invoice_data.get("items", []):
        table_data.append([
            item.get("name", ""),
            str(item.get("quantity", 0)),
            f"₹{item.get('rate', 0):.2f}",
            f"{item.get('discount_percent', 0):.1f}%",
            f"₹{item.get('taxable', 0):.2f}",
            f"₹{item.get('gst_amount', 0):.2f}",
            f"₹{item.get('line_total', 0):.2f}"
        ])
    
    # Footer rows
    items_total = invoice_data.get("items_subtotal", 0)
    shipping = invoice_data.get("shipping", 0)
    gst_total = invoice_data.get("gst_total", 0)
    final_total = invoice_data.get("final_total", 0)
    
    table_data.append([""] * 7)  # Blank row
    table_data.append(["Items Subtotal", "", "", "", "", "", f"₹{items_total:.2f}"])
    table_data.append(["Shipping/Delivery", "", "", "", "", "", f"₹{shipping:.2f}"])
    table_data.append(["GST Total", "", "", "", "", "", f"₹{gst_total:.2f}"])
    table_data.append(["FINAL TOTAL", "", "", "", "", "", f"₹{final_total:.2f}"])
    
    # Create table
    table = Table(table_data, colWidths=[50*mm, 15*mm, 20*mm, 20*mm, 25*mm, 20*mm, 25*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -6), 1, colors.black),
        ('FONTNAME', (0, -5), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e6f0ff')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#1f4788')),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('ALIGN', (0, 1), (-3, -6), 'CENTER'),
        ('ALIGN', (-3, 1), (-1, -6), 'RIGHT'),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Footer
    elements.append(Paragraph("Thank you for your business!", style_small))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_receipt_pdf(receipt_data: dict) -> BytesIO:
    """
    Generate receipt PDF (same format as invoice)
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=12,
        alignment=1
    )
    style_normal = styles['Normal']
    style_small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=9)
    
    elements = []
    
    # Title
    elements.append(Paragraph("RECEIPT", style_title))
    elements.append(Spacer(1, 0.1*inch))
    
    # Receipt header info
    header_info = [
        f"Invoice ID: {receipt_data.get('invoice_id', 'N/A')}",
        f"Receipt ID: {receipt_data.get('receipt_id', 'N/A')}",
        f"Date: {receipt_data.get('date', datetime.now().strftime('%Y-%m-%d'))}",
        f"User: {receipt_data.get('user_name', 'N/A')}",
        f"User ID: {receipt_data.get('user_id', 'N/A')}"
    ]
    
    for line in header_info:
        elements.append(Paragraph(line, style_small))
    
    elements.append(Spacer(1, 0.15*inch))
    
    # Items table (same as invoice)
    table_data = [
        ["Item Name", "Qty", "Rate", "Discount %", "Taxable", "GST", "Total"]
    ]
    
    for item in receipt_data.get("items", []):
        table_data.append([
            item.get("name", ""),
            str(item.get("quantity", 0)),
            f"₹{item.get('rate', 0):.2f}",
            f"{item.get('discount_percent', 0):.1f}%",
            f"₹{item.get('taxable', 0):.2f}",
            f"₹{item.get('gst_amount', 0):.2f}",
            f"₹{item.get('line_total', 0):.2f}"
        ])
    
    # Footer rows
    items_total = receipt_data.get("items_subtotal", 0)
    shipping = receipt_data.get("shipping", 0)
    gst_total = receipt_data.get("gst_total", 0)
    final_total = receipt_data.get("final_total", 0)
    
    table_data.append([""] * 7)
    table_data.append(["Items Subtotal", "", "", "", "", "", f"₹{items_total:.2f}"])
    table_data.append(["Shipping/Delivery", "", "", "", "", "", f"₹{shipping:.2f}"])
    table_data.append(["GST Total", "", "", "", "", "", f"₹{gst_total:.2f}"])
    table_data.append(["AMOUNT PAID", "", "", "", "", "", f"₹{final_total:.2f}"])
    
    table = Table(table_data, colWidths=[50*mm, 15*mm, 20*mm, 20*mm, 25*mm, 20*mm, 25*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -6), 1, colors.black),
        ('FONTNAME', (0, -5), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d4edda')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#155724')),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('ALIGN', (0, 1), (-3, -6), 'CENTER'),
        ('ALIGN', (-3, 1), (-1, -6), 'RIGHT'),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Footer
    elements.append(Paragraph("Payment received. Thank you!", style_small))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

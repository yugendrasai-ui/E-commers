from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO

def generate_pdf(order, items):
    """
    Generates a professional PDF invoice using reportlab.
    Args:
        order: SQLite Row or dict containing 'order_id', 'amount', 'created_at', 'address'
        items: List of SQLite Rows or dicts containing 'product_name', 'price', 'quantity'
    Returns:
        BytesIO: PDF buffer
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    elements = []

    styles = getSampleStyleSheet()
    
    # Custom styles
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Heading1'], fontSize=24, spaceAfter=20, textColor=colors.HexColor("#2874f0"))
    normal_style = styles['Normal']
    bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold')

    # Header
    elements.append(Paragraph("INVOICE", header_style))
    elements.append(Paragraph(f"<b>Order ID:</b> #{order['order_id']}", normal_style))
    elements.append(Paragraph(f"<b>Date:</b> {order['created_at']}", normal_style))
    elements.append(Spacer(1, 20))

    # Delivery Address
    elements.append(Paragraph("<b>Delivery Address:</b>", bold_style))
    elements.append(Paragraph(order['address'].replace('\n', '<br/>'), normal_style))
    elements.append(Spacer(1, 30))

    # Table Header
    data = [["Product", "Price", "Quantity", "Subtotal"]]
    
    # Table Data
    for item in items:
        # Handle decimal/float prices
        price = float(item['price'])
        qty = int(item['quantity'])
        subtotal = price * qty
        data.append([
            item['product_name'],
            f"INR {price:,.2f}",
            str(qty),
            f"INR {subtotal:,.2f}"
        ])

    # Table Styling
    table = Table(data, colWidths=[250, 100, 70, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#172337")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Left align product names
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))

    # Grand Total
    elements.append(Paragraph(f"<b>Grand Total: INR {float(order['amount']):,.2f}</b>", ParagraphStyle('TotalStyle', parent=styles['Normal'], fontSize=14, alignment=2)))

    # Footer
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("Thank you for shopping with Express-Kart!", ParagraphStyle('FooterStyle', parent=styles['Normal'], alignment=1, textColor=colors.grey)))

    doc.build(elements)
    buffer.seek(0)
    return buffer

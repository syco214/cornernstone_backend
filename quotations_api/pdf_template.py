from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, 
    PageBreak, ListFlowable, ListItem
)
from reportlab.platypus.flowables import KeepTogether
from io import BytesIO
from django.conf import settings
import os
from decimal import Decimal
from datetime import datetime

def format_currency(amount, currency):
    """Format amount with appropriate currency symbol"""
    if not amount:
        return "0.00"
    
    symbols = {
        'USD': '$',
        'EURO': '€',
        'RMB': '¥',
        'PHP': '₱'
    }
    
    symbol = symbols.get(currency, '')
    return f"{symbol}{amount:,.2f}"

def generate_quotation_pdf(quotation):
    """
    Generate a PDF document for a quotation
    
    Args:
        quotation: Quotation model instance
    
    Returns:
        BytesIO: PDF file as a buffer
    """
    buffer = BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=25*mm,
        leftMargin=25*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
        title=f"Quotation {quotation.quote_number}"
    )
    
    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='CenterHeading',
        parent=styles['Heading1'],
        alignment=1,  # Center alignment
    ))
    styles.add(ParagraphStyle(
        name='RightAligned',
        parent=styles['Normal'],
        alignment=2,  # Right alignment
    ))
    styles.add(ParagraphStyle(
        name='SmallText',
        parent=styles['Normal'],
        fontSize=8,
    ))
    styles.add(ParagraphStyle(
        name='Bold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
    ))
    
    # Define styles for the table cells
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        alignment=2,  # Right aligned
    )
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        alignment=0,  # Left aligned
        wordWrap='CJK',  # Enable word wrapping
    )
    
    # Content elements
    elements = []
    
    # Company logo
    logo_path = os.path.join(settings.STATIC_ROOT, 'images', 'company_logo.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=2*inch, height=0.75*inch)
        elements.append(logo)
    
    # Quotation header
    elements.append(Paragraph(f"QUOTATION", styles['CenterHeading']))
    elements.append(Spacer(1, 10*mm))
    
    # Quotation details
    quotation_info = [
        [Paragraph('Quotation Number:', label_style), Paragraph(quotation.quote_number, value_style)],
        [Paragraph('Date:', label_style), Paragraph(quotation.date.strftime('%d %b %Y'), value_style)],
        [Paragraph('Expiry Date:', label_style), Paragraph(quotation.expiry_date.strftime('%d %b %Y'), value_style)],
        [Paragraph('Currency:', label_style), Paragraph(quotation.currency, value_style)],
    ]
    
    if quotation.purchase_request:
        quotation_info.append([
            Paragraph('Purchase Request:', label_style), 
            Paragraph(quotation.purchase_request, value_style)
        ])
    
    # Customer information
    customer = quotation.customer
    customer_info = [
        [Paragraph('Customer:', label_style), Paragraph(customer.name, value_style)],
        [Paragraph('Registered Name:', label_style), Paragraph(customer.registered_name, value_style)],
        [Paragraph('Address:', label_style), Paragraph(customer.company_address, value_style)],
        [Paragraph('City:', label_style), Paragraph(customer.city, value_style)],
        [Paragraph('TIN:', label_style), Paragraph(customer.tin or 'N/A', value_style)],
        [Paragraph('Phone:', label_style), Paragraph(customer.phone_number, value_style)],
    ]
    
    # If the customer has contacts, add the primary contact
    try:
        primary_contact = customer.contacts.first()
        if primary_contact:
            customer_info.append([
                Paragraph('Contact Person:', label_style), 
                Paragraph(primary_contact.contact_person, value_style)
            ])
            customer_info.append([
                Paragraph('Position:', label_style), 
                Paragraph(primary_contact.position, value_style)
            ])
            customer_info.append([
                Paragraph('Department:', label_style), 
                Paragraph(primary_contact.department, value_style)
            ])
            customer_info.append([
                Paragraph('Email:', label_style), 
                Paragraph(primary_contact.email, value_style)
            ])
            customer_info.append([
                Paragraph('Mobile:', label_style), 
                Paragraph(primary_contact.mobile_number, value_style)
            ])
    except:
        pass
    
    # Update the table styles with appropriate column widths
    customer_table = Table(customer_info, colWidths=[120, 300])
    customer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    # Similarly for the quotation info table
    quotation_table = Table(quotation_info, colWidths=[120, 200])
    quotation_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    # Combine quotation and customer info into a table
    data = []
    for i in range(max(len(quotation_info), len(customer_info))):
        row = []
        if i < len(quotation_info):
            row.extend(quotation_info[i])
        else:
            row.extend(['', ''])
        
        # Add spacing between columns
        row.append('')
        
        if i < len(customer_info):
            row.extend(customer_info[i])
        else:
            row.extend(['', ''])
        
        data.append(row)
    
    # Create table for header information
    header_table = Table(data, colWidths=[80, 150, 20, 80, 150])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10*mm))
    
    # Contact persons
    if quotation.contacts.exists():
        elements.append(Paragraph("Contact Persons:", styles['Bold']))
        contact_data = []
        
        for contact in quotation.contacts.all():
            if contact.customer_contact:
                cc = contact.customer_contact
                contact_data.append([
                    cc.contact_person,
                    cc.position or '',
                    cc.email or '',
                    cc.mobile_number or ''
                ])
        
        if contact_data:
            contact_table = Table(contact_data, colWidths=[120, 100, 150, 100])
            contact_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(contact_table)
            elements.append(Spacer(1, 5*mm))
    
    # Sales agent
    main_agent = quotation.sales_agents.filter(role='main').first()
    if main_agent:
        elements.append(Paragraph(f"Sales Representative: {main_agent.agent_name}", styles['Normal']))
        elements.append(Spacer(1, 5*mm))
    
    # Items table
    elements.append(Paragraph("Items:", styles['Bold']))
    
    # Table header
    items_header = ['No.', 'Item Code', 'Description', 'Qty', 'Unit', 'Unit Price', 'Total']
    
    # Get additional controls
    try:
        controls = quotation.additional_controls
        show_all_photos = not controls.do_not_show_all_photos
        highlight_notes = controls.highlight_item_notes
    except:
        show_all_photos = False
        highlight_notes = True
    
    # Table data
    items_data = [items_header]
    
    for idx, item in enumerate(quotation.items.all(), 1):
        description_parts = []
        
        # Product name
        description_parts.append(item.inventory.product_name)
        
        # External description
        if item.external_description:
            description_parts.append(item.external_description)
        
        # Brand and Made in
        if item.show_brand and item.inventory.brand:
            description_parts.append(f"Brand: {item.inventory.brand.name}")
        
        if item.show_made_in and item.inventory.brand and item.inventory.brand.made_in:
            description_parts.append(f"Made in: {item.inventory.brand.made_in}")
        
        # Notes (highlighted if needed)
        if item.notes:
            if highlight_notes:
                description_parts.append(f"<b>Notes: {item.notes}</b>")
            else:
                description_parts.append(f"Notes: {item.notes}")
        
        # Join all description parts
        description = "<br/>".join(description_parts)
        
        # Format the row
        row = [
            str(idx),
            item.inventory.item_code,
            Paragraph(description, styles['Normal']),
            str(item.quantity),
            item.unit,
            format_currency(item.net_selling, quotation.currency),
            format_currency(item.total_selling, quotation.currency)
        ]
        
        items_data.append(row)
        
        # Add photo if needed
        if item.show_photo and item.photo and show_all_photos:
            photo_row = ['', '', Image(item.photo.path, width=2*inch, height=2*inch), '', '', '', '']
            items_data.append(photo_row)
    
    # Add total row
    items_data.append(['', '', '', '', '', 'Total:', format_currency(quotation.total_amount, quotation.currency)])
    
    # Create items table
    col_widths = [20, 70, 220, 30, 40, 70, 70]
    items_table = Table(items_data, colWidths=col_widths, repeatRows=1)
    
    # Style the table
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (3, 1), (6, -1), 'RIGHT'),
    ]
    
    # Style the total row
    total_row_index = len(items_data) - 1
    table_style.extend([
        ('FONTNAME', (5, total_row_index), (6, total_row_index), 'Helvetica-Bold'),
        ('LINEABOVE', (5, total_row_index), (6, total_row_index), 1, colors.black),
    ])
    
    items_table.setStyle(TableStyle(table_style))
    elements.append(items_table)
    elements.append(Spacer(1, 10*mm))
    
    # Terms and conditions
    try:
        terms = quotation.terms_and_conditions
        if terms:
            elements.append(Paragraph("Terms and Conditions:", styles['Bold']))
            elements.append(Spacer(1, 3*mm))
            
            terms_list = []
            
            if terms.price:
                terms_list.append(ListItem(Paragraph(f"<b>Price:</b> {terms.price}", styles['Normal'])))
            
            if terms.payment:
                terms_list.append(ListItem(Paragraph(f"<b>Payment:</b> {terms.payment.text}", styles['Normal'])))
            
            if terms.delivery:
                terms_list.append(ListItem(Paragraph(f"<b>Delivery:</b> {terms.delivery.text}", styles['Normal'])))
            
            if terms.validity:
                terms_list.append(ListItem(Paragraph(f"<b>Validity:</b> {terms.validity}", styles['Normal'])))
            
            if terms.other:
                terms_list.append(ListItem(Paragraph(f"<b>Other:</b> {terms.other.text}", styles['Normal'])))
            
            if terms_list:
                elements.append(ListFlowable(terms_list, bulletType='bullet', leftIndent=20))
    except:
        pass
    
    # Additional clauses based on controls
    try:
        if quotation.additional_controls.show_devaluation_clause:
            elements.append(Spacer(1, 5*mm))
            elements.append(Paragraph("Devaluation Clause:", styles['Bold']))
            devaluation_text = (
                "In the event of a significant currency devaluation (>3%) between the date of this "
                "quotation and the date of payment, we reserve the right to adjust pricing accordingly."
            )
            elements.append(Paragraph(devaluation_text, styles['Normal']))
    except:
        pass
    
    # Notes
    if quotation.notes:
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph("Additional Notes:", styles['Bold']))
        elements.append(Paragraph(quotation.notes, styles['Normal']))
    
    # Footer with signature
    elements.append(Spacer(1, 20*mm))
    elements.append(Paragraph("For and on behalf of:", styles['Normal']))
    elements.append(Spacer(1, 15*mm))
    
    # Signature line
    signature_data = [
        ['_______________________', '_______________________'],
        ['Authorized Signature', 'Customer Acceptance'],
    ]
    signature_table = Table(signature_data, colWidths=[200, 200])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(signature_table)
    
    # Build the PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer
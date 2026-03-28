#!/usr/bin/env python
"""Generate a PDF catalog with one product per page in table format."""
import csv
from pathlib import Path

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, PageBreak, Spacer
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
except ImportError:
    raise SystemExit("reportlab is required. Install it with: .venv\\Scripts\\pip install reportlab")


def generate_product_id(name: str) -> str:
    """Generate a slug-like ID from product name."""
    return name.lower().replace(" ", "-")


def generate_pdf_catalog(csv_file: str, output_pdf: str):
    """Generate PDF catalog from CSV with one product per page."""
    
    # Read CSV
    products = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append(row)
    
    print(f"Read {len(products)} products from CSV")
    
    # Create PDF
    pdf_path = Path(output_pdf)
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    
    # Build document
    story = []
    styles = getSampleStyleSheet()
    
    # Create a title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    
    for idx, product in enumerate(products, 1):
        # Product ID
        product_id = generate_product_id(product.get('Product Name', f'Product {idx}'))
        
        # Create table data
        table_data = [
            ['Field', 'Value'],
            ['id', product_id],
            ['sku', product_id],
            ['name', product.get('Product Name', '')],
            ['category', product.get('Category', '')],
            ['description', product.get('Description', '')],
            ['price', product.get('Price', '0')],
            ['rating', '0.0'],
            ['tags', product.get('Tags', '')],
            ['use_cases', product.get('Use Cases', '')],
            ['benefits', product.get('Benefits', '')],
            ['image_hints', product.get('Image Hints', '')],
            ['source', 'uploaded-catalog'],
        ]
        
        # Create table
        table = Table(table_data, colWidths=[1.5 * inch, 4.5 * inch])
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#e8e8e8')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('WORDWRAP', (1, 1), (1, -1), True),
        ]))
        
        # Add title
        title = Paragraph(f"Product {idx} of {len(products)}", title_style)
        story.append(title)
        story.append(Spacer(1, 0.2 * inch))
        
        # Add table
        story.append(table)
        
        # Add page break (except on last page)
        if idx < len(products):
            story.append(PageBreak())
    
    # Build PDF
    doc.build(story)
    print(f"✓ PDF generated: {pdf_path}")
    print(f"  Total pages: {len(products)}")
    print(f"  File size: {pdf_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    csv_file = "data/product-catalog.csv"
    output_pdf = "data/product-catalog-generated.pdf"
    
    if Path(csv_file).exists():
        generate_pdf_catalog(csv_file, output_pdf)
    else:
        print(f"CSV file not found: {csv_file}")

import markdown
from xhtml2pdf import pisa
import os

def md_to_pdf(md_file, pdf_file):
    with open(md_file, 'r', encoding='utf-8') as f:
        md_text = f.read()

    # Convert Markdown to HTML
    html_text = markdown.markdown(md_text, extensions=['fenced_code', 'tables'])

    # Add some basic styling for the PDF
    styled_html = f"""
    <html>
    <head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        h1 {{ color: #2874f0; border-bottom: 2px solid #2874f0; padding-bottom: 10px; }}
        h2 {{ color: #172337; margin-top: 30px; border-bottom: 1px solid #ddd; }}
        pre {{ background: #f4f4f4; padding: 10px; border-radius: 5px; font-family: monospace; }}
        code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
    </head>
    <body>
    {html_text}
    </body>
    </html>
    """

    # Create PDF
    with open(pdf_file, "wb") as f:
        pisa_status = pisa.CreatePDF(styled_html, dest=f)

    return not pisa_status.err

if __name__ == "__main__":
    success = md_to_pdf("DOCUMENTATION.md", "Ecommers_Project_Documentation.pdf")
    if success:
        print("PDF generated successfully!")
    else:
        print("Error generating PDF.")

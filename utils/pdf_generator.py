try:
    from xhtml2pdf import pisa
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

from io import BytesIO

def generate_pdf(template_html):
    if not PDF_SUPPORT:
        print("Warning: xhtml2pdf not installed. PDF generation is disabled.")
        return None

    pdf = BytesIO()
    pisa_status = pisa.CreatePDF(template_html, dest=pdf)

    if pisa_status.err:
        return None

    return pdf

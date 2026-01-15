import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER

def generate_profile_pdf(analysis_text, domain_name):
    """
    Utility to convert AI text into a structured PDF report.
    """
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=LETTER)
    p.setTitle(f"Profile Report - {domain_name}")
    
    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 750, f"Domain Profile: {domain_name.upper()}")
    p.setLineWidth(1)
    p.line(50, 740, 550, 740)
    
    # Body Text
    text_object = p.beginText(50, 710)
    text_object.setFont("Helvetica", 11)
    text_object.setLeading(14)
    
    # Simple line wrapping
    for line in analysis_text.split('\n'):
        if len(line) > 90:
            text_object.textLine(line[:90] + "-")
            text_object.textLine(line[90:])
        else:
            text_object.textLine(line)
            
    p.drawText(text_object)
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
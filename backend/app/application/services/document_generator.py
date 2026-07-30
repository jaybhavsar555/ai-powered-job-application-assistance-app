import io
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

class DocumentGenerator:
    """
    Service responsible for converting JSON structured resume data into downloadable file formats.
    """
    def generate_docx(self, user_name: str, contact_info: str, summary: str, bullets: list[str]) -> io.BytesIO:
        doc = Document()
        
        # Name Header
        name_para = doc.add_paragraph()
        name_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        name_run = name_para.add_run(user_name.upper())
        name_run.bold = True
        name_run.font.size = Pt(16)
        
        # Contact Info Header
        contact_para = doc.add_paragraph()
        contact_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        contact_para.add_run(contact_info)
        
        # Professional Summary Section
        if summary:
            doc.add_heading('Professional Summary', level=1)
            doc.add_paragraph(summary)
            
        # Experience / Tailored Bullets Section
        if bullets:
            doc.add_heading('Key Achievements & Experience', level=1)
            for bullet in bullets:
                doc.add_paragraph(bullet, style='List Bullet')
                
        # Save to memory stream
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        
        return file_stream

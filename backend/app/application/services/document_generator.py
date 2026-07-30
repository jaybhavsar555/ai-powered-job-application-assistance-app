import io
import re
from typing import List, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer


class DocumentGenerator:
    """Convert tailored resume / cover letter content into DOCX and PDF."""

    def generate_resume_docx(
        self,
        user_name: str,
        contact_info: str,
        summary: str,
        bullets: list[str],
        skills: Optional[list[str]] = None,
        base_excerpt: Optional[str] = None,
    ) -> io.BytesIO:
        doc = Document()

        name_para = doc.add_paragraph()
        name_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        name_run = name_para.add_run(user_name.upper())
        name_run.bold = True
        name_run.font.size = Pt(16)

        if contact_info:
            contact_para = doc.add_paragraph()
            contact_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            contact_para.add_run(contact_info)

        if summary:
            doc.add_heading("Professional Summary", level=1)
            doc.add_paragraph(summary)

        if bullets:
            doc.add_heading("Key Achievements & Experience", level=1)
            for bullet in bullets:
                doc.add_paragraph(bullet, style="List Bullet")

        if skills:
            doc.add_heading("Highlighted Skills", level=1)
            doc.add_paragraph(", ".join(skills))

        if base_excerpt:
            doc.add_heading("Supporting Experience (from base resume)", level=1)
            for block in self._split_blocks(base_excerpt, limit=12):
                doc.add_paragraph(block)

        stream = io.BytesIO()
        doc.save(stream)
        stream.seek(0)
        return stream

    # Backward-compatible alias used by /documents/export/docx
    def generate_docx(self, user_name: str, contact_info: str, summary: str, bullets: list[str]) -> io.BytesIO:
        return self.generate_resume_docx(user_name, contact_info, summary, bullets)

    def generate_cover_letter_docx(self, user_name: str, content: str) -> io.BytesIO:
        doc = Document()
        for para in self._paragraphs(content):
            doc.add_paragraph(para)
        if user_name and user_name.lower() not in content.lower():
            doc.add_paragraph("")
            doc.add_paragraph(user_name)
        stream = io.BytesIO()
        doc.save(stream)
        stream.seek(0)
        return stream

    def generate_resume_pdf(
        self,
        user_name: str,
        contact_info: str,
        summary: str,
        bullets: list[str],
        skills: Optional[list[str]] = None,
        base_excerpt: Optional[str] = None,
    ) -> io.BytesIO:
        stream = io.BytesIO()
        doc = SimpleDocTemplate(
            stream,
            pagesize=LETTER,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.7 * inch,
            bottomMargin=0.7 * inch,
        )
        styles = getSampleStyleSheet()
        title = ParagraphStyle(
            "ResumeTitle",
            parent=styles["Heading1"],
            fontSize=16,
            alignment=1,
            spaceAfter=6,
        )
        contact = ParagraphStyle(
            "Contact",
            parent=styles["Normal"],
            fontSize=9,
            alignment=1,
            spaceAfter=14,
        )
        heading = ParagraphStyle(
            "Section",
            parent=styles["Heading2"],
            fontSize=12,
            spaceBefore=10,
            spaceAfter=6,
        )
        body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=13)

        story = [
            Paragraph(self._escape(user_name.upper()), title),
            Paragraph(self._escape(contact_info or ""), contact),
        ]
        if summary:
            story.append(Paragraph("Professional Summary", heading))
            story.append(Paragraph(self._escape(summary), body))
            story.append(Spacer(1, 6))
        if bullets:
            story.append(Paragraph("Key Achievements & Experience", heading))
            items = [ListItem(Paragraph(self._escape(b), body)) for b in bullets]
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=12))
        if skills:
            story.append(Paragraph("Highlighted Skills", heading))
            story.append(Paragraph(self._escape(", ".join(skills)), body))
        if base_excerpt:
            story.append(Paragraph("Supporting Experience (from base resume)", heading))
            for block in self._split_blocks(base_excerpt, limit=10):
                story.append(Paragraph(self._escape(block), body))
                story.append(Spacer(1, 4))

        doc.build(story)
        stream.seek(0)
        return stream

    def generate_cover_letter_pdf(self, user_name: str, content: str) -> io.BytesIO:
        stream = io.BytesIO()
        doc = SimpleDocTemplate(
            stream,
            pagesize=LETTER,
            leftMargin=0.85 * inch,
            rightMargin=0.85 * inch,
            topMargin=0.85 * inch,
            bottomMargin=0.85 * inch,
        )
        styles = getSampleStyleSheet()
        body = ParagraphStyle("CLBody", parent=styles["Normal"], fontSize=11, leading=15, spaceAfter=10)
        story = [Paragraph(self._escape(p), body) for p in self._paragraphs(content)]
        if user_name and user_name.lower() not in content.lower():
            story.append(Spacer(1, 12))
            story.append(Paragraph(self._escape(user_name), body))
        doc.build(story)
        stream.seek(0)
        return stream

    @staticmethod
    def _escape(text: str) -> str:
        return (
            (text or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    @staticmethod
    def _paragraphs(content: str) -> List[str]:
        parts = re.split(r"\n\s*\n", (content or "").strip())
        out = []
        for part in parts:
            cleaned = " ".join(line.strip() for line in part.splitlines() if line.strip())
            if cleaned:
                out.append(cleaned)
        return out or [content or ""]

    @staticmethod
    def _split_blocks(text: str, limit: int = 12) -> List[str]:
        lines = [ln.strip(" •-\t") for ln in (text or "").splitlines() if ln.strip()]
        # Prefer bullet-like lines
        bullets = [ln for ln in lines if len(ln) > 40][:limit]
        return bullets or lines[:limit]

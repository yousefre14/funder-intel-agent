"""Convert markdown reports to styled PDFs using fpdf2 + DejaVu (full Unicode)."""
from io import BytesIO
from datetime import datetime
from pathlib import Path
import re
from fpdf import FPDF


# Path to bundled fonts
FONTS_DIR = Path(__file__).parent / "fonts"


class FunderReportPDF(FPDF):
    """Custom PDF with DejaVu Unicode font, header, footer."""

    def __init__(self, funder_name: str):
        super().__init__()
        self.funder_name = funder_name
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)
        self._register_unicode_fonts()

    def _register_unicode_fonts(self):
        """Register DejaVu Sans for full Unicode support."""
        self.add_font("DejaVu", "", str(FONTS_DIR / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(FONTS_DIR / "DejaVuSans-Bold.ttf"))
        self.add_font("DejaVu", "I", str(FONTS_DIR / "DejaVuSans-Oblique.ttf"))
        self.add_font("DejaVu", "BI", str(FONTS_DIR / "DejaVuSans-BoldOblique.ttf"))

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0, 10,
            f"Funder Intel Agent  ·  Page {self.page_no()}/{{nb}}",
            align="C",
        )

    def cover_page(self):
        self.add_page()
        self.set_y(80)
        self.set_font("DejaVu", "B", 26)
        self.set_text_color(26, 54, 93)
        self.cell(0, 15, "Funder Intelligence Report", align="C")
        self.ln(20)

        self.set_font("DejaVu", "B", 20)
        self.set_text_color(44, 82, 130)
        self.cell(0, 12, self.funder_name, align="C")
        self.ln(40)

        self.set_font("DejaVu", "", 11)
        self.set_text_color(113, 128, 150)
        self.cell(0, 8, f"Generated {datetime.now().strftime('%B %d, %Y')}", align="C")
        self.ln(8)
        self.cell(0, 8, "Funder Intel Agent", align="C")


def _clean_markdown_line(line: str) -> str:
    """Strip markdown markers — keep all Unicode."""
    line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
    line = re.sub(r"\*(.+?)\*", r"\1", line)
    line = re.sub(r"`(.+?)`", r"\1", line)
    line = re.sub(r"$$(.+?)$$\(.+?\)", r"\1", line)
    return line.strip()


def markdown_to_pdf_bytes(
    md_content: str,
    funder_name: str,
    title: str = "Funder Intelligence Report",
) -> bytes:
    """Convert markdown to a styled PDF, return bytes."""
    pdf = FunderReportPDF(funder_name)
    pdf.alias_nb_pages()
    pdf.cover_page()

    pdf.add_page()

    for raw_line in md_content.split("\n"):
        line = raw_line.rstrip()

        if not line or line.startswith("=") or line.startswith("---"):
            pdf.ln(3)
            continue

        # Headings
        if line.startswith("# "):
            pdf.ln(4)
            pdf.set_font("DejaVu", "B", 18)
            pdf.set_text_color(26, 54, 93)
            pdf.multi_cell(0, 9, _clean_markdown_line(line[2:]))
            pdf.ln(2)
            continue

        if line.startswith("## "):
            pdf.ln(3)
            pdf.set_font("DejaVu", "B", 14)
            pdf.set_text_color(44, 82, 130)
            pdf.multi_cell(0, 8, _clean_markdown_line(line[3:]))
            pdf.ln(1)
            continue

        if line.startswith("### "):
            pdf.set_font("DejaVu", "B", 12)
            pdf.set_text_color(45, 55, 72)
            pdf.multi_cell(0, 7, _clean_markdown_line(line[4:]))
            continue

        # Bullets — now Unicode bullets work fine
        if line.lstrip().startswith(("- ", "* ", "• ")):
            pdf.set_font("DejaVu", "", 11)
            pdf.set_text_color(45, 55, 72)
            text = _clean_markdown_line(line.lstrip()[2:])
            pdf.multi_cell(0, 6, f"  •  {text}")
            continue

        if re.match(r"^\d+\.\s", line.lstrip()):
            pdf.set_font("DejaVu", "", 11)
            pdf.set_text_color(45, 55, 72)
            pdf.multi_cell(0, 6, _clean_markdown_line(line))
            continue

        # Default paragraph
        pdf.set_font("DejaVu", "", 11)
        pdf.set_text_color(45, 55, 72)
        pdf.multi_cell(0, 6, _clean_markdown_line(line))

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
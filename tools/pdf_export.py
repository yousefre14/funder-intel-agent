"""Convert markdown reports to styled PDFs using fpdf2 (no custom fonts)."""
from io import BytesIO
from datetime import datetime
import re
from fpdf import FPDF


# Map Unicode chars to Latin-1 safe equivalents
UNICODE_REPLACEMENTS = {
    # Bullets
    "•": "-", "●": "-", "◦": "-", "▪": "-", "‣": "-", "·": "-",
    # Arrows
    "→": "->", "←": "<-", "⇒": "=>", "⇐": "<=",
    # Dashes & punctuation
    "—": "-", "–": "-", "…": "...",
    "“": '"', "”": '"', "‘": "'", "’": "'", "«": '"', "»": '"',
    # Marks
    "✓": "[x]", "✔": "[x]", "✗": "[ ]", "✘": "[ ]",
    "★": "*", "☆": "*",
    "©": "(c)", "®": "(R)", "™": "(TM)",
    "°": " deg", "€": "EUR", "£": "GBP", "¥": "JPY",
    # Common emojis in your app
    "🔍": "[Search]", "📋": "[Profile]", "🎯": "[Target]",
    "🔗": "[Link]", "✉️": "[Email]", "✉": "[Email]",
    "🚀": "[Launch]", "💰": "[Cost]", "📄": "[Doc]",
    "📂": "[Folder]", "📊": "[Stats]", "🏛️": "[Org]",
    "🌐": "[Web]", "⏱️": "[Time]", "✅": "[Done]",
    "⚙️": "[Settings]", "🏢": "[Org]", "📚": "[Library]",
    "🔄": "[Refresh]", "📥": "[Download]", "📑": "[PDF]",
}


def _sanitize_for_latin1(text: str) -> str:
    """Replace Unicode chars with Latin-1 equivalents and strip the rest."""
    if not text:
        return ""
    for unicode_char, replacement in UNICODE_REPLACEMENTS.items():
        text = text.replace(unicode_char, replacement)
    return text.encode("latin-1", errors="ignore").decode("latin-1")


class FunderReportPDF(FPDF):
    """Custom PDF using built-in Helvetica (no font files needed)."""

    def __init__(self, funder_name: str):
        super().__init__()
        self.funder_name = _sanitize_for_latin1(funder_name)
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0, 10,
            f"Funder Intel Agent  -  Page {self.page_no()}/{{nb}}",
            align="C",
        )

    def cover_page(self):
        self.add_page()
        self.set_y(80)
        self.set_font("Helvetica", "B", 26)
        self.set_text_color(26, 54, 93)
        self.cell(0, 15, "Funder Intelligence Report", align="C")
        self.ln(20)

        self.set_font("Helvetica", "B", 20)
        self.set_text_color(44, 82, 130)
        self.cell(0, 12, self.funder_name, align="C")
        self.ln(40)

        self.set_font("Helvetica", "", 11)
        self.set_text_color(113, 128, 150)
        self.cell(
            0, 8,
            f"Generated {datetime.now().strftime('%B %d, %Y')}",
            align="C",
        )
        self.ln(8)
        self.cell(0, 8, "Funder Intel Agent", align="C")


def _clean_markdown_line(line: str) -> str:
    """Strip markdown markers and sanitize Unicode."""
    line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)        # bold
    line = re.sub(r"\*(.+?)\*", r"\1", line)            # italic
    line = re.sub(r"`(.+?)`", r"\1", line)              # inline code
    line = re.sub(r"$$(.+?)$$\(.+?\)", r"\1", line)     # links
    return _sanitize_for_latin1(line.strip())


def markdown_to_pdf_bytes(
    md_content: str,
    funder_name: str,
    title: str = "Funder Intelligence Report",
) -> bytes:
    """Convert markdown to a styled PDF and return bytes."""
    pdf = FunderReportPDF(funder_name)
    pdf.alias_nb_pages()
    pdf.cover_page()
    pdf.add_page()

    for raw_line in md_content.split("\n"):
        line = raw_line.rstrip()

        # Skip dividers and empty lines
        if not line or line.startswith("=") or line.startswith("---"):
            pdf.ln(3)
            continue

        # H1
        if line.startswith("# "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_text_color(26, 54, 93)
            pdf.multi_cell(0, 9, _clean_markdown_line(line[2:]))
            pdf.ln(2)
            continue

        # H2
        if line.startswith("## "):
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(44, 82, 130)
            pdf.multi_cell(0, 8, _clean_markdown_line(line[3:]))
            pdf.ln(1)
            continue

        # H3
        if line.startswith("### "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(45, 55, 72)
            pdf.multi_cell(0, 7, _clean_markdown_line(line[4:]))
            continue

        # Bullets — using a Latin-1 safe character
        stripped = line.lstrip()
        if stripped.startswith(("- ", "* ", "• ")):
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(45, 55, 72)
            text = _clean_markdown_line(stripped[2:])
            pdf.multi_cell(0, 6, f"   -  {text}")
            continue

        # Numbered list
        if re.match(r"^\d+\.\s", stripped):
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(45, 55, 72)
            pdf.multi_cell(0, 6, _clean_markdown_line(line))
            continue

        # Default paragraph
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(45, 55, 72)
        pdf.multi_cell(0, 6, _clean_markdown_line(line))

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
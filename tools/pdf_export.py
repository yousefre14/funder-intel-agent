"""Convert markdown reports to styled PDFs using fpdf2."""
from io import BytesIO
from datetime import datetime
import re
from fpdf import FPDF


# ═══════════════════════════════════════════════════════════
# UNICODE SANITIZATION
# ═══════════════════════════════════════════════════════════

UNICODE_REPLACEMENTS = {
    "•": "-", "●": "-", "◦": "-", "▪": "-", "‣": "-", "·": "-",
    "→": "->", "←": "<-", "⇒": "=>", "⇐": "<=",
    "—": "-", "–": "-", "…": "...",
    "“": '"', "”": '"', "‘": "'", "’": "'", "«": '"', "»": '"',
    "✓": "[x]", "✔": "[x]", "✗": "[ ]", "✘": "[ ]",
    "★": "*", "☆": "*",
    "©": "(c)", "®": "(R)", "™": "(TM)",
    "°": " deg", "€": "EUR", "£": "GBP", "¥": "JPY",
    "🔍": "", "📋": "", "🎯": "", "🔗": "", "✉️": "", "✉": "",
    "🚀": "", "💰": "", "📄": "", "📂": "", "📊": "", "🏛️": "",
    "🌐": "", "⏱️": "", "✅": "", "⚙️": "", "🏢": "", "📚": "",
    "🔄": "", "📥": "", "📑": "",
}


def _sanitize(text: str) -> str:
    """Replace Unicode chars with Latin-1 equivalents and strip the rest."""
    if not text:
        return ""
    for src, repl in UNICODE_REPLACEMENTS.items():
        text = text.replace(src, repl)
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def _break_long_tokens(text: str, max_len: int = 50) -> str:
    """Insert spaces inside long unbroken strings (URLs, paths)."""
    if not text:
        return text
    words = text.split(" ")
    out = []
    for w in words:
        if len(w) > max_len:
            chunks = [w[i:i + max_len] for i in range(0, len(w), max_len)]
            out.append(" ".join(chunks))
        else:
            out.append(w)
    return " ".join(out)


def _clean(line: str) -> str:
    """Strip markdown markers, sanitize, break long tokens."""
    line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
    line = re.sub(r"\*(.+?)\*", r"\1", line)
    line = re.sub(r"`(.+?)`", r"\1", line)
    line = re.sub(r"$$(.+?)$$\(.+?\)", r"\1", line)
    return _break_long_tokens(_sanitize(line.strip()))


# ═══════════════════════════════════════════════════════════
# PDF CLASS
# ═══════════════════════════════════════════════════════════

# Layout constants — A4 is 210mm wide
PAGE_W = 210
PAGE_H = 297
MARGIN_LR = 18      # left/right margin
MARGIN_TB = 18      # top/bottom margin
CONTENT_W = PAGE_W - (2 * MARGIN_LR)   # 174mm of usable width


class FunderReportPDF(FPDF):

    def __init__(self, funder_name: str):
        super().__init__(format="A4", unit="mm")
        self.funder_name = _sanitize(funder_name) or "Funder"
        self.set_margins(MARGIN_LR, MARGIN_TB, MARGIN_LR)
        self.set_auto_page_break(auto=True, margin=MARGIN_TB)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(
            CONTENT_W, 6,
            f"Funder Intel Agent  |  Page {self.page_no()}/{{nb}}",
            align="C",
        )

    def render_cover(self):
        """Cover page with title, funder name, and date."""
        self.add_page()

        # Title (centered vertically)
        self.set_y(90)
        self.set_font("Helvetica", "B", 24)
        self.set_text_color(26, 54, 93)
        self.cell(CONTENT_W, 12, "Funder Intelligence Report", align="C")
        self.ln(18)

        # Funder name
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(44, 82, 130)
        self.cell(CONTENT_W, 10, self.funder_name, align="C")
        self.ln(40)

        # Date and footer text
        self.set_font("Helvetica", "", 10)
        self.set_text_color(120, 120, 120)
        self.cell(
            CONTENT_W, 6,
            f"Generated {datetime.now().strftime('%B %d, %Y')}",
            align="C",
        )
        self.ln(6)
        self.cell(CONTENT_W, 6, "Funder Intel Agent", align="C")

    def render_paragraph(self, text: str, font="Helvetica", style="", size=10,
                         color=(45, 55, 72), spacing_after=2):
        """Render a wrapped paragraph using the full content width."""
        self.set_font(font, style, size)
        self.set_text_color(*color)
        # Use explicit width to avoid epw edge cases
        self.multi_cell(CONTENT_W, size * 0.5 + 1, text)
        if spacing_after:
            self.ln(spacing_after)

    def render_h1(self, text: str):
        self.ln(3)
        self.render_paragraph(text, style="B", size=16,
                              color=(26, 54, 93), spacing_after=3)

    def render_h2(self, text: str):
        self.ln(2)
        self.render_paragraph(text, style="B", size=13,
                              color=(44, 82, 130), spacing_after=2)

    def render_h3(self, text: str):
        self.render_paragraph(text, style="B", size=11,
                              color=(45, 55, 72), spacing_after=1)

    def render_bullet(self, text: str):
        # Indent + dash + text
        self.set_font("Helvetica", "", 10)
        self.set_text_color(45, 55, 72)
        # Bullet marker takes ~6mm; remaining width = CONTENT_W - 6
        bullet_width = 6
        text_width = CONTENT_W - bullet_width

        x_start = self.get_x()
        y_start = self.get_y()

        # Write marker
        self.cell(bullet_width, 5.5, "  -")
        # Write wrapped text using remaining width
        self.multi_cell(text_width, 5.5, text)


# ═══════════════════════════════════════════════════════════
# MAIN ENTRY
# ═══════════════════════════════════════════════════════════

def markdown_to_pdf_bytes(
    md_content: str,
    funder_name: str,
    title: str = "Funder Intelligence Report",
) -> bytes:
    """Convert markdown to a styled PDF, return bytes."""
    pdf = FunderReportPDF(funder_name)
    pdf.alias_nb_pages()

    # Cover page
    pdf.render_cover()

    # Content starts on a new page
    pdf.add_page()

    for raw in md_content.split("\n"):
        line = raw.rstrip()

        # Skip empty lines and dividers
        if not line:
            pdf.ln(2)
            continue
        if line.startswith("=") or line.startswith("---") or line.startswith("___"):
            pdf.ln(2)
            continue

        # Headings
        if line.startswith("# "):
            pdf.render_h1(_clean(line[2:]))
            continue
        if line.startswith("## "):
            pdf.render_h2(_clean(line[3:]))
            continue
        if line.startswith("### "):
            pdf.render_h3(_clean(line[4:]))
            continue

        stripped = line.lstrip()

        # Bullets
        if stripped.startswith(("- ", "* ", "• ")):
            pdf.render_bullet(_clean(stripped[2:]))
            continue

        # Numbered lists
        if re.match(r"^\d+\.\s", stripped):
            pdf.render_paragraph(_clean(line), size=10, spacing_after=1)
            continue

        # Regular paragraph
        pdf.render_paragraph(_clean(line), size=10, spacing_after=1)

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
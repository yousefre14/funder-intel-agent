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


def _collapse_spaces(text: str) -> str:
    """Collapse repeated spaces/tabs into a single space."""
    return re.sub(r"[ \t]+", " ", text).strip()


def _break_long_tokens(text: str, max_len: int = 45) -> str:
    """
    Insert spaces inside long unbroken strings such as URLs and IDs.
    This prevents fpdf2 from overflowing horizontally.
    """
    if not text:
        return text

    words = text.split(" ")
    out = []

    for word in words:
        if len(word) > max_len:
            chunks = [word[i:i + max_len] for i in range(0, len(word), max_len)]
            out.append(" ".join(chunks))
        else:
            out.append(word)

    return " ".join(out)


def _clean(line: str) -> str:
    """Strip markdown markers, sanitize, collapse spaces, and break long tokens."""

    # Markdown links: [text](url) -> text
    line = re.sub(r"$$([^$$]+)\]\([^)]+\)", r"\1", line)

    # Bold / italic / inline code
    line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
    line = re.sub(r"\*(.+?)\*", r"\1", line)
    line = re.sub(r"`(.+?)`", r"\1", line)

    line = _sanitize(line.strip())
    line = _collapse_spaces(line)
    line = _break_long_tokens(line)

    return line


def _split_inline_items(line: str) -> list[str]:
    """
    Split lines that contain multiple bullets or list items on one line.

    Example:
        "- Name: Ballmer Group        - Type: Foundation"

    becomes:
        ["- Name: Ballmer Group", "- Type: Foundation"]

    This fixes the issue where second/third bullet items appear far right
    and get clipped in the PDF.
    """
    if not line:
        return [""]

    line = line.replace("\t", "    ").rstrip()

    # Split before a later bullet only if preceded by 2+ spaces.
    # Keeps normal hyphenated text intact.
    parts = re.split(r"\s{2,}(?=[\-*•]\s+)", line)

    final_parts = []
    for part in parts:
        # Split before numbered items if they appear after large spacing.
        subparts = re.split(r"\s{2,}(?=\d+\.\s+)", part)
        final_parts.extend(subparts)

    return [p.strip() for p in final_parts if p.strip()]


def _is_table_separator(line: str) -> bool:
    """Detect markdown table separator rows like |---|---|."""
    stripped = line.strip()
    if not stripped:
        return False
    return bool(re.fullmatch(r"\|?[\s:\-|\+]+\|?", stripped))


def _normalize_table_row(line: str) -> str:
    """
    Convert simple markdown table rows to readable text.

    Example:
        | Field | Value |
    becomes:
        Field: Value
    """
    stripped = line.strip()

    if "|" not in stripped:
        return line

    if _is_table_separator(stripped):
        return ""

    cells = [c.strip() for c in stripped.strip("|").split("|")]
    cells = [c for c in cells if c]

    if not cells:
        return ""

    if len(cells) == 1:
        return cells[0]

    if len(cells) == 2:
        return f"- {cells[0]}: {cells[1]}"

    return "- " + " | ".join(cells)


def _prepare_lines(md_content: str) -> list[str]:
    """
    Normalize markdown before rendering:
    - Converts markdown table rows into readable bullets.
    - Splits multiple bullet/list items on the same line.
    - Preserves headings and blank lines.
    """
    prepared = []

    for raw in md_content.split("\n"):
        raw = raw.rstrip()

        # Preserve blank lines.
        if not raw.strip():
            prepared.append("")
            continue

        # Normalize markdown tables.
        if "|" in raw:
            raw = _normalize_table_row(raw)
            if not raw:
                continue

        # Split inline bullets/items.
        parts = _split_inline_items(raw)

        for part in parts:
            prepared.append(part)

    return prepared


# ═══════════════════════════════════════════════════════════
# PDF CLASS
# ═══════════════════════════════════════════════════════════

PAGE_W = 210
PAGE_H = 297
MARGIN_LR = 18
MARGIN_TB = 18
CONTENT_W = PAGE_W - (2 * MARGIN_LR)


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
            CONTENT_W,
            6,
            f"Funder Intel Agent  |  Page {self.page_no()}/{{nb}}",
            align="C",
        )

    def render_cover(self):
        """Cover page with title, funder name, and date."""
        self.add_page()

        self.set_y(90)
        self.set_font("Helvetica", "B", 24)
        self.set_text_color(26, 54, 93)
        self.cell(CONTENT_W, 12, "Funder Intelligence Report", align="C")
        self.ln(18)

        self.set_font("Helvetica", "B", 18)
        self.set_text_color(44, 82, 130)
        self.cell(CONTENT_W, 10, self.funder_name, align="C")
        self.ln(40)

        self.set_font("Helvetica", "", 10)
        self.set_text_color(120, 120, 120)
        self.cell(
            CONTENT_W,
            6,
            f"Generated {datetime.now().strftime('%B %d, %Y')}",
            align="C",
        )
        self.ln(6)
        self.cell(CONTENT_W, 6, "Funder Intel Agent", align="C")

    def render_paragraph(
        self,
        text: str,
        font: str = "Helvetica",
        style: str = "",
        size: int = 10,
        color=(45, 55, 72),
        spacing_after: float = 2,
    ):
        """Render wrapped paragraph."""
        text = _clean(text)
        if not text:
            return

        self.set_x(MARGIN_LR)
        self.set_font(font, style, size)
        self.set_text_color(*color)

        try:
            self.multi_cell(CONTENT_W, size * 0.5 + 1, text)
        except Exception:
            # Last-resort safety: chunk text aggressively.
            chunks = [text[i:i + 80] for i in range(0, len(text), 80)]
            for chunk in chunks:
                self.set_x(MARGIN_LR)
                self.multi_cell(CONTENT_W, size * 0.5 + 1, chunk)

        if spacing_after:
            self.ln(spacing_after)

    def render_h1(self, text: str):
        self.ln(3)
        self.render_paragraph(
            text,
            style="B",
            size=16,
            color=(26, 54, 93),
            spacing_after=3,
        )

    def render_h2(self, text: str):
        self.ln(2)
        self.render_paragraph(
            text,
            style="B",
            size=13,
            color=(44, 82, 130),
            spacing_after=2,
        )

    def render_h3(self, text: str):
        self.render_paragraph(
            text,
            style="B",
            size=11,
            color=(45, 55, 72),
            spacing_after=1,
        )

    def render_bullet(self, text: str):
        """Render a wrapped bullet with proper indentation."""
        text = _clean(text)
        if not text:
            return

        self.set_font("Helvetica", "", 10)
        self.set_text_color(45, 55, 72)

        bullet_w = 7
        text_w = CONTENT_W - bullet_w

        self.set_x(MARGIN_LR)
        self.cell(bullet_w, 5.5, "-")
        self.multi_cell(text_w, 5.5, text)
        self.ln(0.5)


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

    pdf.render_cover()
    pdf.add_page()

    for line in _prepare_lines(md_content):
        line = line.rstrip()

        if not line:
            pdf.ln(2)
            continue

        if line.startswith("=") or line.startswith("---") or line.startswith("___"):
            pdf.ln(2)
            continue

        if line.startswith("# "):
            pdf.render_h1(line[2:])
            continue

        if line.startswith("## "):
            pdf.render_h2(line[3:])
            continue

        if line.startswith("### "):
            pdf.render_h3(line[4:])
            continue

        stripped = line.lstrip()

        if stripped.startswith(("- ", "* ", "• ")):
            pdf.render_bullet(stripped[2:])
            continue

        if re.match(r"^\d+\.\s", stripped):
            pdf.render_paragraph(line, size=10, spacing_after=1)
            continue

        pdf.render_paragraph(line, size=10, spacing_after=1)

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
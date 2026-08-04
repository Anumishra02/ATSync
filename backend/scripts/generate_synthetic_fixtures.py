"""Generate the committed synthetic PDF fixture set.

One fake résumé (Priya Sharma / priya.sharma@example.com -- entirely
fictional), exported five ways with the same content but different layout
engines/styles, so a parser bug shows up as "these five don't agree"
without needing any real person's document or hand-labeled ground truth.

None of these are literal exports from Word/Google Docs/Canva -- this
environment has no LaTeX, no LibreOffice, no Word/Docs/Canva automation
available, only reportlab. Each layout instead *approximates* that tool's
characteristic output (font choice, column structure, spacing) closely
enough to exercise the same parsing hazards: reportlab's canvas gives exact
word-level x/y placement, which is what actually matters for testing
column detection and reading-order reconstruction -- the visual polish of
the real tool is not the thing under test.

Canonical section order (shared by all five, and by expected_text.txt):
    1. Header (name + contact line)
    2. Summary
    3. Education
    4. Experience
    5. Projects
    6. Skills
    7. Certifications

The two two-column layouts split this list after section 3 (Education) --
LEFT = {Header, Summary, Education}, RIGHT = {Experience, Projects, Skills,
Certifications} -- so "read left column top-to-bottom, then right column
top-to-bottom" reproduces the *exact same* canonical order as the
single-column layouts. That's what makes one shared expected_text.txt
meaningful across all five files: correct extraction always yields the
same sequence, regardless of visual layout.

Run:  python scripts/generate_synthetic_fixtures.py
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

OUT_DIR = Path(__file__).resolve().parents[2] / "backend" / "tests" / "fixtures" / "pdfs"

NAME = "Priya Sharma"
CONTACT = "priya.sharma@example.com | +91 98765 43210 | Bengaluru, India | linkedin.com/in/priyasharma"

SUMMARY = [
    "Computer Science undergraduate with hands-on experience in full-stack web",
    "development and machine learning. Skilled in Python, JavaScript, and cloud",
    "deployment. Seeking a Software Engineering internship.",
]

EDUCATION = [
    ("B.Tech in Computer Science", "ABC Institute of Technology, 2022-2026, CGPA: 8.4/10"),
]

EXPERIENCE = [
    {
        "title": "Software Engineering Intern, TechNova Solutions",
        "meta": "May 2025 - Jul 2025, Bengaluru",
        "bullets": [
            "Built a REST API using FastAPI and PostgreSQL, serving 50,000 requests per day.",
            "Automated deployment pipelines with Docker and GitHub Actions, cutting release time by 30%.",
            "Collaborated with a team of 5 engineers using Agile sprints to ship features biweekly.",
        ],
    },
]

PROJECTS = [
    {
        "title": "Campus Connect | React, Node.js, MongoDB",
        "bullets": [
            "Developed a campus event platform used by 1,200 students, with real-time notifications.",
        ],
    },
    {
        "title": "StockSense | Python, scikit-learn, Flask",
        "bullets": [
            "Built a stock price prediction model achieving 82% directional accuracy on test data.",
        ],
    },
]

SKILLS = [
    "Languages: Python, JavaScript, Java, SQL",
    "Frameworks: React, FastAPI, Flask, Node.js",
    "Tools: Docker, Git, AWS, PostgreSQL, MongoDB",
]

CERTIFICATIONS = [
    "AWS Certified Cloud Practitioner",
    "Deep Learning Specialization - Coursera",
]


def canonical_lines() -> list[str]:
    """The single shared ground truth, in canonical reading order."""
    lines = [NAME, CONTACT, "Summary", *SUMMARY, "Education"]
    for degree, detail in EDUCATION:
        lines += [degree, detail]
    lines.append("Experience")
    for job in EXPERIENCE:
        lines += [job["title"], job["meta"], *job["bullets"]]
    lines.append("Projects")
    for proj in PROJECTS:
        lines += [proj["title"], *proj["bullets"]]
    lines.append("Skills")
    lines += SKILLS
    lines.append("Certifications")
    lines += CERTIFICATIONS
    return lines


# ---------------------------------------------------------------------------
# Low-level word-wrap helper (kept dependency-free -- no Platypus needed for
# what is otherwise exact x/y placement).
# ---------------------------------------------------------------------------


def _wrap(c: canvas.Canvas, text: str, font: str, size: float, max_width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if c.stringWidth(trial, font, size) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class _Writer:
    """Tiny top-down text cursor for one column of a page."""

    def __init__(self, c: canvas.Canvas, x: float, top: float, width: float):
        self.c = c
        self.x = x
        self.y = top
        self.width = width

    def line(self, text: str, font: str, size: float, gap: float = 4, color=colors.black) -> None:
        self.c.setFont(font, size)
        self.c.setFillColor(color)
        for wrapped in _wrap(self.c, text, font, size, self.width):
            self.c.drawString(self.x, self.y, wrapped)
            self.y -= size + gap

    def space(self, amount: float) -> None:
        self.y -= amount


# ---------------------------------------------------------------------------
# Section renderers, parameterized by font so each layout gets its own feel.
# ---------------------------------------------------------------------------


def _heading(w: _Writer, text: str, font_bold: str, size: float, rule: bool = False) -> None:
    w.space(6)
    w.line(text.upper(), font_bold, size, gap=2)
    if rule:
        w.c.setStrokeColor(colors.grey)
        w.c.line(w.x, w.y + 4, w.x + w.width, w.y + 4)
    w.space(4)


def _render_header_summary_education(w: _Writer, font: str, font_bold: str, name_size: float) -> None:
    w.line(NAME, font_bold, name_size, gap=6)
    w.line(CONTACT, font, 9, color=colors.HexColor("#444444"))
    _heading(w, "Summary", font_bold, 11, rule=True)
    for line in SUMMARY:
        w.line(line, font, 10)
    _heading(w, "Education", font_bold, 11, rule=True)
    for degree, detail in EDUCATION:
        w.line(degree, font_bold, 10)
        w.line(detail, font, 10, color=colors.HexColor("#444444"))


def _render_experience_projects_skills_certs(w: _Writer, font: str, font_bold: str) -> None:
    _heading(w, "Experience", font_bold, 11, rule=True)
    for job in EXPERIENCE:
        w.line(job["title"], font_bold, 10)
        w.line(job["meta"], font, 9, color=colors.HexColor("#444444"))
        for b in job["bullets"]:
            w.line(f"- {b}", font, 10)
    _heading(w, "Projects", font_bold, 11, rule=True)
    for proj in PROJECTS:
        w.line(proj["title"], font_bold, 10)
        for b in proj["bullets"]:
            w.line(f"- {b}", font, 10)
    _heading(w, "Skills", font_bold, 11, rule=True)
    for s in SKILLS:
        w.line(s, font, 10)
    _heading(w, "Certifications", font_bold, 11, rule=True)
    for cert in CERTIFICATIONS:
        w.line(cert, font, 10)


def _single_column(path: Path, font: str, font_bold: str, name_size: float = 20) -> None:
    c = canvas.Canvas(str(path), pagesize=LETTER)
    page_w, page_h = LETTER
    margin = 0.85 * inch
    w = _Writer(c, margin, page_h - margin, page_w - 2 * margin)
    _render_header_summary_education(w, font, font_bold, name_size)
    _render_experience_projects_skills_certs(w, font, font_bold)
    c.save()


def _two_column(path: Path, font: str, font_bold: str, sidebar_fill: colors.Color | None) -> None:
    c = canvas.Canvas(str(path), pagesize=LETTER)
    page_w, page_h = LETTER
    margin = 0.7 * inch
    gutter = 0.35 * inch
    left_w = (page_w - 2 * margin - gutter) * 0.38
    right_w = (page_w - 2 * margin - gutter) * 0.62
    left_x = margin
    right_x = margin + left_w + gutter

    if sidebar_fill is not None:
        c.setFillColor(sidebar_fill)
        c.rect(0, 0, left_x + left_w + gutter / 2, page_h, fill=1, stroke=0)

    left = _Writer(c, left_x, page_h - margin, left_w)
    _render_header_summary_education(left, font, font_bold, name_size=16)

    right = _Writer(c, right_x, page_h - margin, right_w)
    _render_experience_projects_skills_certs(right, font, font_bold)

    c.save()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. "Word"-style: single column, serif, traditional margins.
    _single_column(OUT_DIR / "word_style.pdf", "Times-Roman", "Times-Bold")

    # 2. "Google Docs"-style: single column, sans-serif.
    _single_column(OUT_DIR / "google_docs_style.pdf", "Helvetica", "Helvetica-Bold")

    # 3. "Canva"-style: two columns, filled sidebar, sans-serif.
    _two_column(
        OUT_DIR / "canva_style.pdf", "Helvetica", "Helvetica-Bold",
        sidebar_fill=colors.HexColor("#EFEFF7"),
    )

    # 4. "LaTeX"-style APPROXIMATION: serif, tight leading, ruled headings --
    #    not real pdflatex output (unavailable in this environment), styled
    #    to resemble the classic Jake's-Resume-template look.
    _single_column(OUT_DIR / "latex_style.pdf", "Times-Roman", "Times-Bold", name_size=18)

    # 5. Two-column template, distinct from Canva: no fill, plain divider.
    _two_column(OUT_DIR / "two_column_template.pdf", "Times-Roman", "Times-Bold", sidebar_fill=None)

    expected = OUT_DIR / "expected_text.txt"
    expected.write_text("\n".join(canonical_lines()) + "\n", encoding="utf-8")

    print(f"Wrote 5 PDFs + expected_text.txt to {OUT_DIR}")


if __name__ == "__main__":
    main()

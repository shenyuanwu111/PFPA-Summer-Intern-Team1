from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


OUTPUT = "/Users/haixintan/Documents/Codex/2026-06-24/2-years-financials/Week2/outputs/github_upload_report.pdf"


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, letter[0], letter[1], stroke=0, fill=1)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(0.72 * inch, 0.45 * inch, "PFPA-W2 GitHub Upload Report")
    canvas.drawRightString(7.78 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def p(text, style):
    return Paragraph(text, style)


def build():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=letter,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.72 * inch,
        title="GitHub Upload Report",
        author="Codex",
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1F4E78"),
        spaceAfter=14,
    )
    h1 = ParagraphStyle(
        "HeadingCustom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1F4E78"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "BodyCustom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=7,
    )
    bullet = ParagraphStyle(
        "BulletCustom",
        parent=body,
        leftIndent=14,
        bulletIndent=5,
        spaceAfter=4,
    )
    small = ParagraphStyle(
        "SmallCustom",
        parent=body,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#444444"),
    )

    story = []
    story.append(p("GitHub Upload Report", title))
    story.append(p("<b>Repository:</b> https://github.com/ht2871-dot/PFPA-W2", body))
    story.append(p("<b>Prepared for:</b> PFPA-W2 two-year financials project", body))
    story.append(p("<b>Purpose:</b> Explain the files uploaded to GitHub and what each file is used for.", body))

    story.append(p("Executive Summary", h1))
    story.append(p(
        "The GitHub repository contains a complete financial workbook project. It includes the final Excel deliverable, "
        "the code used to generate it, preview images used for quality assurance, and documentation explaining the data sources and methodology.",
        body,
    ))

    story.append(p("Uploaded File Inventory", h1))
    data = [
        ["File or Folder", "Purpose"],
        ["README.md", "Project overview, included companies, deliverable location, data sources, and key assumptions."],
        [".gitignore", "Keeps temporary files, logs, raw data caches, and dependency folders out of GitHub."],
        ["Week2/outputs/.../two_year_financials.xlsx", "Final Excel workbook and primary deliverable."],
        ["Week2/work/build_financials.mjs", "Node.js script that generated the workbook and preview images."],
        ["Week2/outputs/.../*_preview.png", "Rendered previews of workbook sheets used for visual QA."],
    ]
    data = [[p(cell, small) for cell in row] for row in data]
    table = Table(data, colWidths=[2.65 * inch, 4.05 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("LEADING", (0, 0), (-1, -1), 10.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BFBFBF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FB")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)

    story.append(p("1. Final Excel Workbook", h1))
    story.append(p("<b>File:</b> Week2/outputs/financials_2026_06_24/two_year_financials.xlsx", body))
    story.append(p(
        "This is the main deliverable. It contains two years of financial, rate, and market data for COST, KO, DELL, ORCL, PNC, WMT, INTU, AMZN, T, and KHC.",
        body,
    ))
    for item in [
        "Cover - project overview, company list, source notes, and methodology.",
        "Summary - latest closing price, dividend adjustment factor, shares outstanding, market cap, 1Y Treasury, and SOFR.",
        "Company Financials - two latest SEC annual fiscal years per company, including debt, liabilities, dividends, and source tags.",
        "Rates - daily one-year Treasury and SOFR data.",
        "Prices - daily closing prices for the 10 companies.",
        "Sources Audit - source URLs, SEC tags, periods, and notes.",
        "Checks - basic validation checks for completeness and missing market caps.",
    ]:
        story.append(p(item, bullet))

    story.append(p("2. Code File", h1))
    story.append(p("<b>File:</b> Week2/work/build_financials.mjs", body))
    story.append(p(
        "This Node.js script generated the Excel workbook. It reads source data, maps company financial fields to SEC XBRL tags, calculates market cap, "
        "calculates dividend adjustment factor from adjusted close divided by close, applies workbook formatting, renders preview images, and exports the final XLSX file.",
        body,
    ))
    story.append(p(
        "This file is important because it makes the workbook creation process reproducible and shows how the final numbers were assembled.",
        body,
    ))

    story.append(p("3. Preview Images", h1))
    story.append(p(
        "The repository includes preview images for Checks, Company Financials, Prices, Rates, Sources Audit, and Summary. "
        "These PNG files were used to verify that workbook sheets were readable, aligned, and not visually broken.",
        body,
    ))

    story.append(p("4. Documentation and Ignore Rules", h1))
    story.append(p(
        "README.md provides the project description and key assumptions. .gitignore keeps the repository clean by excluding logs, raw downloaded caches, "
        "temporary Excel lock files, workbook inspection dumps, and dependency folders.",
        body,
    ))

    story.append(p("Excluded Files", h1))
    story.append(p(
        "Raw SEC JSON files, Yahoo JSON files, FRED CSV files, failed Stooq downloads, logs, and large inspection NDJSON files were intentionally not uploaded. "
        "These files are either temporary, reproducible, or unnecessary for reviewing the final deliverable.",
        body,
    ))

    story.append(p("Conclusion", h1))
    story.append(p(
        "The GitHub repository contains the materials needed to review and reproduce the project: the final Excel workbook, the generation script, visual QA previews, "
        "and documentation. The uploaded files are focused on the deliverable and its reproducibility while avoiding unnecessary temporary data.",
        body,
    ))
    story.append(Spacer(1, 0.12 * inch))
    story.append(p("Repository link: https://github.com/ht2871-dot/PFPA-W2", small))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build()

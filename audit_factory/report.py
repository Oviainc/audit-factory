"""Report rendering: Markdown, HTML and PDF from one AuditResult.

Branding follows the standing OVIA rules: no public prices anywhere in a
client-facing document (fees are quoted privately, in a written plan),
and the call to action is "Got questions?".
"""

from __future__ import annotations

import html as html_lib
import io

from .checks import AuditResult, Check

STATUS_ICON = {"pass": "✅", "warn": "⚠️", "fail": "❌", "not_checked": "➖"}
STATUS_WORD = {"pass": "Pass", "warn": "Partial", "fail": "Missing", "not_checked": "Not checked"}


def _top_fixes(result: AuditResult, n: int = 5) -> list[Check]:
    failed = [c for c in result.checks if c.status == "fail"]
    warned = [c for c in result.checks if c.status == "warn"]
    return sorted(failed + warned, key=lambda c: -c.max_points)[:n]


def render_markdown(result: AuditResult) -> str:
    lines = [
        f"# Website & Enquiry Audit — {result.business_name}",
        "",
        f"**Site:** {result.final_url or result.url}  ",
        f"**Checked:** {result.fetched_at} · Response {result.response_ms} ms · HTTP {result.status_code}",
        "",
        f"## Score: {result.score:.0f} / 100 — {result.grade}",
        "",
        "Every check below was verified on the page itself. Anything a website "
        "cannot prove is marked Not checked — never guessed.",
        "",
        "## The fixes that matter most",
        "",
    ]
    for i, c in enumerate(_top_fixes(result), 1):
        lines.append(f"{i}. **{c.label}** — {c.recommendation}")
    lines += ["", "## Full check list", ""]
    current = None
    for c in result.checks:
        if c.category != current:
            current = c.category
            lines += [f"### {current}", ""]
        lines.append(
            f"- {STATUS_ICON[c.status]} **{c.label}** ({STATUS_WORD[c.status]}) — {c.evidence}")
        if c.status in ("fail", "warn", "not_checked"):
            lines.append(f"  - Fix: {c.recommendation}")
    lines += [
        "",
        "## What managed operations change",
        "",
        "A managed team — people plus AI helpers set up around the way the "
        "business already runs — answers every call, books every appointment, "
        "follows up every quote and invoice, and keeps records current, in the "
        "client's own language. Fees are quoted privately in a written plan, "
        "with a fixed price before work starts.",
        "",
        "**Got questions?** That is the next step — one conversation, then a written plan.",
        "",
        "---",
        "Prepared by OVIA Inc — Studio & Lab. Checks verified from the public "
        "website only; phone answering and review scores require a separate test.",
    ]
    return "\n".join(lines) + "\n"


def render_html(result: AuditResult) -> str:
    e = html_lib.escape
    fix_items = "".join(
        f"<li><strong>{e(c.label)}</strong> — {e(c.recommendation)}</li>"
        for c in _top_fixes(result))
    rows = ""
    current = None
    for c in result.checks:
        if c.category != current:
            current = c.category
            rows += f'<tr class="cat"><td colspan="4">{e(current)}</td></tr>'
        rows += (f"<tr><td>{STATUS_ICON[c.status]}</td><td><strong>{e(c.label)}</strong><br>"
                 f"<small>{e(c.evidence)}</small></td><td>{STATUS_WORD[c.status]}</td>"
                 f"<td>{e(c.recommendation) if c.status != 'pass' else '—'}</td></tr>")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Audit — {e(result.business_name)}</title>
<style>
body{{font-family:system-ui,Arial,sans-serif;max-width:860px;margin:40px auto;padding:0 20px;color:#14181d;line-height:1.55}}
.score{{font-size:44px;font-weight:800}} .band{{background:#0A0E14;color:#fff;padding:28px;border-radius:12px}}
.band .score{{color:#2E9BD6}} table{{width:100%;border-collapse:collapse;margin-top:16px}}
td{{border-bottom:1px solid #e3e7ec;padding:8px;vertical-align:top;font-size:14px}}
tr.cat td{{background:#eef4f9;font-weight:700}} small{{color:#5a6572}}
</style></head><body>
<div class="band"><div>Website &amp; Enquiry Audit</div>
<h1 style="margin:6px 0">{e(result.business_name)}</h1>
<div class="score">{result.score:.0f} / 100</div><div>{e(result.grade)}</div>
<div><small style="color:#b9c6d2">{e(result.final_url or result.url)} · Checked {e(result.fetched_at)} · {result.response_ms} ms · HTTP {result.status_code}</small></div></div>
<h2>The fixes that matter most</h2><ol>{fix_items}</ol>
<h2>Full check list</h2><table>{rows}</table>
<h2>What managed operations change</h2>
<p>A managed team — people plus AI helpers set up around the way the business already runs — answers every call, books every appointment, follows up every quote and invoice, and keeps records current, in the client's own language. Fees are quoted privately in a written plan, with a fixed price before work starts.</p>
<p><strong>Got questions?</strong> That is the next step — one conversation, then a written plan.</p>
<p><small>Prepared by OVIA Inc — Studio &amp; Lab. Checks verified from the public website only; phone answering and review scores require a separate test.</small></p>
</body></html>
"""


def render_pdf(result: AuditResult) -> bytes:
    """Clean one-document PDF via reportlab Platypus (same stack as billing_pdf)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1x", parent=styles["Title"], textColor=colors.HexColor("#0A0E14"))
    h2 = ParagraphStyle("h2x", parent=styles["Heading2"], textColor=colors.HexColor("#0A0E14"))
    body = ParagraphStyle("bodyx", parent=styles["BodyText"], fontSize=9.5, leading=13.5)
    small = ParagraphStyle("smallx", parent=body, fontSize=8, textColor=colors.HexColor("#5a6572"))
    accent = colors.HexColor("#2E9BD6")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Audit — {result.business_name}", author="OVIA Inc")
    story = [
        Paragraph("Website &amp; Enquiry Audit", small),
        Paragraph(html_lib.escape(result.business_name), h1),
        Paragraph(f"<b>Score: {result.score:.0f} / 100 — {result.grade}</b>", body),
        Paragraph(f"{html_lib.escape(result.final_url or result.url)} · Checked "
                  f"{html_lib.escape(result.fetched_at)} · {result.response_ms} ms · HTTP {result.status_code}", small),
        Spacer(1, 5 * mm),
        Paragraph("The fixes that matter most", h2),
    ]
    for i, c in enumerate(_top_fixes(result), 1):
        story.append(Paragraph(f"{i}. <b>{html_lib.escape(c.label)}</b> — {html_lib.escape(c.recommendation)}", body))
    story += [Spacer(1, 4 * mm), Paragraph("Full check list", h2)]

    data = [["", "Check", "Result", "Fix"]]
    current = None
    for c in result.checks:
        if c.category != current:
            current = c.category
            data.append(["", f"<b>{html_lib.escape(current)}</b>", "", ""])
        data.append([STATUS_ICON[c.status],
                     Paragraph(f"<b>{html_lib.escape(c.label)}</b><br/><font size='7.5' color='#5a6572'>{html_lib.escape(c.evidence)}</font>", body),
                     STATUS_WORD[c.status],
                     Paragraph(html_lib.escape(c.recommendation) if c.status != "pass" else "—", body)])
    table = Table(data, colWidths=[10 * mm, 62 * mm, 22 * mm, 80 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7dee6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [
        table,
        Spacer(1, 5 * mm),
        Paragraph("What managed operations change", h2),
        Paragraph("A managed team — people plus AI helpers set up around the way the business "
                  "already runs — answers every call, books every appointment, follows up every "
                  "quote and invoice, and keeps records current, in the client's own language. "
                  "Fees are quoted privately in a written plan, with a fixed price before work starts.", body),
        Spacer(1, 3 * mm),
        Paragraph("<b>Got questions?</b> That is the next step — one conversation, then a written plan.", body),
        Spacer(1, 4 * mm),
        Paragraph("Prepared by OVIA Inc — Studio &amp; Lab. Checks verified from the public website "
                  "only; phone answering and review scores require a separate test.", small),
    ]
    doc.build(story)
    return buf.getvalue()

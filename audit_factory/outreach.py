"""Outreach packet generator (v0.2) — STAGED DRAFTS ONLY.

Reads audit JSON files and writes one packet per prospect:
  - recommended channel (email > form > phone) from contacts found on the
    prospect's own site during the audit
  - an exact draft message referencing that prospect's real top fixes
  - a 30-second call script for phone-only prospects

Nothing in this module sends anything. Packets are internal drafts that
wait for explicit approval, per prospect or per batch. Drafts carry no
public prices (OVIA rule) and close with "Got questions?".
Tainted audits (HTTP 403 or a failed fetch, where the score may reflect a
blocked checker rather than the real site) are flagged DO NOT USE.
"""

from __future__ import annotations

import json
from pathlib import Path

TAINT_STATUS = {403, 0}


def load_audit(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def is_tainted(audit: dict) -> bool:
    return audit.get("status_code") in TAINT_STATUS


def channel_for(audit: dict) -> str:
    contacts = audit.get("contacts") or {}
    if contacts.get("emails"):
        return "email"
    if contacts.get("has_form"):
        return "form"
    return "phone"


def top_fixes(audit: dict, n: int = 3) -> list[dict]:
    fixes = [c for c in audit.get("checks", []) if c["status"] in ("fail", "warn")]
    return sorted(fixes, key=lambda c: -c["max_points"])[:n]


def site_language(audit: dict) -> str:
    for c in audit.get("checks", []):
        if c["id"] == "multilingual":
            langs = c["evidence"].replace("Languages detected on page:", "").strip()
            return langs
    return "EN"


def render_packet(audit: dict, prospect_phone: str = "") -> str:
    name = audit["business_name"]
    score = audit["score"]
    channel = channel_for(audit)
    contacts = audit.get("contacts") or {}
    fixes = top_fixes(audit)
    fix_lines = "\n".join(
        f"- **{f['label']}** — {f['evidence']}" for f in fixes) or "- No major gaps found."
    fix_sentence = "; ".join(f["label"].lower() for f in fixes[:2])
    if fix_sentence:
        gap_clause = f"The strongest gaps found: {fix_sentence}."
        script_gap_clause = f"Two findings stand out: {fix_sentence}."
    else:
        # Clean site: the honest angle is the one thing a website cannot
        # prove — what happens on an unanswered call.
        gap_clause = ("No gaps on the website itself — a clean result. The one thing "
                      "a website cannot prove is what a client hears when a call goes "
                      "unanswered, and that test is the natural next step.")
        script_gap_clause = ("The website itself is clean. One question remains: "
                             "what a client hears when a call goes unanswered.")

    if is_tainted(audit):
        header_status = (
            f"⛔ **DO NOT USE — tainted audit.** Fetch returned HTTP "
            f"{audit.get('status_code')}; the score may reflect a blocked checker, "
            f"not the real site. Re-verify by human browser look before any contact.")
    else:
        header_status = "Staged draft — nothing sent. Approval required before any contact."

    if channel == "email":
        route = f"Email to: {', '.join(contacts['emails'])}"
        draft = f"""Subject: {name} — website audit, {score:.0f}/100

Bonjour / Hello,

A short audit of the {name} website was run this week — the site scored
{score:.0f}/100 on how easily a new client can reach the business, book, and
get followed up. {gap_clause}

The full one-page audit is attached. Managed operations — every call
answered, every appointment booked, every quote followed up, in the
client's own language — close exactly those gaps. Fees are quoted
privately in a written plan.

Got questions? One short call is enough to walk through the findings.

— OVIA Inc, Studio & Lab"""
    elif channel == "form":
        route = f"Website enquiry form at {audit.get('final_url') or audit.get('url')}"
        draft = f"""Form message for {name}:

Bonjour / Hello — a short audit of your website scored {score:.0f}/100 on
how easily a new client can reach you, book, and get followed up. {gap_clause}
The full audit is ready to send on request — managed
operations close exactly those gaps: every call answered, every appointment
booked, every quote followed up, in the client's own language. Got
questions? Reply here and the audit follows the same day. — OVIA Inc"""
    else:
        route = f"Phone only: {prospect_phone or (contacts.get('phones_in_text') or ['no number in site text'])[0]}"
        draft = f"""30-second call script for {name} (French first if answered in French):

"Bonjour, OVIA Inc — a short audit of your website was run this week,
{score:.0f} out of 100 on how easily clients can reach you and book.
{script_gap_clause} The audit is free to hear —
two minutes now, or a better time today?"

If interest: walk the top fixes, offer to send the full audit, close on
one question — "Got questions after seeing it? A written plan follows,
fixed price, no obligation."
If no interest: thank, offer the audit by email/form anyway, end clean."""

    return f"""# Outreach packet — {name}

{header_status}

- **Score:** {score:.0f}/100 — {audit.get('grade', '')}
- **Site:** {audit.get('final_url') or audit.get('url')}
- **Channel:** {channel} — {route}
- **Site languages detected:** {site_language(audit)}
- **Contacts found on site:** emails {contacts.get('emails') or 'none'} · phones {contacts.get('phones_in_text') or 'none'} · form {'yes' if contacts.get('has_form') else 'no'}

## Top fixes to reference

{fix_lines}

## Draft (exact text, approval required)

{draft}

---
Internal packet — OVIA funnel: audit → conversation → written plan with a
fixed price → managed Operations Manager install. No prices in the draft,
by rule.
"""


def opportunity_score(audit: dict, category: str = "") -> float:
    """Higher = call first. Gap size × channel reachability × trade urgency."""
    if is_tainted(audit):
        return -1.0
    gap = 100 - float(audit.get("score", 100))
    channel_bonus = {"email": 20, "form": 12, "phone": 5}[channel_for(audit)]
    urgency = 0
    cat = (category or "").lower()
    if "plumb" in cat or "hvac" in cat:
        urgency = 15
    elif "dental" in cat:
        urgency = 10
    elif "salon" in cat:
        urgency = 6
    return round(gap + channel_bonus + urgency, 1)


def generate_packets(audits_dir: Path, out_dir: Path,
                     categories: dict[str, str] | None = None,
                     phones: dict[str, str] | None = None,
                     exclude_names: set[str] | None = None) -> list[dict]:
    """Write one packet per audit JSON. Returns ranking rows, best first."""
    categories = categories or {}
    phones = phones or {}
    exclude_names = exclude_names or set()
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(audits_dir.glob("*.json")):
        audit = load_audit(path)
        name = audit["business_name"]
        if name in exclude_names:
            continue
        (out_dir / f"{path.stem}-outreach.md").write_text(
            render_packet(audit, phones.get(name, "")), encoding="utf-8")
        rows.append({
            "name": name,
            "score": audit["score"],
            "channel": channel_for(audit),
            "tainted": is_tainted(audit),
            "opportunity": opportunity_score(audit, categories.get(name, "")),
            "packet": f"{path.stem}-outreach.md",
        })
    rows.sort(key=lambda r: -r["opportunity"])
    return rows


def render_priority(rows: list[dict]) -> str:
    lines = [
        "# Prospect priority — call order",
        "",
        "Ranked by gap size × reachable channel × trade urgency. "
        "Tainted audits sit at the bottom and are never used until re-verified.",
        "",
        "| # | Prospect | Audit | Channel | Opportunity | Packet |",
        "|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        flag = " ⛔ tainted" if r["tainted"] else ""
        lines.append(
            f"| {i} | {r['name']}{flag} | {r['score']:.0f}/100 | {r['channel']} "
            f"| {r['opportunity'] if r['opportunity'] >= 0 else '—'} | {r['packet']} |")
    lines += ["", "Sending rule: nothing leaves without explicit approval, "
              "per batch. Drafts carry no public prices and close with "
              "“Got questions?”."]
    return "\n".join(lines) + "\n"

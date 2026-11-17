"""Offline tests: fixture HTML in, scores and reports out. No network."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audit_factory.checks import run_checks
from audit_factory.cli import slugify
from audit_factory.report import render_html, render_markdown, render_pdf

GOOD_HTML = """<!DOCTYPE html><html><head>
<title>Clinique Sourire — Dentist in Sainte-Agathe</title>
<meta name="description" content="Family dentistry in Sainte-Agathe-des-Monts. Book an appointment today.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script type="application/ld+json">{"@type":"Dentist"}</script>
</head><body>
<h1>Family dentistry, managed with care</h1>
<p>Call us: <a href="tel:+18193240000">(819) 324-0000</a> or
<a href="mailto:bonjour@exemple.ca">bonjour@exemple.ca</a></p>
<p>Book an appointment — prendre rendez-vous en ligne. Get a free quote / devis gratuit.</p>
<p>Monday to Friday, 9am to 5pm. 123 Rue Principale, Sainte-Agathe-des-Monts.</p>
<p>Accueil — nous vous accueillons avec le sourire, contactez nous.</p>
<form action="/contact"><input type="text" name="n"><input type="submit" value="Send"></form>
<img src="team.jpg" alt="The clinic team">
<a href="https://facebook.com/exemple">Facebook</a>
</body></html>"""

BAD_HTML = "<html><head></head><body><p>Welcome.</p></body></html>"


def test_good_site_scores_high():
    r = run_checks("Clinique Sourire", "https://exemple.ca", GOOD_HTML,
                   "https://exemple.ca", 200, 900, 40000)
    assert r.score >= 85, [(c.id, c.status) for c in r.checks]
    assert r.grade == "Strong"


def test_bad_site_scores_low_and_flags_core_gaps():
    r = run_checks("Empty Site", "http://empty.example", BAD_HTML,
                   "http://empty.example", 200, 900, 300)
    by_id = {c.id: c for c in r.checks}
    assert by_id["https"].status == "fail"
    assert by_id["click_to_call"].status == "fail"
    assert by_id["booking"].status == "fail"
    assert by_id["form"].status == "fail"
    assert r.score < 50


def test_unverifiable_checks_are_never_invented():
    r = run_checks("Any", "https://x.ca", GOOD_HTML, "https://x.ca", 200, 100, 1000)
    by_id = {c.id: c for c in r.checks}
    assert by_id["call_answering"].status == "not_checked"
    assert by_id["reviews"].status == "not_checked"


def test_reports_render_and_carry_no_public_prices():
    r = run_checks("Clinique Sourire", "https://exemple.ca", GOOD_HTML,
                   "https://exemple.ca", 200, 900, 40000)
    md = render_markdown(r)
    html = render_html(r)
    pdf = render_pdf(r)
    assert "Clinique Sourire" in md and "Got questions?" in md
    assert "Clinique Sourire" in html
    assert pdf[:4] == b"%PDF" and len(pdf) > 3000
    for text in (md, html):
        assert "$2,500" not in text and "$1,250" not in text and "$497" not in text


def test_slugify():
    assert slugify("Clinique Sourire & Fils!") == "clinique-sourire-fils"
    assert slugify("  ") == "business"

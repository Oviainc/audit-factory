"""v0.2 tests: contact capture, channel routing, taint flag, ranking."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audit_factory.checks import run_checks
from audit_factory.outreach import channel_for, is_tainted, opportunity_score, render_packet
from test_audit_factory import GOOD_HTML


def _audit(html=GOOD_HTML, status=200):
    return run_checks("Clinique Sourire", "https://exemple.ca", html,
                      "https://exemple.ca", status, 900, 40000)


def test_contacts_captured_from_page():
    r = _audit()
    assert "bonjour@exemple.ca" in r.contacts["emails"]
    assert r.contacts["tel_links"], "tel: link must be captured"
    assert r.contacts["has_form"] is True


def test_channel_prefers_email_then_form_then_phone():
    from audit_factory.checks import result_to_dict
    d = result_to_dict(_audit())
    assert channel_for(d) == "email"
    d2 = {"contacts": {"emails": [], "has_form": True}}
    assert channel_for(d2) == "form"
    d3 = {"contacts": {"emails": [], "has_form": False}}
    assert channel_for(d3) == "phone"


def test_tainted_audits_flagged_and_unranked():
    blocked = {"status_code": 403, "score": 17.1, "contacts": {}}
    assert is_tainted(blocked)
    assert opportunity_score(blocked) == -1.0
    packet = render_packet({**blocked, "business_name": "Blocked Co",
                            "url": "https://x.ca", "final_url": "https://x.ca",
                            "grade": "Losing enquiries", "checks": []})
    assert "DO NOT USE" in packet


def test_packet_has_no_public_prices_and_closes_with_cta():
    from audit_factory.checks import result_to_dict
    packet = render_packet(result_to_dict(_audit()), "+15140000000")
    assert "Got questions?" in packet
    for price in ("$2,500", "$1,250", "$497"):
        assert price not in packet


def test_clean_site_packet_uses_unanswered_call_angle():
    clean = {"business_name": "Perfect Co", "score": 100.0, "grade": "Strong",
             "url": "https://p.ca", "final_url": "https://p.ca", "status_code": 200,
             "contacts": {"emails": ["info@p.ca"], "has_form": True},
             "checks": [{"id": "multilingual", "status": "pass", "max_points": 4,
                         "label": "Multilingual", "evidence": "Languages detected on page: EN"}]}
    packet = render_packet(clean)
    assert "gaps found: ." not in packet
    assert "unanswered" in packet

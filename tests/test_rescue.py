"""Rescue generator tests: staging, exclusion, priority, languages."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audit_factory.rescue import build_campaign, render_campaign, stage_for_age

TODAY = date(2026, 11, 15)
ROWS = [
    {"id": "1", "customer": "Mme Roy", "email": "roy@x.ca", "phone": "",
     "total": "12000", "created_at": "2026-10-01", "status": "draft", "language": "fr"},
    {"id": "2", "customer": "Mr Lee", "email": "", "phone": "+15140000000",
     "total": "3000", "created_at": "2026-11-05", "status": "draft", "language": "en"},
    {"id": "3", "customer": "Done Deal", "email": "d@x.ca", "phone": "",
     "total": "9000", "created_at": "2026-09-01", "status": "approved", "language": "en"},
    {"id": "4", "customer": "Fresh", "email": "f@x.ca", "phone": "",
     "total": "5000", "created_at": "2026-11-14", "status": "draft", "language": "es"},
]


def test_stages_by_age():
    assert stage_for_age(50) == "last-call"
    assert stage_for_age(31) == "expiry-warning"
    assert stage_for_age(15) == "value-reminder"
    assert stage_for_age(8) == "gentle-check-in"
    assert stage_for_age(2) == "too-fresh"


def test_campaign_excludes_approved_and_fresh_and_orders_by_priority():
    items = build_campaign(ROWS, today=TODAY)
    ids = [i.quote_id for i in items]
    assert ids == ["1", "2"]  # approved #3 excluded, fresh #4 excluded
    assert items[0].stage == "last-call" and items[0].language == "fr"
    assert "Des questions" in items[0].draft
    assert items[1].stage == "gentle-check-in"


def test_campaign_render_states_value_and_no_send_rule():
    md = render_campaign(build_campaign(ROWS, today=TODAY), "Acme Reno", "2026-11-15")
    assert "$15,000.00 in unsigned work" in md
    assert "nothing sent" in md
    assert "$2,500" not in md and "$497" not in md

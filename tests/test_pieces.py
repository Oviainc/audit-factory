from datetime import date
from pathlib import Path

from audit_factory.pieces import load_items, render_campaign, stage_for

CSV = """client,email,phone,language,pieces_missing,deadline
Client A,a@example.com,,fr,T4; Releve 1,2027-04-30
Client B,,514-555-0100,en,NOA,2026-11-20
Client C,c@example.com,,es,,2027-04-30
"""


def _items(tmp_path: Path):
    p = tmp_path / "clients.csv"
    p.write_text(CSV, encoding="utf-8")
    return load_items(p, today=date(2026, 11, 17))


def test_stage_boundaries():
    assert stage_for(-1) == "overdue"
    assert stage_for(3) == "final-call"
    assert stage_for(10) == "urgent"
    assert stage_for(21) == "pressing"
    assert stage_for(45) == "gentle"
    assert stage_for(90) == "early-list"


def test_complete_files_are_skipped_and_order_is_tightest_first(tmp_path):
    items = _items(tmp_path)
    assert [i.client for i in items] == ["Client B", "Client A"]


def test_drafts_name_the_pieces_in_the_client_language(tmp_path):
    items = _items(tmp_path)
    a = next(i for i in items if i.client == "Client A")
    assert "T4" in a.draft and "Bonjour" in a.draft
    campaign = render_campaign(items)
    assert "nothing sent" in campaign

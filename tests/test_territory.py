import json
from pathlib import Path

from audit_factory.territory import load_territory, render_report, slugify

ROSTER = """name,url,sector,municipality
Café Un,https://a.example,Restauration,Val-des-Monts
Café Deux,https://b.example,Restauration,Lac-Beau
Hotel Trois,https://c.example,Hébergement,Val-des-Monts
"""


def _territory(tmp_path: Path):
    roster = tmp_path / "roster.csv"
    roster.write_text(ROSTER, encoding="utf-8")
    audits = tmp_path / "audits"
    audits.mkdir()
    for slug, score in [("cafe-un", 40.0), ("cafe-deux", 80.0), ("hotel-trois", 60.0)]:
        (audits / f"{slug}.json").write_text(
            json.dumps({"score": score, "grade": "g"}), encoding="utf-8")
    return load_territory(roster, audits)


def test_slugify_accents():
    assert slugify("Café L'Opium") == "cafe-l-opium"


def test_means_and_matrix(tmp_path):
    t = _territory(tmp_path)
    assert t.mean() == 60.0
    assert t.mean(t.by("sector")["Restauration"]) == 60.0
    assert t.matrix()["Hébergement"]["Val-des-Monts"] == 60.0


def test_cohort_and_report(tmp_path):
    t = _territory(tmp_path)
    assert [r.name for r in t.cohort()] == ["Café Un", "Hotel Trois"]
    report = render_report(t, "MRC Exemple")
    assert "Score territorial moyen : 60.0/100" in report
    assert "Cohorte de rattrapage" in report

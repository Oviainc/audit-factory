"""Baromètre Territorial de l'Accueil — territorial benchmark builder.

Idea 17, promoted 2026-11-17 from the daily review. A territory
campaign for an MRC, chamber of commerce or economic-development body:
a roster of the territory's client-facing businesses (CSV with sector
and municipality tags), each one site-audited by the existing Audit
Factory, then compared — sector × municipality matrix, territory
headline score, weakest links, and a cohort follow-on tracker naming
the businesses a funded catch-up cohort would serve first.

Inputs:
    roster.csv      name,url,sector,municipality
    audits_dir/     one <slug>.json per business, Audit Factory format

Output: one council-ready Markdown report. Mystery-call scripts for
the campaign are generated alongside (the calls themselves are placed
by humans; nothing here contacts anyone).
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

COHORT_THRESHOLD = 70.0  # below this score a business joins the cohort list


def slugify(name: str) -> str:
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")


@dataclass
class TerritoryRow:
    name: str
    url: str
    sector: str
    municipality: str
    score: float | None  # None when no audit JSON was found
    grade: str = ""


@dataclass
class Territory:
    rows: list[TerritoryRow] = field(default_factory=list)

    @property
    def audited(self) -> list[TerritoryRow]:
        return [r for r in self.rows if r.score is not None]

    def mean(self, rows: list[TerritoryRow] | None = None) -> float:
        rows = self.audited if rows is None else [r for r in rows if r.score is not None]
        return round(sum(r.score for r in rows) / len(rows), 1) if rows else 0.0

    def by(self, key: str) -> dict[str, list[TerritoryRow]]:
        groups: dict[str, list[TerritoryRow]] = {}
        for r in self.audited:
            groups.setdefault(getattr(r, key), []).append(r)
        return dict(sorted(groups.items(), key=lambda kv: self.mean(kv[1])))

    def matrix(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for sector, srows in self.by("sector").items():
            out[sector] = {}
            munis: dict[str, list[TerritoryRow]] = {}
            for r in srows:
                munis.setdefault(r.municipality, []).append(r)
            for muni, mrows in munis.items():
                out[sector][muni] = self.mean(mrows)
        return out

    def cohort(self) -> list[TerritoryRow]:
        return sorted((r for r in self.audited if r.score < COHORT_THRESHOLD),
                      key=lambda r: r.score)


def load_territory(roster_csv: Path, audits_dir: Path) -> Territory:
    t = Territory()
    with roster_csv.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("name") or "").strip()
            if not name:
                continue
            score, grade = None, ""
            audit_file = audits_dir / f"{slugify(name)}.json"
            if audit_file.exists():
                data = json.loads(audit_file.read_text(encoding="utf-8"))
                score, grade = float(data["score"]), data.get("grade", "")
            t.rows.append(TerritoryRow(
                name=name, url=(row.get("url") or "").strip(),
                sector=(row.get("sector") or "Autre").strip(),
                municipality=(row.get("municipality") or "").strip(),
                score=score, grade=grade))
    return t


def render_report(t: Territory, territory_name: str) -> str:
    L = [f"# Baromètre de l'accueil — {territory_name}", ""]
    L.append(f"**Score territorial moyen : {t.mean()}/100** — "
             f"{len(t.audited)} entreprises auditées sur {len(t.rows)} au registre.")
    L.append("")
    L.append("## Par secteur")
    L.append("")
    L.append("| Secteur | Entreprises | Score moyen |")
    L.append("|---|---|---|")
    for sector, rows in t.by("sector").items():
        L.append(f"| {sector} | {len(rows)} | {t.mean(rows)} |")
    L.append("")
    L.append("## Par municipalité")
    L.append("")
    L.append("| Municipalité | Entreprises | Score moyen |")
    L.append("|---|---|---|")
    for muni, rows in t.by("municipality").items():
        L.append(f"| {muni} | {len(rows)} | {t.mean(rows)} |")
    L.append("")
    L.append("## Matrice secteur × municipalité (scores moyens)")
    L.append("")
    munis = sorted({r.municipality for r in t.audited})
    L.append("| Secteur | " + " | ".join(munis) + " |")
    L.append("|---|" + "---|" * len(munis))
    matrix = t.matrix()
    for sector in sorted(matrix):
        cells = [str(matrix[sector].get(m, "—")) for m in munis]
        L.append(f"| {sector} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("## Entreprises les plus faibles")
    L.append("")
    for r in sorted(t.audited, key=lambda r: r.score)[:10]:
        L.append(f"- {r.name} ({r.municipality}, {r.sector}) — {r.score}/100 — {r.grade}")
    L.append("")
    L.append(f"## Cohorte de rattrapage — suivi (score sous {COHORT_THRESHOLD:.0f})")
    L.append("")
    L.append("| Entreprise | Municipalité | Secteur | Score | Statut |")
    L.append("|---|---|---|---|---|")
    for r in t.cohort():
        L.append(f"| {r.name} | {r.municipality} | {r.sector} | {r.score} | à inviter |")
    L.append("")
    L.append("Rapport préparé par OVIA Inc, Studio & Lab — audits de sites "
             "publics seulement; l'accueil téléphonique fait l'objet des "
             "appels mystères de la campagne. Got questions?")
    return "\n".join(L) + "\n"


MYSTERY_CALL_SCRIPTS = """# Appels mystères — scripts de campagne territoriale

À placer par des humains formés. Aucun enregistrement sans le cadre
légal applicable; l'appelant ne se fait jamais passer pour un client
en détresse réelle.

## Scénario A — heures et accès (FR)
« Bonjour, je prépare une visite chez vous. Quelles sont vos heures
d'ouverture cette fin de semaine, et est-ce qu'il faut réserver? »
Noter : réponse en moins de 4 sonneries? heures exactes données?
invitation claire à réserver?

## Scénario B — prix et disponibilité (FR)
« Bonjour, je cherche [service du secteur] pour deux personnes la
semaine prochaine. Qu'est-ce que vous avez, et ça coûte combien? »
Noter : prix ou fourchette donnés? alternative proposée si complet?
coordonnées prises pour un suivi?

## Scénario C — hours and booking (EN)
"Hello, I'm planning a visit. What are your opening hours this
weekend, and do I need to book ahead?"
Score: answered within 4 rings? exact hours given? clear booking path?

## Grille de notation (par appel, /100)
- Réponse et délai : 25 — Langue de l'appelant respectée : 15
- Exactitude de l'information : 25 — Chemin de réservation offert : 20
- Suivi proposé (rappel, courriel, coordonnées prises) : 15
"""

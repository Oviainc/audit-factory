"""Estimate-Expiry Rescue — campaign generator (staged drafts only).

Works a contractor's unsigned (draft) quotes in age order. Input is a CSV
export with columns:
    id,customer,email,phone,total,created_at,status,language
(total in dollars, created_at YYYY-MM-DD, status draft|approved,
language en|fr|es — anything else defaults to en.)

Every open quote gets a rescue stage by age, a priority score
(age × value), and an exact follow-up draft in the quote's language.
Output is one campaign Markdown file. NOTHING is sent — a human sends
each message after approval, the same rule as outreach packets.
Approved quotes are excluded: those are invoices, and the receivables
flow in ai-receptionist already chases those.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

STAGES = [
    # (min_age_days, stage name)
    (45, "last-call"),
    (30, "expiry-warning"),
    (14, "value-reminder"),
    (7, "gentle-check-in"),
    (0, "too-fresh"),
]

MESSAGES = {
    "en": {
        "gentle-check-in": "Hello {customer}, a quick check-in on quote #{qid} for {total}, sent on {created}. Happy to answer any question, adjust the scope, or book a start date — one reply is enough. Got questions? Just answer here.",
        "value-reminder": "Hello {customer}, quote #{qid} for {total} is still open from {created}. Prices and scheduling are easiest to hold while the quote is current — a short call settles any open point. Got questions? Just answer here.",
        "expiry-warning": "Hello {customer}, quote #{qid} for {total} reaches its validity limit soon. After that date the work would need a fresh estimate. One reply keeps the current price and place in the schedule. Got questions? Just answer here.",
        "last-call": "Hello {customer}, final note on quote #{qid} for {total} from {created}: the file closes this week unless a reply arrives. If the timing is wrong, a one-word answer parks it properly instead of losing it. Got questions? Just answer here.",
    },
    "fr": {
        "gentle-check-in": "Bonjour {customer}, petit suivi sur le devis nº {qid} de {total}, envoyé le {created}. Questions, ajustement de portée ou date de début — une seule réponse suffit. Des questions? Répondez simplement ici.",
        "value-reminder": "Bonjour {customer}, le devis nº {qid} de {total} est toujours ouvert depuis le {created}. Le prix et la place au calendrier se gardent plus facilement pendant que le devis est courant. Des questions? Répondez simplement ici.",
        "expiry-warning": "Bonjour {customer}, le devis nº {qid} de {total} arrive bientôt à sa limite de validité. Après cette date, les travaux demanderont une nouvelle estimation. Une réponse garde le prix actuel et la place au calendrier. Des questions? Répondez simplement ici.",
        "last-call": "Bonjour {customer}, dernier mot sur le devis nº {qid} de {total} du {created} : le dossier se ferme cette semaine sans réponse. Si le moment ne convient pas, un seul mot le met en attente proprement. Des questions? Répondez simplement ici.",
    },
    "es": {
        "gentle-check-in": "Hola {customer}, un breve seguimiento sobre el presupuesto nº {qid} por {total}, enviado el {created}. Preguntas, ajustes o fecha de inicio: basta una respuesta. ¿Preguntas? Responda aquí mismo.",
        "value-reminder": "Hola {customer}, el presupuesto nº {qid} por {total} sigue abierto desde el {created}. El precio y el lugar en el calendario se conservan mejor mientras el presupuesto está vigente. ¿Preguntas? Responda aquí mismo.",
        "expiry-warning": "Hola {customer}, el presupuesto nº {qid} por {total} llega pronto a su límite de validez. Después de esa fecha, el trabajo necesitará una nueva estimación. Una respuesta conserva el precio actual y el lugar en el calendario. ¿Preguntas? Responda aquí mismo.",
        "last-call": "Hola {customer}, último aviso sobre el presupuesto nº {qid} por {total} del {created}: el expediente se cierra esta semana sin respuesta. Si el momento no conviene, una sola palabra lo deja en espera correctamente. ¿Preguntas? Responda aquí mismo.",
    },
}


@dataclass
class RescueItem:
    quote_id: str
    customer: str
    email: str
    phone: str
    total: float
    created: str
    age_days: int
    stage: str
    priority: float
    language: str
    draft: str


def stage_for_age(age_days: int) -> str:
    for minimum, name in STAGES:
        if age_days >= minimum:
            return name
    return "too-fresh"


def load_quotes(csv_path: Path) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def build_campaign(rows: list[dict], today: date | None = None,
                   business_name: str = "the business") -> list[RescueItem]:
    """Pure: quote rows in, staged rescue items out, priority first."""
    today = today or date.today()
    items = []
    for row in rows:
        if (row.get("status") or "draft").strip().lower() != "draft":
            continue  # approved quotes became invoices — receivables' job
        created = date.fromisoformat((row.get("created_at") or "")[:10])
        age = max((today - created).days, 0)
        stage = stage_for_age(age)
        if stage == "too-fresh":
            continue
        total = float(row.get("total") or 0)
        lang = (row.get("language") or "en").strip().lower()
        if lang not in MESSAGES:
            lang = "en"
        draft = MESSAGES[lang][stage].format(
            customer=(row.get("customer") or "").strip() or "there",
            qid=row.get("id", ""), total=f"${total:,.2f}",
            created=created.isoformat())
        items.append(RescueItem(
            quote_id=str(row.get("id", "")),
            customer=(row.get("customer") or "").strip(),
            email=(row.get("email") or "").strip(),
            phone=(row.get("phone") or "").strip(),
            total=total, created=created.isoformat(), age_days=age,
            stage=stage, priority=round(age * max(total, 1) / 100, 1),
            language=lang, draft=draft))
    return sorted(items, key=lambda i: -i.priority)


def render_campaign(items: list[RescueItem], business_name: str,
                    generated_on: str) -> str:
    total_value = sum(i.total for i in items)
    lines = [
        f"# Estimate-Expiry Rescue — {business_name}",
        "",
        f"Generated {generated_on} · **{len(items)} open quotes · "
        f"${total_value:,.2f} in unsigned work** · staged drafts only, "
        f"nothing sent — each message goes out by hand after approval.",
        "",
        "| # | Quote | Customer | Age | Stage | Value | Channel |",
        "|---|---|---|---|---|---|---|",
    ]
    for n, i in enumerate(items, 1):
        channel = i.email or i.phone or "no contact on file"
        lines.append(f"| {n} | #{i.quote_id} | {i.customer} | {i.age_days}d "
                     f"| {i.stage} | ${i.total:,.2f} | {channel} |")
    lines += ["", "## Drafts in send order", ""]
    for n, i in enumerate(items, 1):
        lines += [f"### {n}. Quote #{i.quote_id} — {i.customer} "
                  f"({i.stage}, {i.language})", "", i.draft, ""]
    lines += ["---", "Rule: one stage per quote per week maximum. A reply "
              "of any kind stops the sequence for that quote."]
    return "\n".join(lines) + "\n"

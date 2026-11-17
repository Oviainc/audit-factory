"""Chasse aux Pièces — document-chase campaign generator (staged drafts).

Built for accounting and bookkeeping firms before and during tax season:
the hours preparers lose chasing clients for missing slips, receipts and
forms. Input is a CSV export with columns:
    client,email,phone,language,pieces_missing,deadline
(pieces_missing is a semicolon-separated list, deadline YYYY-MM-DD,
language en|fr|es — anything else defaults to en.)

Each open client file gets a chase stage by days left before the
deadline, and an exact follow-up draft in the client's language naming
the missing pieces. Output is one campaign Markdown file. NOTHING is
sent — a human sends each message after approval, the same rule as
outreach packets and Estimate-Expiry Rescue.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

STAGES = [
    # (max days left, stage name) — first match wins, tightest first
    (0, "overdue"),
    (3, "final-call"),
    (10, "urgent"),
    (21, "pressing"),
    (45, "gentle"),
    (10**9, "early-list"),
]

MESSAGES = {
    "en": {
        "early-list": "Hello {client}, tax season is coming. To keep your file moving, the pieces still needed are: {pieces}. Sending them as they arrive is easiest — one reply per piece is fine. Got questions? Just answer here.",
        "gentle": "Hello {client}, a gentle note on your file: the pieces still missing are {pieces}. The deadline is {deadline}. Sending them this week keeps your place in the preparation queue. Got questions? Just answer here.",
        "pressing": "Hello {client}, your file is waiting on: {pieces}. With the deadline on {deadline}, files completed now are prepared first. A photo of each piece, sent here, is accepted. Got questions? Just answer here.",
        "urgent": "Hello {client}, urgent: {pieces} are still missing and the deadline is {deadline}. Without them the return cannot be completed on time. Send photos of the pieces today and the file stays on schedule. Got questions? Just answer here.",
        "final-call": "Hello {client}, final call before the {deadline} deadline: {pieces} are still missing. Send them today, even as photos — after the deadline the file moves to late processing. Got questions? Just answer here.",
        "overdue": "Hello {client}, the {deadline} deadline has passed and your file still needs: {pieces}. Send them now to limit late fees and interest, and the file is completed in arrival order. Got questions? Just answer here.",
    },
    "fr": {
        "early-list": "Bonjour {client}, la saison des impôts approche. Pour faire avancer votre dossier, les pièces encore requises sont : {pieces}. Les envoyer au fur et à mesure est le plus simple — une réponse par pièce suffit. Des questions? Répondez simplement ici.",
        "gentle": "Bonjour {client}, petit mot sur votre dossier : les pièces encore manquantes sont {pieces}. L'échéance est le {deadline}. Les envoyer cette semaine garde votre place dans la file de préparation. Des questions? Répondez simplement ici.",
        "pressing": "Bonjour {client}, votre dossier attend : {pieces}. Avec l'échéance du {deadline}, les dossiers complets maintenant sont préparés en premier. Une photo de chaque pièce, envoyée ici, est acceptée. Des questions? Répondez simplement ici.",
        "urgent": "Bonjour {client}, urgent : {pieces} manquent toujours et l'échéance est le {deadline}. Sans elles, la déclaration ne peut pas être terminée à temps. Envoyez des photos des pièces aujourd'hui et le dossier reste au calendrier. Des questions? Répondez simplement ici.",
        "final-call": "Bonjour {client}, dernier appel avant l'échéance du {deadline} : {pieces} manquent toujours. Envoyez-les aujourd'hui, même en photo — après l'échéance, le dossier passe au traitement tardif. Des questions? Répondez simplement ici.",
        "overdue": "Bonjour {client}, l'échéance du {deadline} est passée et votre dossier attend toujours : {pieces}. Envoyez-les maintenant pour limiter pénalités et intérêts; le dossier sera terminé par ordre d'arrivée. Des questions? Répondez simplement ici.",
    },
    "es": {
        "early-list": "Hola {client}, se acerca la temporada de impuestos. Para avanzar su expediente, las piezas que aún se necesitan son: {pieces}. Enviarlas a medida que llegan es lo más fácil; basta una respuesta por pieza. ¿Preguntas? Responda aquí mismo.",
        "gentle": "Hola {client}, una nota breve sobre su expediente: las piezas que aún faltan son {pieces}. La fecha límite es el {deadline}. Enviarlas esta semana conserva su lugar en la fila de preparación. ¿Preguntas? Responda aquí mismo.",
        "pressing": "Hola {client}, su expediente espera: {pieces}. Con la fecha límite del {deadline}, los expedientes completos ahora se preparan primero. Una foto de cada pieza, enviada aquí, es aceptada. ¿Preguntas? Responda aquí mismo.",
        "urgent": "Hola {client}, urgente: aún faltan {pieces} y la fecha límite es el {deadline}. Sin ellas la declaración no puede completarse a tiempo. Envíe fotos de las piezas hoy y el expediente se mantiene en calendario. ¿Preguntas? Responda aquí mismo.",
        "final-call": "Hola {client}, último aviso antes de la fecha límite del {deadline}: aún faltan {pieces}. Envíelas hoy, incluso en foto; después de la fecha límite el expediente pasa a procesamiento tardío. ¿Preguntas? Responda aquí mismo.",
        "overdue": "Hola {client}, la fecha límite del {deadline} ya pasó y su expediente aún necesita: {pieces}. Envíelas ahora para limitar multas e intereses; el expediente se completa por orden de llegada. ¿Preguntas? Responda aquí mismo.",
    },
}


@dataclass
class PieceItem:
    client: str
    email: str
    phone: str
    language: str
    pieces: list[str]
    deadline: date
    days_left: int
    stage: str
    draft: str


def stage_for(days_left: int) -> str:
    for limit, name in STAGES:
        if days_left <= limit:
            return name
    return "early-list"


def load_items(csv_path: Path, today: date | None = None) -> list[PieceItem]:
    today = today or date.today()
    items: list[PieceItem] = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            pieces = [p.strip() for p in (row.get("pieces_missing") or "").split(";") if p.strip()]
            if not pieces:
                continue  # complete file — nothing to chase
            deadline = date.fromisoformat((row.get("deadline") or "").strip())
            days_left = (deadline - today).days
            stage = stage_for(days_left)
            lang = (row.get("language") or "en").strip().lower()
            if lang not in MESSAGES:
                lang = "en"
            draft = MESSAGES[lang][stage].format(
                client=(row.get("client") or "").strip(),
                pieces=", ".join(pieces),
                deadline=deadline.isoformat(),
            )
            items.append(PieceItem(
                client=(row.get("client") or "").strip(),
                email=(row.get("email") or "").strip(),
                phone=(row.get("phone") or "").strip(),
                language=lang, pieces=pieces, deadline=deadline,
                days_left=days_left, stage=stage, draft=draft))
    # tightest deadline first, then most pieces missing
    items.sort(key=lambda i: (i.days_left, -len(i.pieces)))
    return items


def render_campaign(items: list[PieceItem]) -> str:
    lines = ["# Chasse aux Pièces — campaign (staged drafts, nothing sent)", ""]
    lines.append(f"{len(items)} open client file(s), tightest deadline first.")
    lines.append("")
    for i in items:
        channel = i.email or i.phone or "no contact on file"
        lines.append(f"## {i.client} — {i.stage} ({i.days_left} day(s) left, {len(i.pieces)} piece(s))")
        lines.append(f"Channel: {channel} · Language: {i.language} · Deadline: {i.deadline.isoformat()}")
        lines.append("")
        lines.append(i.draft)
        lines.append("")
    return "\n".join(lines)

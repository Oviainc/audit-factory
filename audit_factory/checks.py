"""Site fetching, HTML parsing, checks and scoring.

Only the standard library plus httpx (already in the ai-receptionist
requirements). Parsing uses html.parser so the factory runs in the
receptionist venv with no new dependency.
"""

from __future__ import annotations

import json
import re
import ssl
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

USER_AGENT = "AuditFactory/0.1 (+website audit; respects robots intent, single page fetch)"


@dataclass
class Check:
    id: str
    category: str
    label: str
    status: str  # pass | warn | fail | not_checked
    points: float
    max_points: float
    evidence: str
    recommendation: str


@dataclass
class AuditResult:
    business_name: str
    url: str
    final_url: str = ""
    fetched_at: str = ""
    response_ms: int = 0
    status_code: int = 0
    page_bytes: int = 0
    checks: list[Check] = field(default_factory=list)
    contacts: dict = field(default_factory=dict)

    @property
    def score(self) -> float:
        earned = sum(c.points for c in self.checks if c.status != "not_checked")
        possible = sum(c.max_points for c in self.checks if c.status != "not_checked")
        return round(100 * earned / possible, 1) if possible else 0.0

    @property
    def grade(self) -> str:
        s = self.score
        if s >= 85:
            return "Strong"
        if s >= 70:
            return "Solid, with gaps"
        if s >= 50:
            return "Leaking enquiries"
        return "Losing enquiries daily"


class PageParser(HTMLParser):
    """Collects exactly the signals the checks need — nothing more."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self._in_title = False
        self.meta: dict[str, str] = {}
        self.h1_count = 0
        self.links: list[str] = []
        self.forms = 0
        self.form_has_submit = False
        self.images = 0
        self.images_with_alt = 0
        self.has_jsonld = False
        self.text_parts: list[str] = []
        self._skip_text = 0  # inside script/style

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag in ("script", "style"):
            self._skip_text += 1
            if tag == "script" and a.get("type") == "application/ld+json":
                self.has_jsonld = True
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key and a.get("content"):
                self.meta[key] = a["content"]
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "a":
            if a.get("href"):
                self.links.append(a["href"])
        elif tag == "form":
            self.forms += 1
        elif tag in ("input", "button"):
            if (a.get("type") or "").lower() in ("submit",):
                self.form_has_submit = True
        elif tag == "img":
            self.images += 1
            if (a.get("alt") or "").strip():
                self.images_with_alt += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("script", "style") and self._skip_text:
            self._skip_text -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        if not self._skip_text:
            self.text_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join(" ".join(self.title_parts).split())

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.text_parts).split())


BOOKING_WORDS = [
    "book", "booking", "appointment", "schedule", "consultation", "reserve",
    "reservation", "rendez-vous", "prendre rendez-vous", "réserver", "reserver",
    "cita", "reservar",
]
QUOTE_WORDS = ["quote", "estimate", "devis", "soumission", "cotización", "presupuesto"]
HOURS_RE = re.compile(
    r"\b(mon|tue|wed|thu|fri|sat|sun|monday|tuesday|wednesday|thursday|friday|"
    r"saturday|sunday|lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b"
    r"|\b\d{1,2}\s?(am|pm|h\d{2}|:\d{2})\b",
    re.I,
)
ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+[A-ZÀ-Þ][\wÀ-ÿ'’.-]+(\s+[\wÀ-ÿ'’.-]+){0,3}\s+"
    r"(street|st\.?|avenue|ave\.?|road|rd\.?|boulevard|blvd\.?|rue|chemin|"
    r"drive|dr\.?|lane|ln\.?|court|ct\.?)\b",
    re.I,
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}")
FR_WORDS = [" le ", " la ", " les ", " des ", " nous ", " vous ", " accueil ", " contactez"]
ES_WORDS = [" el ", " la ", " los ", " las ", " nosotros ", " contacto ", " inicio "]


def _check(cid, category, label, ok, max_points, evidence, recommendation, warn=False):
    if ok:
        status, points = "pass", max_points
    elif warn:
        status, points = "warn", max_points / 2
    else:
        status, points = "fail", 0.0
    return Check(cid, category, label, status, points, max_points, evidence, recommendation)


def fetch_page(url: str, timeout: float = 20.0) -> tuple[httpx.Response, int]:
    """Fetch one page. Returns (response, elapsed_ms).

    Sandbox quirk (found live, Nov 11 2026): a NO_PROXY value containing
    bracketed IPv6 entries like [::1] makes httpx raise
    "Invalid port: ':1]'" for every request. Sanitising NO_PROXY to the
    plain localhost forms for the duration of the fetch fixes it without
    touching proxy routing itself.
    """
    import os
    if not urlparse(url).scheme:
        url = "https://" + url
    saved = {k: os.environ.get(k) for k in ("NO_PROXY", "no_proxy")}
    for key in saved:
        if saved[key] and "[" in saved[key]:
            os.environ[key] = "localhost,127.0.0.1"
    try:
        start = time.perf_counter()
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            verify=ssl.create_default_context(),
        ) as client:
            resp = client.get(url)
        return resp, int((time.perf_counter() - start) * 1000)
    finally:
        for key, val in saved.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val


def run_checks(business_name: str, url: str, html: str, final_url: str,
               status_code: int, response_ms: int, page_bytes: int) -> AuditResult:
    """Pure function: HTML in, scored AuditResult out. Fully testable offline."""
    p = PageParser()
    p.feed(html or "")
    text = p.text
    text_low = " " + text.lower() + " "
    links = p.links
    result = AuditResult(
        business_name=business_name, url=url, final_url=final_url,
        status_code=status_code, response_ms=response_ms, page_bytes=page_bytes,
    )
    add = result.checks.append

    # v0.2: real contact details found on the page, for outreach routing.
    # Only what the page itself publishes — nothing looked up elsewhere.
    found_emails = sorted({m.group(0) for m in EMAIL_RE.finditer(text)})
    found_emails += [h[7:].split("?")[0] for h in p.links
                     if h.lower().startswith("mailto:")
                     and h[7:].split("?")[0] not in found_emails]
    found_phones = sorted({m.group(0) for m in PHONE_RE.finditer(text)})
    result.contacts = {
        "emails": found_emails[:5],
        "phones_in_text": found_phones[:5],
        "tel_links": [h for h in p.links if h.lower().startswith("tel:")][:5],
        "has_form": p.forms >= 1,
        "social_links": [h for h in p.links if any(s in h.lower() for s in
                          ("facebook.com", "instagram.com", "linkedin.com"))][:5],
    }

    https = urlparse(final_url or url).scheme == "https"
    add(_check("https", "Reachability", "Secure HTTPS site", https, 8,
               f"Final URL: {final_url or url}",
               "Move the site to HTTPS — browsers flag non-secure sites and visitors leave."))
    add(_check("reachable", "Reachability", "Site answers with success (200)", status_code == 200, 8,
               f"HTTP status {status_code}",
               "Fix the server error/redirect chain so the homepage always loads."))
    fast = 0 < response_ms <= 2500
    slow_warn = 0 < response_ms <= 5000
    add(_check("speed", "Reachability", "Homepage loads fast (under 2.5s)", fast, 8,
               f"Measured {response_ms} ms, page weight {page_bytes // 1024} KB",
               "Trim heavy images/scripts — every extra second costs enquiries.",
               warn=slow_warn and not fast))
    add(_check("title", "Reachability", "Page title present and clear", 10 <= len(p.title) <= 70, 5,
               f'Title: "{p.title[:90]}"' if p.title else "No <title> found",
               "Write a title that names the business, the service and the town."))
    add(_check("meta_desc", "Reachability", "Meta description present", bool(p.meta.get("description")), 5,
               (p.meta.get("description") or "Missing")[:110],
               "Add a one-line description — search results without one get skipped."))
    add(_check("viewport", "Reachability", "Mobile viewport set", "viewport" in p.meta, 6,
               "viewport meta present" if "viewport" in p.meta else "No viewport meta",
               "Most local searches are on phones — the site must be built mobile-first."))
    add(_check("h1", "Reachability", "One clear headline (H1)", p.h1_count == 1, 4,
               f"{p.h1_count} H1 heading(s)",
               "Use one H1 that states the offer in plain words."))

    tel_links = [h for h in links if h.lower().startswith("tel:")]
    add(_check("click_to_call", "Contactability", "Click-to-call phone number", bool(tel_links), 10,
               f"tel: links: {tel_links[:2] if tel_links else 'none'}",
               "Make the phone number tap-to-call on every page — and have every call answered, by a managed AI helper when the team is busy."))
    shown_phone = bool(PHONE_RE.search(text))
    add(_check("phone_shown", "Contactability", "Phone number visible in text", shown_phone, 5,
               "Phone pattern found in page text" if shown_phone else "No phone number in page text",
               "Show the number as readable text, not only inside an image."))
    mailto = [h for h in links if h.lower().startswith("mailto:")]
    shown_email = bool(EMAIL_RE.search(text))
    add(_check("email_shown", "Contactability", "Email contact visible", bool(mailto or shown_email), 5,
               f"mailto: {mailto[:1]}, email in text: {shown_email}",
               "Publish a contact email and route it to a managed inbox with same-day replies."))
    add(_check("form", "Contactability", "Contact / enquiry form present", p.forms >= 1, 8,
               f"{p.forms} form(s) found",
               "Add a short enquiry form — many visitors will write who will never phone. Every submission needs an instant acknowledgement."))

    booking_hit = next((w for w in BOOKING_WORDS if w in text_low), None)
    add(_check("booking", "Booking", "Booking / appointment path visible", bool(booking_hit), 10,
               f'Keyword found: "{booking_hit}"' if booking_hit else "No booking language on the page",
               "Offer direct booking — a managed helper can answer, check the calendar and confirm, in the client's language."))
    quote_hit = next((w for w in QUOTE_WORDS if w in text_low), None)
    add(_check("quote", "Booking", "Quote / estimate path visible", bool(quote_hit), 5,
               f'Keyword found: "{quote_hit}"' if quote_hit else "No quote/estimate language on the page",
               "Add a quote request path and follow every quote up automatically until it closes or is declined."))

    hours_hit = bool(HOURS_RE.search(text))
    add(_check("hours", "Trust", "Opening hours listed", hours_hit, 4,
               "Hours pattern found" if hours_hit else "No hours found on the page",
               "List hours clearly — and cover the closed hours with a managed answering service, not voicemail."))
    addr_hit = bool(ADDRESS_RE.search(text))
    add(_check("address", "Trust", "Street address / service area listed", addr_hit, 4,
               "Address pattern found" if addr_hit else "No street address found on the page",
               "Show the address or service area — local buyers check before they call."))
    social = [h for h in links if any(s in h.lower() for s in
              ("facebook.com", "instagram.com", "linkedin.com", "youtube.com", "tiktok.com"))]
    add(_check("social", "Trust", "Social profiles linked", bool(social), 3,
               f"{len(social)} social link(s)" if social else "No social links",
               "Link the active social profiles so visitors can verify the business."))
    add(_check("jsonld", "Trust", "Structured data (schema.org) present", p.has_jsonld, 3,
               "JSON-LD block found" if p.has_jsonld else "No JSON-LD structured data",
               "Add LocalBusiness structured data so search engines show hours, phone and reviews correctly."))

    langs = ["EN"]
    if sum(w in text_low for w in FR_WORDS) >= 2:
        langs.append("FR")
    if sum(w in text_low for w in ES_WORDS) >= 2:
        langs.append("ES")
    add(_check("multilingual", "Booking", "Multilingual service signal", len(langs) >= 2, 4,
               f"Languages detected on page: {', '.join(langs)}",
               "Serve clients in their own language — EN/FR/ES as standard — on the site, on the phone and in follow-up.",
               warn=len(langs) == 1))
    if p.images:
        alt_ratio = p.images_with_alt / p.images
        add(_check("img_alt", "Reachability", "Images carry descriptions (alt text)", alt_ratio >= 0.8, 3,
                   f"{p.images_with_alt}/{p.images} images with alt text",
                   "Describe images in text — accessibility and search both depend on it.",
                   warn=0.4 <= alt_ratio < 0.8))
    else:
        result.checks.append(Check("img_alt", "Reachability", "Images carry descriptions (alt text)",
                                   "not_checked", 0, 3, "No images on the page",
                                   "Add real photography of the work and describe each image."))

    result.checks.append(Check("call_answering", "Contactability", "What happens when the phone rings unanswered",
                               "not_checked", 0, 0,
                               "Cannot be verified from the website — needs a test call",
                               "Place one test call outside hours. Whatever a client hears then is the real first impression."))
    result.checks.append(Check("reviews", "Trust", "Google rating and review count",
                               "not_checked", 0, 0,
                               "Cannot be verified from the website alone",
                               "Check the Google profile rating in the full review — never guess it from the site."))
    return result


def audit_business(business_name: str, url: str, timeout: float = 20.0) -> AuditResult:
    """Fetch + check. Network errors become a scored result, not a crash."""
    from datetime import datetime, timezone
    fetched_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    try:
        resp, ms = fetch_page(url, timeout=timeout)
        html = resp.text if resp.headers.get("content-type", "").startswith(
            ("text/html", "text/")) or "<html" in resp.text[:200].lower() else ""
        result = run_checks(business_name, url, html, str(resp.url),
                            resp.status_code, ms, len(resp.content))
    except Exception as exc:  # unreachable site is itself a finding
        result = run_checks(business_name, url, "", url, 0, 0, 0)
        for c in result.checks:
            if c.id == "reachable":
                c.evidence = f"Fetch failed: {type(exc).__name__}: {exc}"
    result.fetched_at = fetched_at
    return result


def result_to_dict(result: AuditResult) -> dict:
    return {
        "business_name": result.business_name,
        "url": result.url,
        "final_url": result.final_url,
        "fetched_at": result.fetched_at,
        "response_ms": result.response_ms,
        "status_code": result.status_code,
        "page_bytes": result.page_bytes,
        "score": result.score,
        "grade": result.grade,
        "contacts": result.contacts,
        "checks": [vars(c) for c in result.checks],
    }

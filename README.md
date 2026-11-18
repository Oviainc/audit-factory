![OVIA Audit Factory](docs/banner.svg)

# OVIA Audit Factory

The sales engine and campaign builders behind OVIA's managed AI
operations offers. Three working tools, one rule: **everything is a
staged draft — a human approves before anything is sent.**

## 1. Website audit engine

Give it a business name and a website; it runs 21 checks across
reachability, contactability, booking and trust, scores the site out
of 100, and produces a one-page audit (Markdown / HTML / PDF / JSON)
with the top fixes first. What a website cannot prove — an unanswered
phone, review replies — is reported as **Not checked**, never invented.

```bash
python -m audit_factory "Example Dental" https://example.com --out audits/
python -m audit_factory --csv prospects.csv --out audits/   # batch
```

## 2. Estimate-Expiry Rescue

Works a contractor's unsigned quotes in age order. Quotes CSV in,
staged follow-up campaign out: four stages (gentle check-in,
value reminder, expiry warning, last call), each drafted in the
customer's language — EN / FR / ES.

```bash
python generate_rescue.py quotes.csv campaign.md
```

## 3. Chasse aux Pièces — document chase

Built for accounting firms at tax season: the client files still
missing slips, receipts and forms, chased in stages by days left
before the deadline (early list → gentle → pressing → urgent →
final call → overdue), each draft naming the exact missing pieces,
in EN / FR / ES. Complete files are skipped automatically.

```bash
python generate_pieces.py clients.csv campaign.md
```

## 4. Baromètre Territorial — territorial benchmark

A territory campaign for an MRC, chamber of commerce or
economic-development body: a roster of local businesses with sector
and municipality tags, every one audited, compared in a
sector × municipality matrix, and delivered as a council-ready
report with a catch-up cohort tracker. Mystery-call scripts for the
campaign ship alongside.

```bash
python generate_territory.py roster.csv audits/ "Territory name" out/
```

## 5. Outreach packets

For every audited business, a packet: the channel that actually
reaches it (email, form or phone script), the exact draft, and the
findings it rests on. Drafts carry no public prices and close with
"Got questions?".

## 6. Installable agent packs (examples/)

Config-only installs for the OVIA AI receptionist — each file is a
complete fictional-business configuration, ready to adapt:

- `funeral_switchboard.yaml` — after-hours answering for funeral homes
- `registration_desk.yaml` — bookings and waitlists for camps and ski schools
- `sinistre_first_response.yaml` — 24/7 first-response line for
  water/fire damage restoration firms: timestamped intake, photos
  requested on the call, on-call crew dispatched, insurer-ready file

## Tests

```bash
python -m pytest tests/ -q   # 19 passed
```

## License

Apache-2.0. Built and operated by OVIA Inc, Studio & Lab.

"""Command line: one business in, three report files out.

Usage (from the audit-factory folder, using the receptionist venv):

    python -m audit_factory --name "Clinique Exemple" --url https://exemple.ca
    python -m audit_factory --csv prospects.csv --out audits/

CSV columns: name,url  (header row required)
Outputs per business: <slug>.md, <slug>.html, <slug>.pdf, <slug>.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from .checks import audit_business, result_to_dict
from .report import render_html, render_markdown, render_pdf


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "business"


def run_one(name: str, url: str, out_dir: Path) -> dict:
    result = audit_business(name, url)
    slug = slugify(name)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{slug}.md").write_text(render_markdown(result), encoding="utf-8")
    (out_dir / f"{slug}.html").write_text(render_html(result), encoding="utf-8")
    (out_dir / f"{slug}.pdf").write_bytes(render_pdf(result))
    (out_dir / f"{slug}.json").write_text(
        json.dumps(result_to_dict(result), indent=2, ensure_ascii=False), encoding="utf-8")
    return {"name": name, "url": url, "score": result.score,
            "grade": result.grade, "slug": slug}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="audit_factory", description=__doc__)
    ap.add_argument("--name", help="Business name (single audit)")
    ap.add_argument("--url", help="Business website URL (single audit)")
    ap.add_argument("--csv", help="CSV with name,url columns (batch audit)")
    ap.add_argument("--out", default="audits", help="Output folder (default: audits/)")
    args = ap.parse_args(argv)

    out_dir = Path(args.out)
    jobs: list[tuple[str, str]] = []
    if args.csv:
        with open(args.csv, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("name") and row.get("url"):
                    jobs.append((row["name"].strip(), row["url"].strip()))
    elif args.name and args.url:
        jobs.append((args.name, args.url))
    else:
        ap.error("give --name and --url, or --csv")

    summaries = []
    for name, url in jobs:
        summary = run_one(name, url, out_dir)
        summaries.append(summary)
        print(f"{summary['score']:5.1f}/100  {summary['grade']:<24}  {name}  ->  {summary['slug']}.*")
    print(f"\n{len(summaries)} audit(s) written to {out_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

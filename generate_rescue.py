"""Generate an Estimate-Expiry Rescue campaign from a quotes CSV export.

Usage:
    python generate_rescue.py --quotes quotes.csv --business "Contractor Name"

Output: rescue/<slug>-rescue.md — staged drafts only, nothing is sent.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_factory.cli import slugify
from audit_factory.rescue import build_campaign, load_quotes, render_campaign


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quotes", required=True, help="CSV: id,customer,email,phone,total,created_at,status,language")
    ap.add_argument("--business", required=True)
    ap.add_argument("--out", default="rescue")
    args = ap.parse_args()

    items = build_campaign(load_quotes(Path(args.quotes)), business_name=args.business)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slugify(args.business)}-rescue.md"
    path.write_text(render_campaign(items, args.business, date.today().isoformat()),
                    encoding="utf-8")
    print(f"{len(items)} rescue drafts, ${sum(i.total for i in items):,.2f} open -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

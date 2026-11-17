"""Generate outreach packets + PRIORITY.md from the audits folder.

Usage:
    python generate_packets.py [--audits audits] [--out outreach]

Reads category + phone per prospect from
~/workspace/ai-receptionist/prospects.csv (matched by business name).
The OVIA self-audit is excluded — packets are for prospects only.
STAGED DRAFTS ONLY: this script sends nothing, ever.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_factory.outreach import generate_packets, render_priority

PROSPECTS_CSV = Path.home() / "workspace" / "ai-receptionist" / "prospects.csv"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audits", default="audits")
    ap.add_argument("--out", default="outreach")
    args = ap.parse_args()

    categories, phones = {}, {}
    if PROSPECTS_CSV.exists():
        with open(PROSPECTS_CSV, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                categories[row["name"]] = row.get("category", "")
                phones[row["name"]] = row.get("phone", "")

    audits_dir = Path(args.audits)
    # Exclude the OVIA self-audit from prospect packets.
    rows = generate_packets(audits_dir, Path(args.out), categories, phones,
                            exclude_names={"OVIA Inc"})
    (audits_dir / "PRIORITY.md").write_text(render_priority(rows), encoding="utf-8")
    for i, r in enumerate(rows, 1):
        flag = " TAINTED" if r["tainted"] else ""
        print(f"{i:2}. {r['opportunity']:>6}  {r['channel']:<5}  {r['name']}{flag}")
    print(f"\n{len(rows)} packets in {args.out}/ · ranking in {audits_dir}/PRIORITY.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

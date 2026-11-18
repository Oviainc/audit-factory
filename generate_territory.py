"""CLI: python generate_territory.py roster.csv audits_dir "Territoire" out_dir"""
import sys
from pathlib import Path

from audit_factory.territory import MYSTERY_CALL_SCRIPTS, load_territory, render_report

if __name__ == "__main__":
    roster, audits_dir, name, out_dir = sys.argv[1], Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
    out_dir.mkdir(parents=True, exist_ok=True)
    t = load_territory(Path(roster), audits_dir)
    (out_dir / "barometre.md").write_text(render_report(t, name), encoding="utf-8")
    (out_dir / "appels-mysteres.md").write_text(MYSTERY_CALL_SCRIPTS, encoding="utf-8")
    print(f"{len(t.audited)}/{len(t.rows)} audited, territory mean {t.mean()}, "
          f"cohort {len(t.cohort())} -> {out_dir}")

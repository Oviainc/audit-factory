"""CLI: python generate_pieces.py clients.csv campaign.md"""
import sys
from pathlib import Path

from audit_factory.pieces import load_items, render_campaign

if __name__ == "__main__":
    items = load_items(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(render_campaign(items), encoding="utf-8")
    print(f"{len(items)} open file(s) staged -> {sys.argv[2]}")

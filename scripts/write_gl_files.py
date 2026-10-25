"""Write the simulated account-level detail of the demo deal to two CSV files, one per company.

    backend/.venv/bin/python scripts/write_gl_files.py [<output folder>]   # default: data/

Writes kewaunee_gl.csv and nuaire_gl.csv with the columns company, line, section, account, name, amount, prior,
entries, last_posted, unit. Every row is SIMULATED: public filings stop at statement lines, so the accounts come
from backend/app/tools/gl_detail.py and sum exactly to each filed line of the fixture. The files have no comment
row, so any CSV reader takes them as is. They never replace kewaunee_lines.csv or nuaire_lines.csv.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.fixtures.kewaunee import build_lines  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402
from app.tools.gl_detail import gl_detail  # noqa: E402

COLUMNS = ["company", "line", "section", "account", "name", "amount", "prior", "entries", "last_posted", "unit"]
FILES = {"Kewaunee": "kewaunee_gl.csv", "Nu Aire": "nuaire_gl.csv"}


def main(out_dir: Path) -> None:
    lines = build_lines(MemoryStore())
    detail = gl_detail(lines)
    out_dir.mkdir(parents=True, exist_ok=True)
    for company, name in FILES.items():
        path = out_dir / name
        rows = 0
        with path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
            for line in lines:
                if line.company != company or line.is_total:
                    continue
                for a in detail[line.id]:
                    w.writerow([company, line.line, line.section, a.account, a.name, f"{a.amount:.0f}",
                                f"{a.prior:.0f}", a.entries, a.last_posted, line.unit])
                    rows += 1
        print(f"{path}: {rows} rows")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data")

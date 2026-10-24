"""Read and write the two input files: one CSV of statement lines per company.

    backend/.venv/bin/python scripts/load_lines.py export   # fixture -> data/kewaunee_lines.csv, data/nuaire_lines.csv
    backend/.venv/bin/python scripts/load_lines.py check    # reload both CSVs and compare them with the fixture

Columns: company, line, section, period, amount, unit, source_ref, is_total, note (note may be blank).
Row order is kept, because the Mapper and the console show lines in filing order.
`load_lines(path, deal_id, store)` is what the fixture and `POST /deals` call to turn a CSV into SourceLine rows.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.models import SourceLine  # noqa: E402
from app.db.memory import MemoryStore  # noqa: E402

COLUMNS = ["company", "line", "section", "period", "amount", "unit", "source_ref", "is_total", "note"]
FILES = {"Kewaunee": ROOT / "data" / "kewaunee_lines.csv", "Nu Aire": ROOT / "data" / "nuaire_lines.csv"}


def load_lines(path: Path, deal_id: str, store: MemoryStore) -> list[SourceLine]:
    """Turn one CSV into SourceLine rows. Raises ValueError with the row number on a bad row."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        missing = set(COLUMNS[:-1]) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
        lines = []
        for n, row in enumerate(reader, start=2):
            try:
                lines.append(SourceLine(
                    id=store.next_id("sl"), deal_id=deal_id, company=row["company"], line=row["line"],
                    section=row["section"], period=row["period"], amount=float(row["amount"]),
                    unit=row["unit"], source_ref=row["source_ref"],
                    is_total=row["is_total"].strip().lower() in ("true", "1", "yes"),
                    note=(row.get("note") or "").strip() or None))
            except Exception as exc:
                raise ValueError(f"{path.name} row {n}: {exc}") from exc
    return lines


def write_lines(path: Path, lines: list[SourceLine]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for sl in lines:
            row = sl.model_dump(include=set(COLUMNS))
            row["amount"] = str(int(sl.amount)) if sl.amount == int(sl.amount) else repr(sl.amount)
            row["note"] = sl.note or ""
            w.writerow(row)


def _fixture_lines() -> list[SourceLine]:
    from app.db.fixtures.kewaunee import build_lines
    return build_lines(MemoryStore())


def main(argv: list[str]) -> int:
    from app.db.fixtures.kewaunee import DEAL_ID
    cmd = argv[1] if len(argv) > 1 else "check"
    fixture = _fixture_lines()
    if cmd == "export":
        for company, path in FILES.items():
            rows = [sl for sl in fixture if sl.company == company]
            write_lines(path, rows)
            print(f"{path.relative_to(ROOT)}: {len(rows)} lines")
        return 0
    if cmd == "check":
        store = MemoryStore()
        loaded = [sl for path in FILES.values() for sl in load_lines(path, DEAL_ID, store)]
        strip = lambda sl: sl.model_dump(exclude={"id"})  # noqa: E731
        if [strip(s) for s in loaded] != [strip(s) for s in fixture]:
            for a, b in zip(loaded, fixture):
                if strip(a) != strip(b):
                    print(f"differs: {a.company} / {a.line}")
            print(f"FAIL: {len(loaded)} loaded, {len(fixture)} in the fixture")
            return 1
        print(f"OK: {len(loaded)} lines round-trip with the fixture")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

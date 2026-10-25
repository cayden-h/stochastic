// The demo deal's statements as the two upload CSVs (data/README.md format), written from the backend's own fixture
// (backend/app/db/fixtures/kewaunee.py), the same way backend/tests/test_api_brief.py builds them.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { BACKEND_DIR, PYTHON, ensureDir } from "./env";

const SCRIPT = `
import csv, sys
from app.db.fixtures.kewaunee import PLATFORM, TARGET, build_lines
from app.db.memory import MemoryStore
lines = build_lines(MemoryStore())
for company, out in ((PLATFORM, sys.argv[1]), (TARGET, sys.argv[2])):
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["line", "section", "period", "amount", "unit", "source_ref", "is_total", "covenant_tag"])
        for l in lines:
            if l.company == company:
                w.writerow([l.line, l.section, l.period, repr(l.amount), l.unit, l.source_ref, str(l.is_total).lower(), l.covenant_tag])
`;

/** Writes Kewaunee.csv and Nu-Aire.csv into dir (the console reads the company from the file name). */
export function writeDemoCsvs(dir: string): { platform: string; target: string } {
  ensureDir(dir);
  const platform = path.join(dir, "Kewaunee.csv");
  const target = path.join(dir, "Nu-Aire.csv");
  execFileSync(PYTHON, ["-c", SCRIPT, platform, target], { cwd: BACKEND_DIR, env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" } });
  if (!fs.statSync(platform).size || !fs.statSync(target).size) throw new Error("the demo CSVs came out empty");
  return { platform, target };
}

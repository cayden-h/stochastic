# Eric: data and facts

Branch: `eric/data`.
Folders: `data/`, `scripts/`, `evals/`.

The filings are already read and the figures are loaded in `backend/app/db/fixtures/kewaunee.py` (Cayden, 2026-10-24). Your job is to check them, make them yours, and build the proof around them.

1. Check every figure in the fixture against the filings. The sources are in the file header. Flag any difference to Cayden.
2. Export the platform file (Kewaunee) and the target file (Nu Aire) as CSVs in `data/` (git-ignored), with the fixture's columns: company, line, section, period, amount, unit, source_ref, is_total.
3. Write `scripts/load_lines.py` that reads those CSVs into `SourceLine` rows, so the fixture and `POST /deals` can use it.
4. Build the answer key from Note 2 of Ex 99.2 in `evals/answer_key.csv`: each Nu Aire line and its Kewaunee line. Mark it preliminary, shape only.
5. Score the Mapper: run `POST /deals/d_kequ_nuaire/run`, read `GET /deals/d_kequ_nuaire/mappings`, count agreements with the key, and write the score, the date, and the backend into `evals/README.md`.
6. Write the flag card facts: the "Financing liability" line, its three parts ($27,782K sale-leaseback, $20,563K PNC term loan and revolver, $22,540K seller notes), and the agreement's two exclusions, with quotes under 15 words and the exhibit and section.
7. Write the brief as prose for the Devpost and the slide.
8. Draft the Devpost text and the real-versus-simulated list by Saturday night. The honest-limits list is in `demo-script.md` section 6.

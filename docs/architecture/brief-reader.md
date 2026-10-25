# The Brief Reader: a fourth agent that reads the credit agreement

Last updated: 2026-10-24, evening.
Status: decided (D20).
Stage 1 is built in the gateway and the agents (2026-10-24); the routes are Tri's T4.
The gateway functions are in `gateway-and-api.md`.
Research: `research/brief-reader.md`.
Claims are tagged [verified] when a file or a filing shows them, and [inferred] when they are our judgment.

## 1. Why

Today a person writes the `Brief` by hand, and the only Brief is PNC's agreement with Kewaunee. [verified: `backend/app/db/fixtures/kewaunee.py`]
The code takes any Brief: `POST /deals` accepts one as JSON, and nothing in the math names PNC or 2.50. [verified: `backend/app/api/routes.py`, `POST /deals`]
So Stochastic supports any agreement with a single debt-to-EBITDA covenant, if a person writes the Brief.
It has been tested on one.
The Brief Reader closes that gap: it reads the agreement and drafts the Brief, code checks every quote, and the controller approves it.

## 2. Why a separate role, not part of the Mapper

- **Different timing.** An agreement is read once per loan, and the books are mapped on every deal. A PE platform makes several add-ons under one facility, so one approved Brief serves many deals. [inferred]
- **Writing the rule and applying it are separate.** The Mapper tags lines against the Brief's definition of debt. If it also wrote that definition, it could shape the rule to fit its own tags. The same reason keeps the Preparer from approving its own draft.
- **A gate between the two.** The Brief is approved and locked before mapping starts.
- **Separate tests and failures.** Note 2 scores the Mapper; hand-written Briefs score the Brief Reader. A bad read is caught without redoing the mapping. Each role can use a different model.
- A role is only a system prompt, a tool list, and typed input and output, so a fourth role costs about the same as a bigger Mapper. [verified: `backend/app/agents/roles.py`]

## 3. The rule: the model points, code decides

- The model fills the Brief's fields and gives at least one verbatim quote per field, with its section.
- The model never computes a number. The only allowed conversion is the unit: `$4,000,000` becomes `4000` (USD thousands).
- Code checks that every quote is in the agreement and that every number appears in its quote.
- Anything the schema cannot express becomes a flag for the controller, not a guess.
- The controller approves the Brief. No agent can.
- The math stays in `backend/app/tools/finance.py`, unchanged.

## 4. What the agreement gives and what it does not

The agreement gives the terms: the limit, the wording, the defined debt term, what it excludes, which add-backs and deductions are allowed, and their caps.
It mostly does not give the amounts.
In the Kewaunee Brief, pension 4,019 and stock compensation 1,018 come from the 10-K, the rent deduction 1,970 is inferred from the 10-K, and `closing_financing` comes from Ex 99.2 Note 4(h). [verified: `backend/app/db/fixtures/kewaunee.py`]
So the Brief Reader returns each adjustment with its name, its cap, and amount 0, marked `inferred` and flagged "amount comes from the books".
The controller enters the amount, with its source, before approving.
Taking amounts from the books automatically is a later step.

## 5. Flow

1. The controller creates a deal with the two statement CSVs and the agreement text (a `.txt` file) instead of a Brief JSON.
   Sending a Brief JSON still works and skips the reader, so the demo deal and the existing tests are unchanged.
2. Code indexes the text: the definitions (`"X" means` and `"X" shall mean`) and the section headings. [inferred: this regex index is how the research recommends handling defined terms]
3. The job runner opens a `draft_brief` work item and runs the Brief Reader.
   It gets the section index, the definitions index, and the sections that mention a leverage ratio.
   It can ask for more through two read-only gateway tools, `get_section(id)` and `get_definition(term)`.
   It never gets the whole agreement in one prompt: the relevant text is about 8K to 30K characters out of 240K to 690K. [verified: `research/brief-reader.md` section 1]
4. The gateway checks the draft (section 6). A failed check is refused and logged, the reader retries once with the reason, and then the scripted backend runs under the same checks, as the Mapper does today.
5. Low-confidence fields, missing fields, and missing amounts open `brief_field` flags. The runner stops on open flags, as it does today.
6. The controller answers the flags, enters the amounts, and approves the Brief. The Brief is then locked on the deal, with the agreement's hash and the approval in the log.
7. Only then does the Mapper start.
   The gateway refuses `store_mapping` and the `ebitda`, `covenant_debt`, and `limit_test` tools on a deal whose Brief is not approved.

Reuse: an approved Brief is keyed by the agreement's SHA-256.
A new deal with the same agreement text reuses it and skips the reader.
An amendment is a new text, so it is read again.

## 6. Gateway checks on a draft Brief

1. Permission `propose:draft_brief` for `agent:brief_reader` only. The item must be a `draft_brief` in state NEW.
2. **Every quote is in the text.** Both sides are normalized the same way: whitespace collapsed, curly quotes made straight, non-breaking spaces made spaces, and the ` | ` cell separators from `scripts/fetch_filings.py` removed. Then the quote must be an exact substring, at least four words long. No fuzzy match, because fuzzy matching can accept "4.50" for "4.25" or drop a "not". [verified: `research/brief-reader.md` section 4]
3. **Every number is in its quote.** The limit must appear as written (for example "2.50" or "2.50 to 1.00"). A cap must appear after the unit conversion. A value not in its quote is refused.
4. **Coverage.** Every required field has a verified quote or an open flag: `lender`, `limit`, `limit_section`, `limit_wording`, `debt_term`, `debt_definition`, each `debt_excludes` item, `ebitda_definition`, and each add-back and deduction name and cap.
5. **Consistency.** `limit_wording` is itself a quote, and `debt_term` appears in it. The finite-number check and `limit > 0`, now in `routes.py`, move into the gateway so they apply to every Brief.
6. **Amounts.** An adjustment amount that is not 0 needs a source outside the agreement, or `inferred=True` and a flag.
7. **Confidence.** A field below 0.6, or with no quote, opens a `brief_field` flag. Confidence is a hint. The real signals are structural: the quote passed, every defined term resolved, every number is in its quote. [inferred: `research/brief-reader.md` section 4]
8. **Missing is said, not blank.** A field not found is reported as "not found in sections X to Y", not left empty. This answers the "no related clause" failure that benchmarks report. [verified: ContractEval]
9. **Amendments.** If no amendment was supplied, the draft says "base agreement only" and the approval card shows it.

## 6a. The verifier: code checks every field after the read (D23)

Built 2026-10-25.
The draft checks above refuse a draft that breaks a rule.
The verifier runs right after a draft is accepted and reports field by field what it confirmed, so the check is visible, not only enforced. [verified: `backend/app/core/verifier.py`, `Gateway.verify_brief`]
It is code, not a model, and it speaks in the conversation as `system:verifier`.

For each required field, with the reader's best quote:
- **verbatim**: the quote is in the agreement word for word after the section 6 normalization, and at least four words long.
- **in_section**: the section the citation names exists, and its text contains the quote.
- **number**: the limit (2.50) is in its quote and in `limit_wording`, and the limit is quoted from `limit_section`; each cap in USD thousands is in its quote as written (4000 is "$4,000,000").
- **defined**: `debt_term` and EBITDA are defined terms of the agreement; `debt_definition` and each `debt_excludes` item are quoted from the debt term's own definition; each add-back and deduction is quoted from the EBITDA definition.
- `test_period_note` is checked when the reader quoted it.

For each adjustment amount:
1. If the deal carries `book_amounts` (adjustments with a source outside the agreement), the verifier fills each amount the reader left at 0 from the book amount of the same name, with its source, as a `brief:amend` row by `system:verifier`.
   Names match after case, a trailing "(capped)", and a leading "any" are ignored; nothing fuzzier.
2. An amount other than 0 passes only with a source outside the agreement; 0 passes as "not applied".

Each check is one `check` message and one `verify:brief_field` audit row (ALLOWED when it passed, DENIED when it failed).
The report, `BriefVerification`, is stored on the draft item and returned on `/case` as `brief_verification`: `checks` (field, value, section, quote, ok, reason, checks), `passed`, `failed`, `filled`, `scope_notes`, `escalated`, and `auto_approved`.

What happens next:
- The draft's questions open only after the verifier ran, so the controller is asked only what is left: amounts the books do not give, low-confidence fields, the reader's own questions, and every failed check.
- What the Brief cannot hold (the second covenant in Section 4.8(b), stage 2) is noted on the report and in a `verify:scope_note` row when every check passed, and not tested; with a failed check it is asked like the rest.
- The verifier never approves. With every check passed and nothing left to ask, the stage is `brief_ready`, the verifier hands the Brief to the controller ("Brief checked; ready for your approval"), and the stream sends one `notify` event of kind `brief_approval`.
  The controller approves in one click, with nothing to type, as in section 5 (maker-checker: the reader drafted it, the controller approves it).
  `POST /deals/{id}/brief/approve` then continues the run in the background at the run's pace, as an answer does.

On the demo deal the verifier writes 22 checks: 17 quoted fields and 5 amounts.
It fills pension 4,019, stock compensation 1,018, and rent 1,970 (inferred) from the books with their 10-K sources, and keeps transaction and integration costs at 0 (not applied).
The amounts are the ones in the hand-written fixture Brief, so the books' figures do not change: 0.76x on the agreement's reading.

### The demo deal's agreement text

The demo deal starts from `data/brief/kewaunee_ex101_extract.txt`, committed so the demo runs on any machine with the repo.
It holds verbatim extracts of Ex 10.1: the opening (the PNC line), Section 4.8 in full, and the EBITDA, Senior Funded Bank Debt, and Subordinated Debt definitions from Addendum I, 3,434 characters in all.
The rest of the 115K-character exhibit stays out of git (`data/raw/`, `scripts/fetch_filings.py`).
Its normalized SHA-256 is listed in `data/brief/kewaunee_quotes.json` as `demo_extract`, so the scripted reader returns the verbatim quotes on it, and every quote is in its section of the extract.
The pinned Sonnet 5.5 read of the full exhibit (`backend/recordings/brief_reader.json`) also passes all 25 of its verifier checks on the extract, but it asks five questions of its own (two of them substantive: the 2.00x prepayment test in Section 5.10(a) and the pro forma Nu Aire add-back), so the demo's read runs on the scripted reader. [verified: run on 2026-10-25]

## 7. Types and files

Proposed, following the patterns already in the code. [inferred]

- `models.py`:
  - The actor `BRIEF_READER = "agent:brief_reader"` and the item type `draft_brief`.
  - `AgreementText`: id, deal id, text, SHA-256, source.
  - `BriefCitation`: field path (for example `ebitda_addbacks[1].cap`), quote, section, confidence, note.
  - `BriefReaderInput` and `BriefReaderOutput` (the Brief, its citations, and its flags).
  - `Deal.brief` becomes optional, with `brief_status`: `approved`, `draft`, or `none`. The default stays `approved`, so the fixture deal is unchanged.
  - The agreement text is stored apart from `Deal`, because `/case` returns the whole deal.
- `roles.py`: `BRIEF_READER_ROLE`, with the two read-only tools.
- `gateway.py`: `store_brief`, `_check_brief`, a `brief_field` branch in the flag answer, Brief approval, and the gates in `store_mapping` and `run_tool`.
- `jobs.py`: the `draft_brief` step before mapping.
- `runner.py` and `backends/scripted.py`: the scripted reader. On the Kewaunee Ex 10.1 text (matched by hash) it returns the fixture Brief with real quotes, already in `devpost/flag-card.md` and `research/real-deal-candidates.md`. On any other text it uses regex for the limit and the definitions, with low confidence and flags.
- `settings.py`, `db/memory.py`, `db/postgres.py`: the new role and the `agreement` kind.
- `routes.py`: `POST /deals` takes `agreement_txt` or `brief`, exactly one. A route for the controller to enter amounts. `/case` adds the draft and its citations.
- `scripts/record_run.py` and `backend/recordings/brief_reader.json`.
- Frontend (Josie): a Brief card at the start of the deal, with each field, its quote, its flags, and Approve. The progress list adds the reader. `page.tsx` reads `deal.brief` at stage `new` and must handle a missing Brief.

## 8. Tests

New `backend/tests/test_brief_reader.py`, one test per rule:
- A quote not in the text is refused, with a DENIED row.
- A limit not in its quote (3.0 against a quote saying "2.50") is refused.
- A required field with no quote and no flag is refused.
- Low confidence opens a `brief_field` flag, and the runner stops.
- Mapping and the covenant tools are refused before the Brief is approved.
- The Brief Reader cannot approve its draft, and no agent can.
- Approval locks the Brief on the deal.
- Text in the agreement that addresses the model cannot create a citation that passes.
- A refused draft is retried with the reason, then made by the scripted backend.
- The scripted reader on the Kewaunee excerpt returns the fixture Brief.

The test agreement is a short synthetic text or stitched excerpts under 15 words, because the cached filings stay out of git.

## 9. The answer key for Briefs

`evals/brief_key/`: one hand-written Brief per agreement, field by field, with the section for each value.
- PNC and Kewaunee: the fixture Brief.
- Noble Roman's: a simple bank covenant, close to PNC, with a certificate worksheet in Annex A. [verified: `research/brief-reader.md` section 2.2]
- Mayville Engineering: a bank covenant with a real add-on behind it. Its 10-Qs report 1.36x before the Accu-Fab deal and 3.47x after it. [verified: `research/brief-reader.md` section 2.1]
  Reproducing 3.47x needs pro forma acquired EBITDA and the step-up, which are stage 2, so for now MEC scores the reader's fields only.

The score is per field: right, wrong, or flagged.
A flagged field is not wrong, but it costs the controller time, so we report both counts.

## 10. Stages

**Stage 1: the current schema.**
Everything above.
It works for agreements like PNC's and Noble Roman's: one leverage covenant, one limit, fixed-dollar caps.
On anything else the reader flags what the schema cannot hold, so a sponsor-style agreement gives a draft with many flags, not a wrong Brief.

**Stage 2: the covenant as data.**
The schema gaps, in the order of how often they appeared in four real agreements (`research/brief-reader.md` section 3):
1. Several covenants per Brief, each with its own ratio type: leverage, fixed charge coverage, interest coverage, minimum liquidity.
2. The test period as data: the last four quarters and the first test date.
3. The comparator as an enum: `max_inclusive` or `max_strict`.
4. Pro forma acquired EBITDA.
5. A limit schedule: step-downs, and a step-up after an acquisition.
6. Cap scope: per period, per acquisition, per unit, or for the life of the agreement.
7. The EBITDA base as a list of parts with signs, so "subtract interest income" is data, not code.
8. Percent-of-EBITDA caps shared by several add-backs, measured before or after them.
9. Cash netting, with an optional cap.
10. Rent-adjusted leverage (EBITDAR).

The formula stays a fixed menu: known parts (net income, interest expense, taxes, D&A, and so on), signs, and a few operations (sum, min, max, percent of, schedule).
The reader picks from the menu and code evaluates it.
The model never writes a free-form formula for code to run, because nobody could check it.
Each ratio type is one small tested function, and a covenant outside the menu is refused with a clear message.

## 11. What we say

"The agents adapt to how the books are labeled, and the Brief Reader adapts to how the contract is written.
It only points at quotes; code checks every quote and every number, and does all the math.
The controller approves the Brief before any deal is tested against it.
Anything the schema cannot express becomes a question, not a guess."

Until stage 1 is built and tested, say instead: "Today a person writes the Brief once per agreement, and the next agent we are building reads it from the contract."

## 12. Open questions

- When to build stage 1. The order of work in `TASKS.md` has a feature freeze on Saturday at 8pm, before judging. [verified: `TASKS.md`]
- Which model runs the reader. Sonnet 5.5 on Droid drafted a Brief that passed every check on the full Ex 10.1, on the runner's retry after one refused three-word quote. [verified: `backend/recordings/brief_reader.json`, 2026-10-25]
- Whether `DROID_TIMEOUT` is enough. A reader turn took 21 to 24 s on 10.8K characters of input, so the demo's 75 s is enough. [verified: the same run]
- The first live run (before two fixes) was refused twice: the limit's quote did not repeat the debt term, a rule stricter than check 3 that is now "the limit is quoted from limit_section", and it changed the text's capitals. [verified: `docs/tasks/cayden.md`, C3]
- Whether the reader keeps one session across agreements, as the other roles do, or starts fresh per agreement so its context does not grow. [inferred]
- `fetch_filings.py` needs `SEC_USER_AGENT` with a real email, which is not set in `.env` today. [verified: key names in `.env`]

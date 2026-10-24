# Design

## Status of the mockups

The Figma mockups were made for an earlier four-screen workflow.
The console now needs one working screen: the flag card, the combined table, the verdict line, and a log link.
Josie decides what to keep from the mockups.
The tokens and rules below still apply.

## Earlier four-screen design

The reviewer console has four screens and one look, called "Paper and ink".
The research behind it is in `ui-ux-research.md`.
The rule for every screen is: do not overbloat.

## Figma file

File: https://www.figma.com/design/KDbPUruO6f5oPLyzyLgUZh (Stochastic - Reviewer Console)

| Page | Frame | Link |
| --- | --- | --- |
| Screens | Plans (hero) | https://www.figma.com/design/KDbPUruO6f5oPLyzyLgUZh?node-id=3-10 |
| Screens | Desk | https://www.figma.com/design/KDbPUruO6f5oPLyzyLgUZh?node-id=5-39 |
| Screens | Log | https://www.figma.com/design/KDbPUruO6f5oPLyzyLgUZh?node-id=7-50 |
| Screens | Source (slide-over) | https://www.figma.com/design/KDbPUruO6f5oPLyzyLgUZh?node-id=7-216 |
| Foundations | Components | https://www.figma.com/design/KDbPUruO6f5oPLyzyLgUZh?node-id=2-2 |

The file holds one variable collection (`Tokens`), seven text styles, and five local components: Actor Chip, Button, Source Chip, Verdict, and Log Row.
All numbers in the mockups are illustrative placeholders. They are not engine output and not from real filings.

## Team board (Schocastic)

File: https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi (Schocastic).
Its `technologies` page (https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=135-2) holds one area per track: Tiger Data, Factory, Workflow, Tech stack, Research, and How it works.
Each item there is a card: a real screenshot (12 px corners, light stroke, soft shadow, dark backing at FIT), a DM Sans SemiBold 20 title, and a DM Sans Regular 15 description.
Add new evidence as cards in the same style, by cloning an existing card.

The Tiger Data area has five rows of cards.
Rows 1 to 3 hold the service, the schema, the hypertable, the hash chain, the fork, and the CLI and docs.
Rows 4 and 5 (added 2026-10-24 afternoon) show the SQL read side and the console:
- Row 4: `ledger_runs`, the BM25 search, and the `audit_activity` continuous aggregate, each captured in the Tiger Cloud SQL Editor.
- Row 5: the columnstore and refresh jobs, the Toolkit `run_stats`, and two captures of the running console (the TIGER CLOUD badge, and the FORK rows in the log).

All captures are from 2026-10-24, ledger 23.
The run statistics are a snapshot and change with each run.

## Screens

| Screen | One job | Primary action |
| --- | --- | --- |
| Desk | Show the one question that needs the reviewer now | Pick an answer on the open card (E1 to E4) |
| Plans (hero) | Compare plans and decide | Approve the recommended plan (E6) |
| Log | Prove what happened | None (read only). One toggle and one Verify button |
| Source | Show the page and the exact quote behind a fact or a denial | Close |

Source is a slide-over panel, not a page change.
Open it from any source chip.

## Tokens

Color roles (contrast checked in the research file):

| Token | Hex | Used for |
| --- | --- | --- |
| `paper` | `#F7F4EC` | Page background |
| `card` | `#FFFFFF` | Cards and the table |
| `ink` | `#1B1F24` | Body text, human chip, primary button |
| `muted` | `#5A6068` | Secondary text and ids |
| `rule` | `#8C8676` | Borders that must be seen |
| `hairline` | `#D9D3C4` | Row dividers |
| `agent` / `agent-tint` | `#274C77` / `#E3EAF3` | Agent chip |
| `code` | `#4A5560` | Gateway chip and mono text |
| `escalation` / `-tint` / `-bar` | `#8A5300` / `#FBEBC8` / `#C77700` | Cards that wait on the human |
| `denied` / `denied-tint` | `#B3261E` / `#FBE4E1` | Blocked plan and DENIED rows |
| `clear` / `clear-tint` | `#1E6B52` / `#E1F0EA` | Clear verdict and verified chain |

Type:
- Public Sans for UI text and numbers.
- Newsreader for verdict headlines and clause quotes.
- IBM Plex Mono for run ids, hashes, and clause numbers.

Sizes: verdict 40, heading 26, body 18, quote 20, label 14, mono 14. Nothing is smaller than 14.
Spacing scale: 4, 8, 12, 16, 24, 32, 48.
Radius: 4 for chips and buttons, 8 for cards.
State is always a color plus a word plus a shape: square (agent), circle (human), triangle (escalation), cross (denied), check (clear).

## Rules for adding to the UI

Apply this checklist before any screen or control ships:
- Can the screen's job be said in 10 words or fewer?
- Is there one primary button, and is it the only filled button?
- Are there 7 or fewer controls on first view?
- Does every number have a unit, and every claim a source link?
- Is there at most a second level of detail, never a third?

The explicit list of things that are not in the UI is in `ui-ux-research.md`, section "NOT in the UI".

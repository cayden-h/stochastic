# Design

## Current UI: Hi-fi v3 (start here)

The latest UI is the `Hi-fi - v3` page of the team file, Schocastic: https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=141-2 [verified: Cayden, 2026-10-24 evening]
Use it whenever you need to look back at the UI.
Every screen is 1440 by 900, with a 240 px sidebar (deal, Dashboard, Case, Review, Mapping, Agents, Log, the model, and the "Always learning from" counters for human answers, policies, and edits).

| Frame | Shows | Link |
| --- | --- | --- |
| V3-1 Dashboard | The cases, with stage, verdict, and updated time; the header has Upload and Run the demo (the console has no Begin there) | https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=141-3 |
| V3-2 Dashboard, upload | The upload modal | https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=141-119 |
| V3-3 Case | The flag card with the three readings, the verdict, the combined books, and Mapping, Review, and Log tiles. The console (2026-10-25) shows the flag card, the pipeline, and the verdict's four figure tiles only, with no verdict sentence and no conversation, and the combined books start hidden behind Show combined books | https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=144-35 |
| V3-4 Mapping | Target line, platform line, and confidence, filtered by All, Unsure, or By policy | https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=144-195 |
| V3-5 Log | The audit log | https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=144-379 |
| V3-6 Agents | The four agents in the live 3D Agent House (code layer 736:1282), each actor's latest line, and the agent timeline | https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=146-149 |
| V3-7.N Review | The Review workbook flow (section "Review flow (D19)") | https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=670-44 |

Josie's teal pass (2026-10-24 evening) changed the whole look, and the console follows it:
- One teal, #0F6674, for the brand, headings, body text, labels, figures, and the primary button.
  Surfaces and borders are pale teal, #DCEFF1.
  Empty values are #7A8A8C.
- Each agent has its own character and tint: the Mapper a teal star (#DCEFF1, #0F6674), the Preparer a blue flower (#E2E9F7, #2E55A3), the Reviewer a violet character (#ECE5F6, #6A4C9C), and the Brief Reader a plum character.
  The console has one source for the 2D characters: `ROLES` and `Avatar` in `frontend/src/components/ui.tsx`, from `frontend/public/v3/agent-*.png`, on every page (chips, the Agents rows and timeline, the Log, toasts, page titles, the Review companion).
- The page wash is the page's agent tint: teal for Dashboard, Mapping, Agents, and Review, blue for the Case, violet for the Log.
- The frames put the page's character in the brand row.
  The console keeps the Stochastic mark there (`brand.md`) and puts the page's character 24 px to the right of the page title instead.

The Agents page builds the frame's 3D layer from its Figma Make code (`frontend/src/components/agent-house/`).
The four characters are rigged and animated in Blender (`art/blender/README.md`), and the page plays the deal's conversation through them live: the speaker talks or asks, a note flies to the listener, and every agent settles where the record says it is.
`/agents?demo=1` runs the prototype's canned loop instead, for the pitch preview.
The frame titles the page "Agent"; the console keeps "Agents", the name in the sidebar.

Other pages in the same file:
- `Components` (https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=487-1681): the components behind v3.
- `Technologies Used` (https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=135-2): material for the pitch deck and the pitches, not the UI. See "Team board" below.
- `Hi-fi - v1`, `Hi-fi - v2`, `Wireframes + Ideation`, `Ideation`, and `3D Mockup`: earlier work, kept as history.

The D19 additions (editable cells, the reason bubble, the companion) are specified in `review-companion.md` and go on top of V3-3 and V3-4.
The logo, the name, and the launch splash are specified in `brand.md` (D21).
The splash shows only the circle and the name, centered, on a transparent background, until the whole app has loaded.
The tokens and rules below still apply.

## Earlier four-screen design (history)

Everything from here to "Team board" describes the first file, before Hi-fi v3.

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

File: https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi (Schocastic). It holds the current UI (Hi-fi v3, above) and the pitch material.
Its `Technologies Used` page is for the pitch deck and the pitches. It (https://www.figma.com/design/biVEkpW4u8S1TiaC9grcqi?node-id=135-2) holds one area per track: Tiger Data, Factory, Workflow, Tech stack, Research, and How it works.
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

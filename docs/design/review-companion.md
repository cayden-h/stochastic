# Review screen and companion

Status: proposed design, 2026-10-24 evening. Decision D19 in `docs/decisions.md`.
Owner: Josie (screens and Figma), Cayden (desktop shell, companion, edit endpoints), Tri (recompute and export).
Read `design/README.md` first: every color, font, and radius here is an existing token.
The base screens are Hi-fi v3 in Figma (`design/README.md` has the frame links).

Update, 2026-10-24 night: editing moved to its own page.
The Review page (`/review`, Figma section "Review flow (D19)", frames V3-7.1 to V3-7.8) holds every edit, the reason bubble, Your edits, Approve and Reject, and Download final files.
It is a full-window workbook with no sidebar: a title bar, a ribbon (Review, Combined, Mapping, Log), a formula bar, the sheet (A line, B platform, C target, D combined, E change), the verdict and Your edits strips, and the sheet tabs (Combined, Edits, Audit).
The Case (V3-3) is read-only: flags, verdict, read-only combined books, conversation, and pipeline; after the Reviewer's hand-off, "Review the books" is its primary action, and the header's Approve is a link, "Review and approve".
Mapping (V3-4) is read-only too; a remap is made from the line cell's menu on Review (V3-7.7a and 7.7b).
The companion is the Reviewer (`frontend/public/agents/reviewer-avatar.png`, 26 px) and lives on the Review page only.
Where the sections below say V3-3, V3-4, or the agent-blue dot, the Review page and the Reviewer now stand in their place.

## 1. What changes

Stochastic ships as a Mac desktop app.
The console is the same Next app, loaded inside an Electron window.
After the agents finish, the controller can edit the combined books directly in the app.
Each edit is answered once with a reason, and the agents learn from it.
When the controller approves, they download the final files with every edit and reason in them.

The companion is a small mark that floats near the cursor inside the app window.
It stays out of the way while the controller reads.
When they change a value, it moves to that cell and asks "Why did you change this?"
The behavior is modeled on Squeek's cursor ghost (https://github.com/syedkazmi14/squeek, `apps/desktop/src/renderer/halo.js`), restyled to our paper-and-ink look.

## 2. Flow

1. The agents run as today: map, flag, combine, test. The controller answers any flags.
2. The verdict line and the combined table appear. The table is now editable (section 4).
3. The controller edits a cell or a mapping. Code recomputes totals, EBITDA, and leverage at once, and the verdict line updates.
4. The companion moves to the edited cell and opens the reason bubble (section 5).
5. The controller picks a reason chip or types one. The edit is saved with its reason, and the agents learn from it (section 7).
6. The Reviewer's checks re-run on the edited books (code, under a second).
7. The controller approves. Approval is refused while any edit has no reason.
8. "Download final files" saves the workbook and the certificate, with every edit in them (section 8).

## 3. Screen layout

The screens are Hi-fi v3 (sidebar plus main area, 1440 by 900).
Changes per frame:

- **V3-3 Case:** the Combined books table becomes editable for amounts (section 4). The **Your edits** section sits directly under the verdict, shown once there is at least one edit. After approval, the verdict shows **Download final files**. The table opens on the section with a change, so the edit stays in view.
- **V3-4 Mapping:** the Platform line column becomes a dropdown, and that is where remaps happen. Add an **Edited** filter next to All, Unsure, and By policy.
- **Sidebar:** "Always learning from" gains a third counter, **Edits**, next to Human answers and Policies. It goes up when an edit is saved with a reason.
- **V3-3 tiles:** the Review tile says "Re-checking your edit" for the second it takes after each edit.

### Header copy while editing

- After the first edit: headline "Under the limit at 0.75x. 1 edit." Sub: "Code recomputed the books with your edit. Give a reason and approve."
- Edit with no reason: sub "1 edit needs a reason before you can approve."
- After approval: sub "Approved with your edits. The reasons are now policies for the next add-on."

## 4. The editable table

The combined table keeps its columns: Line, platform, target, Combined.
Edits are limited to what feeds the books, so the math stays in code and every number stays traceable.

| Cell | Editable | How |
| --- | --- | --- |
| Line (target lines) | On Review | The line cell opens a menu of the platform's lines (V3-7.7a). Picking one remaps the target line; it keeps its place on the sheet and shows where it goes now. |
| Platform amount | Yes | Click, type, Enter. |
| Target amount | Yes | Click, type, Enter. |
| Combined | No | Always computed. Shows the change from the agents' value. |
| Total rows | No | Always computed. |

### Cell states

- **Agent value (default):** as today.
- **Hover on an editable cell:** background `paper`, a 1px `hairline` inset border, cursor `text`. Line names show a small chevron.
- **Editing:** white input, 1px `ink` border, `radius-chip`, tabular numbers, right-aligned. Enter saves, Esc cancels, Tab moves right.
- **Edited, needs a reason:** background `escalation-tint`, a 3px left bar in `escalation-bar`. The agents' value sits struck through in `muted` mono 12px above the new value.
- **Edited, reason given:** background stays white, the left bar turns `clear`, a small check sits after the value. The struck-through agent value stays.
- **Combined cell of an edited row:** shows the new combined value and, under it in mono 12px, the change, for example `+500` in `clear` or `(500)` in `denied`.

Hovering an edited cell shows a tooltip: who edited it, when, the reason, and the policy id if one was made.

### Validation

- Numbers only, in USD thousands. Parentheses or a minus for negatives.
- A change of more than 50% of the agents' value asks for confirmation inside the bubble ("This is a large change. Is the amount right?").
- If the edit breaks the balance sheet tie-out, the "Ties out" chip turns to "Does not tie out" in `denied` and approval is refused, as today.

## 5. The reason bubble

The bubble opens when an edit is saved.
It is anchored to the edited cell, to its right if there is room and otherwise below it, with a 12px gap and an 8px tail pointing at the cell.

```
 ┌───────────────────────────────────────────────┐
 │  Why did you change this?                     │
 │  Nu Aire · Selling, general and admin.        │
 │  9,812 → 9,312   ·   leverage 0.76x → 0.75x   │
 │                                               │
 │  [ One-time acquisition cost, an allowed     ]│
 │  [ add-back                                  ]│
 │  [ Auditor's late adjustment                 ]│
 │  [ Correcting a typo in the source           ]│
 │                                               │
 │  Something else...                            │
 │  ┌─────────────────────────────────────────┐  │
 │  └─────────────────────────────────────────┘  │
 │                                               │
 │  ☑ Suggest this on the next add-on            │
 │                                 Later   Save  │
 └───────────────────────────────────────────────┘
```

The figures above are placeholders. The demo figures come from the filing (section 9).

- **Size:** 340px wide, auto height. `card` background, 1px `hairline` border, `radius-card`, shadow `0 8px 28px rgba(27,31,36,0.18)`.
- **Title:** "Why did you change this?" in the serif, 20px, `ink`.
- **Context:** the line and company in `muted` 14px, then the old and new values and the leverage change in mono 14px. Leverage moving toward the limit is `escalation`, and crossing it is `denied`.
- **Chips:** two or three reasons, one per row, full width, left-aligned text, 1px `rule` border, `radius-chip`, 16px. Hover: `paper` background. Selected: `agent-tint` background, `agent` border. One click selects; a second click on Save, or Enter, saves.
- **Something else:** a single-line text field. Typing in it clears the chip selection.
- **Remember toggle:** a checkbox, checked by default.
  - Remap: "Apply to every add-on on this platform".
  - Amount: "Suggest this on the next add-on". An amount is never applied silently, because it moves leverage.
- **Buttons:** "Later" (link style) closes the bubble and leaves the cell in the "needs a reason" state. "Save" (primary) is disabled until a chip is picked or text is typed.
- **Keys:** 1, 2, 3 pick a chip. Enter saves. Esc is the same as Later.
- **After Save:** the bubble shrinks into the companion over 200ms, and the companion shows a one-line note for 4 seconds: "Learned: allowed add-back, for the next add-on." The cell moves to the "reason given" state.

### Chips for the demo

The chips are hardcoded for the demo deal, and the pitch says so.
In the product, Claude suggests them from the line, the change, the filing notes, and earlier policies.

- Amount edit: "One-time acquisition cost, an allowed add-back", "Auditor's late adjustment", "Correcting a typo in the source".
- Remap: "Not a cash equivalent (over 90 days)", "Matches how the platform reports it", "Auditor's reclassification".

## 6. The companion

### Look

- The Reviewer's avatar (violet centre with a ring of circles), 26px, at 70% opacity while idle.
- While it is asking, it is 100% opacity and sits in a 40px `reviewer-tint` (#ECE5F6) ring that breathes over 1.6s.
- The learned note is a white pill with violet (`reviewer`, #6A4C9C) text beside it.

### Movement

- It follows the cursor at about 48px, below and to the right, so it never covers what the cursor points at.
- It moves on a damped spring, so it trails smoothly and never jumps. Squeek's values are a good start (spring toward the hover point, velocity damping about 0.8 per frame).
- When the cursor stops, it settles within about 300ms.
- It stays inside the app window. When the cursor leaves the window, it parks at the nearest edge and fades to 40%.
- While the reason bubble is open, it stops following and sits on the bubble's tail beside the cell.
- With reduced motion turned on, it does not follow. It sits at the bottom-right of the window and the bubble opens there.

### States

| State | When | Look |
| --- | --- | --- |
| Idle | Reading the screen | Follows the cursor, 70% opacity |
| Noticing | An edit was just saved | Glides to the cell in about 250ms |
| Asking | Bubble open | Parked at the bubble, pulse ring |
| Learned | After Save | One-line note beside it for 4s, then idle |
| Waiting | An edit has no reason | A small violet (`reviewer`) dot on the companion. Clicking it reopens the bubble for the oldest edit without a reason |

The companion is pointer-transparent (`pointer-events: none`), except for the waiting dot and the bubble.

## 7. Your edits section

On Review: a strip under the verdict strip, one 36px row per edit, with "Give a reason" (when the bubble is closed) and "Undo" on the right.

- Label: "Your edits (2)" in the uppercase 14px label style.
- One row per edit: a check or a waiting dot, the line, `old → new` in mono, the reason (truncated, full text on hover), and the policy id in mono if one was made.
- Clicking a row scrolls to the cell and flashes it.
- An "Undo" link on each row reverts the edit, and the agents' value comes back. A reverted edit retires its policy, the same way a reversed flag answer does (D18).

What the agents learn:

- **Remap** becomes a mapping policy, scoped to every add-on on this platform. On the next deal, the Mapper maps that line with the policy as its reason. This is the same `Policy` path as a flag answer (D12), so the existing "Learned" chip shows it.
- **Amount** becomes a logged adjustment with its reason. When the same reason comes up on a later deal, the Preparer proposes the adjustment as a flag for the controller to approve. It is never applied silently.

## 8. Download final files

After approval, the Review ribbon shows a primary button, "Download final files", which opens the macOS save dialog for a folder (`window.stochastic.saveFiles`); in a browser the two files download.
Before approval, with edits, it shows disabled with "after approval" beside it.
It writes two files:

- `Kewaunee + Nu Aire combined books.xlsx`
  - A **Combined** sheet with the final values. Each edited cell has a light amber fill and an Excel note: "Edited by controller, 2026-10-25 10:42. Was 9,812. Reason: One-time acquisition cost, an allowed add-back. Policy p_12."
  - An **Edits** sheet with one row per edit: line, company, agent value, final value, reason, who, when, and policy id.
  - An **Audit** sheet with the run ids behind every number.
- `Compliance certificate (draft).md`, from `GET /deals/{id}/certificate`, with the edited figures and a line listing each edit and its reason.

The button is not shown before approval, matching the certificate route's 409.

## 9. The demo beat (about 10 seconds)

1. The verdict reads under the limit. The controller clicks one target amount in the income statement and types a new value.
2. The verdict line ticks to the new leverage, and the Combined cell shows the change.
3. The companion glides to the cell, and the bubble asks "Why did you change this?"
4. They press 1 (the add-back chip). The note says "Learned: allowed add-back, for the next add-on."
5. Approve, then Download final files. Open the workbook for a second to show the amber cell and its note.

The edit should be a believable one-time cost, sourced from the Kewaunee or Nu Aire filing (Eric to find the line and the amount).
It does not need to cross the limit.
The point of the beat is that the edit is recomputed by code, explained, and remembered.

## 10. Backend contract (proposed)

These routes do not exist yet.

- `POST /deals/{id}/edits` with `{"kind": "amount", "line": "...", "company": "...", "value": 9312}` or `{"kind": "remap", "line": "...", "company": "...", "platform_line": "..."}`.
  Returns the edit (`id`, `old`, `new`, `needs_reason: true`), the recomputed `verdict` and `result`, and `reasons` (the chips, hardcoded for the demo deal).
- `POST /edits/{id}/reason` with `{"chip": 0}` or `{"text": "..."}` and `{"remember": true}`. Returns the edit with its `policy_id` if one was made.
- `DELETE /edits/{id}` reverts the edit and retires its policy.
- `GET /deals/{id}/case` gains `edits: Edit[]`.
- `GET /deals/{id}/export.xlsx` returns the workbook. It returns 409 before approval.

The gateway rules carry over: edits are recorded in the audit log as `human:controller`, recomputing goes through the same tools with new run ids, the Reviewer's checks re-run, and approval is refused while an edit has no reason.

## 11. Desktop shell

- On launch, before the main window, a splash window shows only the circle mark and the name "stochastic", centered on the screen, on a transparent background (`desktop/splash.html`, specified in `brand.md` section 4). It plays the draw once and stays until `GET /health` answers and the console has loaded and read the deal in the hidden main window, at least 2.1 seconds. Then the main window shows and the splash fades out over 200 ms. If startup fails, the error window opens and the splash closes.
- Electron loads the Next app built with `next build`, served locally, in one window. The minimum size is 1280 by 800.
- The title bar is hidden (`titleBarStyle: "hiddenInset"`), so the traffic lights (x 20, y 20) sit over the sidebar.
- In Electron, detected from the user agent, the sidebar's brand row moves down to a 52 px top offset so it clears the traffic lights.
- The brand row and each page header are drag regions (`-webkit-app-region: drag`); their buttons and links are `no-drag`.
- The companion is part of the page (a React layer), not a separate OS window. It only needs to be aware of the cursor inside the app, so no click-through overlay is needed.
- The save dialog for Download final files comes from Electron's `dialog.showSaveDialog`.

## 12. Figma checklist for Josie

- [ ] Editable table cells: default, hover, editing, needs a reason, reason given, combined with change.
- [ ] Line remap dropdown.
- [ ] Reason bubble: amount version, remap version, large-change warning, chip selected.
- [ ] Companion: idle, asking with pulse, learned note, waiting dot.
- [ ] Your edits section, and the row hover.
- [ ] Verdict line with Download final files.
- [ ] One full frame of the demo beat at 1440 by 900 for the pitch.

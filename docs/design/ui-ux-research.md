# Stochastic reviewer console: UI/UX research

Date: 2026-10-23.
Scope: the reviewer console only.
Tags used on claims: [verified: URL] means I opened the page.
[search summary: URL] means I saw only a search snippet or a secondary summary.
[inferred] means it is my own judgment.
[local: path] means I read a local project file.

## Summary

The console has one job: let a senior reviewer decide fast and be able to prove why.
The research agrees on a short list of habits.
Show the proposal with its reason and its source.
Ask only where the stakes are high.
Give the person a clear default, a clear effect for each answer, and a way back.
Keep the screen count low and hide detail behind one click.
For finance, use right-aligned tabular numbers, one number plus one word per verdict, and color only for state.
For the audit log, use a fixed set of verbs, name every actor, and show denied rows as first-class rows.
The demo has one hero screen: the plan table, where the first plan is red and a DENIED row quotes the blocking clause.
I recommend four screens (Desk, Plans, Log, Source) and a quiet "paper and ink" look with three typefaces, each with one role.
Most of the FigBuild lessons carry over, but the "speculative, not judged on feasibility" part does not.

## Design principles for Stochastic

1. Put the verdict first, then the proof.
   Each plan shows one word (Blocked, Needs consent, Clear) and one number before any detail.
   Why: the First Place FigBuild winner leads with a score, a color and a plain action. [local: showcase/projects/hackathon/neuralyfe.md]
   Why: Hick's law says decision time rises with the number of choices. [verified: https://lawsofux.com/hicks-law/]

2. Every number links to its run id and every fact links to its page and quote.
   Why: PAIR says to explain why, especially when stakes are high. [verified: https://pair.withgoogle.com/chapter/explainability-trust/]
   Why: Microsoft HAX guideline 11 is "Make clear why the system did what it did". [verified: https://www.microsoft.com/en-us/haxtoolkit/library/]
   Stochastic adds a code check on top of this, so the link is a proof and not only a claim. [local: docs/STOCHASTIC.md]

3. Ask only at the six escalation points, and ask one question at a time.
   Why: gating every action turns the human into a rubber stamp. [search summary: https://pickaxe.co/post/human-in-the-loop-ai-agents]
   Why: ask the human where evidence is thin, impact is high, or reversal is hard. [search summary: https://www.metacto.com/blogs/human-in-the-loop-ai-workflows-when-agents-should-wait-for-approval]
   The six points in STOCHASTIC.md already follow this rule. [local: docs/STOCHASTIC.md]

4. Every question shows the effect of each answer before the click.
   Why: HAX guideline 16 is "Convey the consequences of user actions". [verified: https://www.microsoft.com/en-us/haxtoolkit/library/]
   Why: Smashing says to show the plan in plain words and offer proceed, edit or take over. [verified: https://smashingmagazine.com/2026/02/designing-agentic-ai-practical-ux-patterns/]

5. Mark one default answer and say why.
   Never pre-submit it.
   Why: Hick's law says to highlight the recommended option. [verified: https://lawsofux.com/hicks-law/]
   Why: showing confidence only helps if it changes the decision, and a category needs a stated action. [verified: https://pair.withgoogle.com/chapter/explainability-trust/]
   [inferred] A pre-selected default that still needs one click keeps the human as the decider.

6. Make every answer reversible by adding a new linked item.
   Never delete.
   Why: Smashing lists "Action Audit and Undo" as a core pattern. [verified: https://smashingmagazine.com/2026/02/designing-agentic-ai-practical-ux-patterns/]
   Why: it matches gateway rule 5, where a reversal is a new item linked to the original. [local: docs/STOCHASTIC.md]

7. Show DENIED rows as loudly as approvals.
   Why: a denied action is the proof that the limit is enforced in code, and Hyphenate asks for "a clean record of its work". [local: docs/sponsors/hyphenate.md]
   Why: audit rows need a named actor, a specific action and a linked object. [verified: https://www.saasui.design/blog/saas-activity-feed-audit-log-ux-patterns]

8. Use color for state only, and always add a word or shape.
   Why: a finance table template keeps the minus sign so meaning survives without color. [search summary: https://www.quackit.com/html/templates/tables/financial_data_table.cfm]
   [inferred] Five state colors, never more.

9. Right-align numbers, use tabular digits, and put units in the column header.
   Why: right-aligned numbers let people compare magnitudes, and tabular digits stop the column from jittering. [verified: http://design.alberta.ca/examples/display-numbers-in-a-table-so-they-can-be-scanned-easily/]
   Why: `tabular-nums` makes digits the same width so columns line up. [verified: https://developer.mozilla.org/en-US/docs/Web/CSS/font-variant-numeric]

10. One primary action per screen, and at most two levels of depth.
    Why: NN/g says two levels is the usual limit for progressive disclosure. [verified: https://www.nngroup.com/articles/progressive-disclosure/]
    Why: Rams' last principle is "Minimal": focus on the essential and strip the rest. [verified: https://www.vitsoe.com/us/about/good-design]

## Anti-bloat rules and what we leave out

### Checklist (apply to every screen before it ships)

- Can I state the one job of this screen in one sentence of 10 words or fewer?
- Is there one primary button, and is it the only filled button?
- Are there 7 or fewer interactive controls on first view? [inferred threshold, a budget and not a research result]
- Does every element answer a question the reviewer asks at this moment?
  If not, move it behind one click or delete it.
- Is there a second level of detail at most?
  Never a third. [verified: https://www.nngroup.com/articles/progressive-disclosure/]
- Does every number have a unit, and every claim a source link?
- Is color the only carrier of meaning anywhere?
  If yes, add a word.
- Does the empty state say what the system is doing and what the human should do (often "nothing")?
- Is the text readable at 3 meters on a projector (see Visual direction for sizes)?
- Would a judge understand the screen in 5 seconds without hearing a word?
  If not, cut or rewrite.
- Does the copy pass a plain-writing check: short sentences, no hedges, no marketing words?
- Is any control there only because "dashboards have it"?
  Delete it.

Evidence for the "fewer controls" stance: Hick's law key takeaways say to cut options when speed matters and to break complex tasks into smaller steps. [verified: https://lawsofux.com/hicks-law/]
Counter-evidence to keep in mind: Hick's law also warns against oversimplifying to the point of vagueness. [verified: https://lawsofux.com/hicks-law/]
Bloomberg says its approach to a very dense product is to conceal complexity from the user. [search summary: https://www.bloomberg.com/company/stories/how-bloomberg-terminal-ux-designers-conceal-complexity]
So "minimal" here means "hidden until asked", not "missing".

### NOT in the UI (explicit list)

- No dashboard home with charts, KPI tiles or trend lines.
- No chat box or free-text prompt to the agents.
  The agents ask, the human picks.
- No agent-to-agent conversation view.
  Agents pass typed work items, so show the items, not a chat. [local: docs/STOCHASTIC.md]
- No autonomy dial, settings page, profile editor or theme switcher in the MVP. (Smashing recommends an autonomy dial, but the demo covers one deal and one profile, so it is not needed. [verified: https://smashingmagazine.com/2026/02/designing-agentic-ai-practical-ux-patterns/])
- No confidence percentages on clause readings.
  Use one word (Sure, Unsure) and the action it triggers. [verified: https://pair.withgoogle.com/chapter/explainability-trust/]
- No Monte Carlo fan charts, histograms or decorative charts.
  One number (chance of breach) plus a run id.
- No donut, gauge or 3D chart.
  Covenant headroom gets one thin bar with a limit tick, or just text. [inferred; no source found for covenant visuals]
- No more than 3 plans in the comparison table.
  Extra plans stay behind one link, "Show other plans".
- No login, accounts, mobile layout, many deals, search, saved views, export, date-range filters or pagination. (Matches the MVP cut list. [local: docs/diagrams/04-mvp-build-plan.html])
- No notification center, badges with counts on everything, toasts for routine events, or sounds.
- No modal confirmation on routine answers.
  Use undo instead.
  Confirmation is reserved for E6 approve.
- No separate memo editor.
  The memo is a short block on the Plans screen with an "Open full memo" link.
- No dark mode and no theme toggle (one theme to test and to film). [inferred]
- No eight-situation picker.
  The demo has one situation, shown as a label.

## Minimal screen set

Four screens.
The fifth slot is deliberately unused.
Evidence is a slide-over panel, so it is counted as the fourth screen but never a page change.

### 1. Desk

- One job: show the deal in one line and the one question that needs the reviewer now.
- Primary action: choose an answer on the open question card (E1, E2, E3).
- Shows: deal name, one-line stage ("Reading clauses. 2 agents working."), the single open escalation card, and below it a collapsed list "Answered (3)".
- Empty state: "Nothing needs you. Intake and Clause reader are working." with the last log line.
- Leaves out: any pipeline diagram, agent avatars grid, metrics.

### 2. Plans (hero screen)

- One job: compare plans and decide.
- Primary action: "Approve Plan B" (E6).
  Secondary: "Ask for changes".
  Tertiary text link: "Reject".
- Handles E4 (plan blocked) and E5 (plan flipped after an event) as a banner on top of the same table, not as new screens.
- Shows: the verdict line, the plan table (see anatomy), and directly under the red plan the DENIED row with the quoted clause and page link.
- Why this is the hero: it shows in one frame the three things the pitch claims, a limit enforced in code, a re-plan, and a human decision. [inferred]
- This matches the FigBuild pattern "the invisible made visible in one hero screen". [local: showcase/patterns/design-winners.md]

### 3. Log

- One job: prove what happened.
- Primary action: none.
  The page is read-only.
  One toggle: "Denied only".
  One button: "Verify chain".
- Shows: the audit log (see anatomy) and a chain status line.

### 4. Source (slide-over panel)

- One job: show the page and the exact quote behind a fact or a denial.
- Primary action: "Close".
  The quote is highlighted on the page image or text.
- Opens from any quote chip on Desk, Plans or Log.
  It never changes the route.
- Shows: document name, page number, the highlighted quote, and the validator result ("Quote found on page 41. Checked by code.").

### Demo flow across the screens (from the MVP script)

- 0:00 Plans: first plan red, DENIED row with the quote. [local: docs/diagrams/04-mvp-build-plan.html]
- 0:40 Desk (E2 facts card) then Source for one citation.
- 1:10 Desk (E3 card).
- 1:50 Plans (new plan, consent route priced, run ids).
- 2:25 Plans (approve), then Log (full log with the denied row, Verify chain).

## Escalation card anatomy

Order of fields, top to bottom.
Everything fits in one card with no scroll at 1280 by 720.

1. Header line: agent chip, point label, and age.
   Example: "Clause reader - E3 Unclear clause - just now".
2. The question: one sentence, under 20 words, ends with a question mark.
3. The quote: serif text, the deciding phrase highlighted, then a source chip "Credit agreement, p. 41, 7.6(e)".
   Click opens Source.
4. Answer buttons: two or three, equal width, each with a one-line effect under it.
   The agent's suggestion carries the tag "Agent suggests" and a short reason.
   Nothing is submitted until the click.
5. Escape link: "Not sure. Hold this item."
   This pauses that branch and logs it.
6. After the click: the card collapses to one line "Answered: Counts as debt. Logged 14:02:11. Undo" with a 30-second undo link.
   Undo adds a REVERSED item.
   It deletes nothing.

Copy style rules:
- Write the question so the answer is a choice, not an essay.
- Name the exact term in quotes, not a paraphrase.
- State the effect with a number and a unit when code has computed it, plus the run id in small mono.
- Use "Unsure" and "Sure", not "low confidence".
- No "I think", no "perhaps", no apologies.

The pattern follows PAIR (explain why, tie to action) [verified: https://pair.withgoogle.com/chapter/explainability-trust/], HAX 16 (convey consequences) [verified: https://www.microsoft.com/en-us/haxtoolkit/library/], and Smashing's escalation pathway (ask, present options, never guess) [verified: https://smashingmagazine.com/2026/02/designing-agentic-ai-practical-ux-patterns/].
The field order, the 30-second undo and the "Hold this item" link are [inferred].

### Example E3 (unclear clause)

```
Clause reader - E3 Unclear clause

Does the redeemable preferred count as debt?

"Disqualified Stock" means stock that the holder can make the company redeem
before 91 days after the maturity date.
Credit agreement, p. 41

The preferred can be redeemed in 2031. The loan matures 5 Nov 2026.
The text does not say if that counts.

[ Counts as debt ]                  [ Does not count ]
Net leverage 4.1x                   Net leverage 2.2x   (example number)
Covenant max 3.00x. Over by 1.1x.   Covenant max 3.00x. Clear.
Run 0xA41                           Run 0xA42

Agent suggests: Counts as debt. A wrong "no" costs more than a wrong "yes".
Not sure. Hold this item.
```

The 4.1x and 3.00x figures come from the project notes and use an inferred adjusted EBITDA. [local: docs/STOCHASTIC.md]
The "2.2x" and the run ids are placeholders for the layout only.
Replace them with real engine output.
The quote above is a paraphrase for layout.
Use the exact clause text in the real card.

### Example E4 (plan blocked)

```
Structuring - E4 Plan blocked

Plan A pays a cash dividend on the new preferred. The credit agreement blocks it.

"The Borrower shall not declare or pay any dividend in cash ..."
Credit agreement, 7.6(g), p. 52

Gateway: DENIED. Plan A not posted.

Choose a route:
[ Pay dividend in kind ]            [ Ask lender for consent ]
Allowed. Cost +0.4 pts, dilution    Needs lender vote. Price: 75 bp fee
+1.1 pts. Run 0xB17                 (example). Run 0xB18

Agent suggests: Ask lender for consent, because it keeps the cash dividend.
Not sure. Hold this item.
```

The quote is shortened and the numbers are placeholders for layout only.
The facts that a blocked cash dividend and a consent route exist come from the project notes. [local: docs/STOCHASTIC.md]

## Plan comparison table anatomy

Layout: plans as columns, measures as rows.
Maximum 3 plan columns.
Reason: a person scans down a row to compare one measure across plans. [inferred]

Column header for each plan: name, one verdict word, and one status icon.
Verdict words, fixed set: Blocked (red), Needs consent (amber), Clear (green).
The recommended plan has a thin ink outline and the tag "Agent suggests".

Rows, in this order.
Stop at 8 rows.
1. Verdict (word plus icon).
2. Raises ($M).
3. All-in cost (% per year).
4. Dilution (% of equity).
5. Net leverage at close (x) with the covenant max and a thin headroom bar, for example "4.1x of 3.00x max".
6. Chance of covenant breach within 5 years (%), with the run id in small mono under it.
7. Consent needed (None, or Lender vote and its price in bp).
8. Blocked by (clause section, linked to Source).

Number rules:
- Right-align all numbers.
  Use tabular lining digits.
  Same decimals down a row. [verified: http://design.alberta.ca/examples/display-numbers-in-a-table-so-they-can-be-scanned-easily/]
- Units sit in the row label, not in every cell.
  Show a delta against the recommended plan in a smaller muted line (for example "+0.4 pts"). [inferred]
- Negative numbers use a real minus sign, never color alone. [search summary: https://www.quackit.com/html/templates/tables/financial_data_table.cfm]
- Row height 44 px or more, header the same height as a row.
  Carbon uses a consistent row size with the header matching it. [verified: https://carbondesignsystem.com/components/data-table/usage/]
- A blocked plan keeps its numbers but the column gets the red tint and a DENIED strip under the header that quotes the clause.
- The headroom bar is optional.
  If the build is short on time, show the text "4.1x of 3.00x max. Over by 1.1x." and skip the bar. [inferred]
- One highlighted cell per column at most (the cell that decides).

GitHub's review model is a useful comparison: three outcomes (comment, approve, request changes) and an option to require approvals before merge. [verified: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews]
Stochastic maps to it as: Ask for changes, Approve, and Reject, with the proposer unable to approve its own item. [inferred mapping; rule 2 is from the project notes]

## Audit log anatomy

One row per event, newest at the bottom (a ledger reads downward). [inferred]
Fixed columns:

1. Time: 24-hour with seconds.
   The header says the time zone once.
2. Actor: chip with role color and a name (Intake, Clause reader, Structuring, Risk, Memo, Gateway, Reviewer).
3. Verb: from a fixed list: PROPOSED, ASKED, ANSWERED, APPROVED, POSTED, DENIED, REVERSED.
   A controlled verb list keeps the log scannable. [search summary: https://gravitee.io/corpus/gen-1361/monochrome-racing/audit-log-presentation.html]
4. Object: a link to the work item, plan or fact.
5. Detail: one line.
   For DENIED, the rule plus the quoted clause and a Source chip.
   For a changed value, "from X to Y". [verified: https://www.saasui.design/blog/saas-activity-feed-audit-log-ux-patterns]
6. Ids: run id and the first 6 characters of the row hash, in small mono, muted.

Rules:
- DENIED rows have a red tint and a left bar.
  Nothing else in the log has a fill.
  This makes them findable in one glance.
- Human actions have a heavier chip than agent actions, so a reader can follow the human trail.
- Above the table: one status line "Chain intact. 214 rows. Head a3f9c1." with a "Verify" button that recomputes the chain live and then shows "Verified 14:05:02".
  This is the whole tamper-evident UI.
- Filters: one toggle "Denied only" and one agent dropdown.
  Nothing else.
- Row click opens a slide-over with the full event JSON.
  This is the second and last level of depth.
- Absolute timestamps only.
  Audit logs need precise, timezone-clear times. [verified: https://www.saasui.design/blog/saas-activity-feed-audit-log-ux-patterns]

Leave out: search, export, date range, grouping, relative times, avatars, pagination.
I found no source on how to display hash-chain status.
The "chain intact plus Verify" pattern is [inferred].
It turns a hidden property into a visible action, and that fits the "invisible made visible" FigBuild pattern. [local: showcase/patterns/design-winners.md]

## Visual direction

Name: Paper and ink.
Idea: a deal-room ledger.
A calm paper background, black ink for people, blue for agents, mono for code, amber for "waiting on you", red for "denied".
[inferred] This reads as finance and as audit work, and it does not look like a default white SaaS dashboard or a neon "AI" look.
It sits at the opposite end from NeuraLyfe's dark holographic look, which fits a clinical emergency but not a lender-facing review. [local: showcase/projects/hackathon/neuralyfe.md]
One serif voice for documents echoes the FigBuild pattern of a serif plus a mono or clean sans. [local: showcase/patterns/design-winners.md]

### Color roles

Contrast ratios below are computed by me with the WCAG relative-luminance formula on 2026-10-23.
WCAG minimums: 4.5:1 for normal text, 3:1 for large text and UI components. [verified: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html]

| Role | Hex | Used for | Contrast |
| --- | --- | --- | --- |
| Paper | #F7F4EC | Page background | base |
| Card | #FFFFFF | Cards and the table | base |
| Ink | #1B1F24 | Body text, human chip fill | 15.07 on Paper |
| Muted | #5A6068 | Secondary text, ids | 5.78 on Paper, 6.35 on Card |
| Rule | #8C8676 | Borders that must be seen (inputs, buttons) | 3.30 on Paper, 3.63 on Card |
| Hairline | #D9D3C4 | Decorative row dividers only | decorative |
| Agent | #274C77 on #E3EAF3 | Agent chip, agent name | 8.01 on Paper, 7.26 on its tint |
| Code | #4A5560 | Gateway and mono text | 6.92 on Paper |
| Human | #F7F4EC on #1B1F24 | Reviewer chip and the approve button | 15.07 |
| Escalation | #8A5300 on #FBEBC8, bar #C77700 | Cards waiting on the human | 5.37 on tint, 3.46 bar on Card |
| Denied | #B3261E on #FBE4E1 | Blocked plan, DENIED rows | 5.95 on Paper, 5.38 on tint |
| Clear | #1E6B52 on #E1F0EA | Clear verdict, verified chain | 5.82 on Paper, 5.44 on tint |

Rules:
- A state is always a color plus a word plus an icon shape (square for agent, circle for human, triangle for escalation, cross for denied, check for clear).
  Never color alone.
- White text on Agent (#274C77) is 8.8:1, on Denied (#B3261E) 6.54:1, on Clear (#1E6B52) 6.4:1.
- Only one filled primary button per screen: Ink fill with Paper text.
- Stripe built its color system in a perceptual color space and set contrast rules per pair of steps.
  We do not need that scale, but the idea of testing every pair is worth copying. [verified: https://stripe.com/blog/accessible-color-systems]

### Type

All three are on Google Fonts and free.
- Public Sans: all UI text and numbers.
  It has the tabular-figure feature. [inferred from a byte-level check of the Google Fonts file on 2026-10-23, not a visual test. Test `font-variant-numeric: tabular-nums` in a browser before relying on it.]
- Newsreader: verdict headlines and every clause quote.
  Serif means "this is the document".
  It has the feature too by the same check.
- IBM Plex Mono: run ids, hashes, clause numbers.
  Mono digits are fixed width by design.
- I rejected Inter as the main face because it is the default SaaS look. [inferred]
  It does have tabular figures by the same check.
- IBM Plex Sans looked like the obvious pairing, but the Google Fonts file did not show a tabular feature in my check, so I did not choose it. [inferred, unverified]

Sizes (screen first, then the projector):
- Verdict headline: 40 px Newsreader, weight 500.
- Section label: 14 px Public Sans, weight 600, letter-spacing 0.04em, uppercase.
- Body and table: 18 px Public Sans.
- Quote: 20 px Newsreader.
- Ids and hashes: 14 px IBM Plex Mono.
  Never below 14 px anywhere. [inferred rule for demo legibility]

### Density, spacing, radius, motion

- Density: medium.
  Row height 44 px, 18 px text.
  Dense on data, loose around it.
- Spacing scale: 4, 8, 12, 16, 24, 32, 48 px.
  Nothing else.
- Layout: one centered column at 960 px max on Desk and Log.
  Plans uses 1120 px.
- Radius: 4 px for chips and inputs, 8 px for cards.
  No pill buttons.
- Borders: 1 px Rule color for controls.
  No shadows.
  A card is a white rectangle on paper.
- Motion: 150 ms ease-out for hover and expand.
  The key moment gets one 400 ms cross-fade of the plan column to the red tint, and the DENIED row slides in over 200 ms.
  Respect reduced-motion.
  No spinners; one slow pulsing dot for "agent working". [inferred]

## Lessons carried over from FigBuild

FigBuild was a speculative design contest judged on craft, story and fit, "not on feasibility". [local: showcase/sources/figbuild-2026-winners.md]
Cal Hacks is a build event with a live demo, and Hyphenate asks "is it real enough". [local: docs/sponsors/hyphenate.md]
The lessons below come from winners only.
There are no losers in the library. [local: showcase/patterns/design-winners.md]

Carry over:
- A distinct identity, not a default UI.
  Applies.
  Paper and ink does this. [local: showcase/patterns/design-winners.md]
- The invisible made visible in one hero screen.
  Applies.
  The Plans screen with the DENIED row is it. [local: showcase/patterns/design-winners.md]
- Plain verdicts and a number plus a word.
  Applies directly.
  NeuraLyfe pairs "95" with "Mandatory removal". [local: showcase/projects/hackathon/neuralyfe.md]
- Design for the user's real state.
  Somne designed for a half-asleep user.
  Our user is a busy senior reviewer, so the card answers in seconds. [local: showcase/projects/hackathon/somne.md]
- Show the quiet or empty screen.
  Somne showed its idle screen.
  Our Desk empty state does the same. [local: showcase/projects/hackathon/somne.md]
- Make the aha one comparison on one screen, and let the user commit before the reveal.
  Chrono does this with "guess first".
  The E3 card works the same way, because the reviewer answers before seeing the plan that depends on it. [inferred link] [local: showcase/projects/hackathon/chrono.md]
- A clickable prototype on a public URL.
  Applies, and a working product on a public URL is stronger.
  Dandi shipped a coded app. [local: showcase/projects/hackathon/dandi.md]
- Craft that survives close inspection.
  Applies.
  Judges visit tables and look closely. [inferred]
- Designed safeguards.
  Applies in a stronger form: the safeguards are real code (gateway rules, DENIED rows), and the UI shows them. [local: docs/STOCHASTIC.md]

Do not carry over:
- One metaphor for the whole interface (root network, jar, compass).
  Our product is the metaphor: a ledger.
  Do not add a second one. [inferred]
- Photoreal lifestyle mockups and AI-generated portraits.
  They prove a speculative product feels real.
  We have a real product, so show it running. [inferred]
- A named person's story as the opening.
  The Hyphenate script opens with the moment, and the pitch rules say to lead with the problem. [local: docs/STOCHASTIC.md]
- Warm, anti-clinical branding (Dandi).
  Our reviewer wants sober and exact. [inferred]
- Mood over journey.
  Somne needed a clear before-and-after story too, and ours is the moment-first script. [local: showcase/projects/hackathon/somne.md]
- Unsourced statistics.
  Dandi quoted numbers without sources.
  We mark every claim verified or inferred. [local: showcase/projects/hackathon/dandi.md]
- Any claim that polish is the score.
  Cal Hacks judges say they care about the idea, effort and thought process more than a polished product. [local: CalHacks/logistics.md]

## Hackathon demo UX (3-minute live demo and judged video)

- Open on the hero screen already in the red state.
  The script says the moment comes first. [local: docs/diagrams/04-mvp-build-plan.html]
- Keep the browser at 1920 by 1080 with 125 percent zoom for the video, so 18 px text reads as about 22 px. [inferred]
- One thing moves at a time.
  Highlight with a thin outline, not an animated arrow. [inferred]
- Prefill the data.
  No loading wait longer than 2 seconds on stage.
  Keep the recorded run ready, as the build plan says. [local: docs/diagrams/04-mvp-build-plan.html]
- Never show a screen with more than one idea.
  If the judge cannot say what the screen is for in 5 seconds, cut.
- Keep a visible "reconstruction from public filings" label in the footer of Plans, because Hyphenate wants proof of what is real and what is simulated. [local: docs/sponsors/hyphenate.md]

## Judging fit

Cal Hacks 13.0 factors: impact, quality, technical complexity, creativity. [local: CalHacks/logistics.md]
That list comes from the organizers' Hacker Guide as noted in the local file.
I did not find an official public rubric online. [search summary: web search found only older Cal Hacks rubrics, for example https://www.hackerearth.com/challenges/hackathon/cal-hacks-50/rules]
Map to the UI:
- Impact: the verdict-first Plans screen shows the cost of a wrong decision in one frame. [inferred]
- Quality: the 4-screen set, the tokens and the contrast checks.
  Small and finished beats wide and rough.
- Technical complexity: the DENIED row, run ids, quote validator result and chain verify are all visible proof of real engineering. [local: docs/STOCHASTIC.md]
- Creativity: the paper-and-ink identity and the "Verify chain" action.
  Not a chat box.

Figma track: the local notes say Figma posted a track "coming" with no details, and the current plan is to skip it. [local: CalHacks/ideation/tracks.md]
Do not design for a Figma prize.
If it is published and fits, a Figma file of the tokens above is cheap. [inferred]

Hyphenate's four questions and the UI answer to each: [local: docs/sponsors/hyphenate.md]
- Real enough?
  A real clause quote with a page link, run ids on every number, and the real-versus-simulated label.
- Would you hire it?
  The agent asks at the right time, shows its record, and cannot approve its own item.
  The Desk and Log show this.
- Something new?
  The DENIED row and the priced consent route on one screen.
- The moment?
  The plan turns red, the log shows DENIED with the clause, the agent re-plans, the human approves.

## Sources

Opened and read (verified):
- https://pair.withgoogle.com/chapter/explainability-trust/ (Google PAIR, explainability and trust)
- https://pair.withgoogle.com/chapter/feedback-controls/ (Google PAIR, feedback and controls; it does not use the words override or undo)
- https://www.microsoft.com/en-us/haxtoolkit/library/ (Microsoft HAX, list of the 18 guideline titles only)
- https://www.nngroup.com/articles/progressive-disclosure/ (NN/g)
- https://www.nngroup.com/articles/ai-paradigm/ (NN/g, intent-based outcome specification; read but not used above)
- https://lawsofux.com/hicks-law/ (Hick's law summary)
- https://www.vitsoe.com/us/about/good-design (Dieter Rams, ten principles)
- https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews (GitHub)
- https://stripe.com/blog/accessible-color-systems (Stripe)
- https://carbondesignsystem.com/components/data-table/usage/ (IBM Carbon, data table)
- https://developer.mozilla.org/en-US/docs/Web/CSS/font-variant-numeric (MDN; I read the first 100,000 characters)
- https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html (WCAG)
- http://design.alberta.ca/examples/display-numbers-in-a-table-so-they-can-be-scanned-easily/ (Alberta design system)
- https://smashingmagazine.com/2026/02/designing-agentic-ai-practical-ux-patterns/ (Smashing, agentic UX patterns; fetch returned a summary table of the six patterns)
- https://www.saasui.design/blog/saas-activity-feed-audit-log-ux-patterns (audit log and activity feed patterns; a vendor-style blog)
- Local files read in full: docs/STOCHASTIC.md, showcase/patterns/design-winners.md, showcase/sources/figbuild-2026-winners.md, showcase/projects/hackathon/neuralyfe.md, chrono.md, somne.md, dandi.md, docs/diagrams/04-mvp-build-plan.html (text), CalHacks/logistics.md (judging lines), CalHacks/ideation/tracks.md (Figma lines), docs/sponsors/hyphenate.md (the four-question lines).

Search summaries only (not opened):
- https://www.bloomberg.com/company/stories/how-bloomberg-terminal-ux-designers-conceal-complexity (my fetch returned HTTP 403)
- https://pickaxe.co/post/human-in-the-loop-ai-agents
- https://www.metacto.com/blogs/human-in-the-loop-ai-workflows-when-agents-should-wait-for-approval
- https://gravitee.io/corpus/gen-1361/monochrome-racing/audit-log-presentation.html
- https://www.quackit.com/html/templates/tables/financial_data_table.cfm
- https://www.hackerearth.com/challenges/hackathon/cal-hacks-50/rules (older Cal Hacks rubric, not 13.0)

Computed by me:
- Contrast ratios (WCAG formula, Python, 2026-10-23).
- Font feature check: I downloaded the Google Fonts TTF files and searched the bytes for the `tnum` tag.
  This is a crude check.

## Limits

- I did not open Nielsen Norman Group pages on AI agents or alert fatigue.
  Search returned none, so the alert-fatigue and rubber-stamp points rest on secondary and healthcare sources.
- The HAX page gave only the 18 guideline titles, not the full guideline text.
  I used titles 11 and 16 only.
- I did not read Linear, Atlassian or Stripe Dashboard UI guidance.
  Stripe is cited only for its color-system post.
- The Bloomberg page returned 403.
  Its claims come from a search summary and are company marketing, not an independent usability study.
- I found no source on covenant headroom visuals, hash-chain display, or delta-column conventions.
  Those parts are [inferred].
- The Smashing numbers (for example reversion thresholds) came from a third-party summary, so I did not use them.
- I found no official Cal Hacks 13.0 rubric.
  The four factors come from a local file that cites the Hacker Guide.
  Judges' weights are unknown.
- Figma track details are not published, so I made no plan for it.
- No user test and no test with a real reviewer.
  The card and table layouts are untested design proposals.
- The font tabular check is by bytes, not by rendering.
  Test in the browser.
  The contrast numbers cover the listed pairs only, not every combination in the build.
- All example numbers (2.2x, 75 bp, +0.4 pts, run ids) are layout placeholders, not engine output.
- Figma, FigBuild and Hyphenate lessons come from winners only, so they carry survivorship bias. [local: showcase/patterns/design-winners.md]

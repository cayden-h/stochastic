# Stochastic - Hyphenate workshop findings

Source: the "Beyond Agentic Harnesses" pre-event workshop on 2026-10-21, a transcript pasted by Cayden and the slide PDF "Beyond Agentic Harnesses - Hyphenate CalHacks Workshop" (20 slides, also pinned in `#cohost-hyphenate`).
Quotes and slide contents are verified.
Everything under "Where Stochastic stands" is agent judgment (inferred).

## What the workshop says matters

1. The track is "pick a company, pick a few roles, make it autonomous". A few roles done deep beats ten shallow ones.
2. Judging has four questions: is it real enough, would you hire it, did we see something new, did it have a wow moment.
   The speaker called "would you hire it" make-or-break.
3. The core idea is "records hold the truth, a system of work holds the work".
   - Systems of record are the bank, ledger, contracts, CRM, and inbox. You integrate with them, you do not replace them.
   - The system of work holds work items, decisions and reasons, questions and approvals, learned policies, and the log. "This is what you build."
4. A good system of work does three things: learns the job from the company's history, improves with every correction, and proves every step months later.
5. The blueprint, in four parts:
   - Environment: sync the records into one shape (raw, standardized, golden), change-only with a cursor, stable ids, every golden row traces to its raw row.
   - Agents and humans as one team: map actors (sync job, AI agent, accountant, controller, gateway), actions (create, propose, ask and answer, approve, post), and resources (bank line, invoice, work item, policy, journal).
   - The harness: tools are CRUD on the work. States are NEW, PROPOSED, NEEDS_INFO, APPROVED, POSTED. Only the gateway posts to the record. A reversal is a new transition, never a delete.
   - Traceability: every transition is logged as a diff, append-only, in the same commit as the change, and denied attempts are logged too.
6. Separation of duties is enforced in code: the proposer of an item cannot approve it, and no role can "post" except the gateway.
7. Self-learning example: the agent queries 12 months of history, finds that short wires of $50 or less were booked to bank fees 214 times, and proposes a policy with its evidence and an approver.
8. Self-improving example: a human corrects a match, the agent searches precedents, spots that the memo lists several invoice numbers, proposes a general policy, and sends it for controller approval.
9. Weak submissions: a chatbot over a spreadsheet, a one-shot extractor, ten shallow workflows, clean happy-path data, an admin key with "the prompt tells it not to", and memory that ends with the context window.
10. Strong submissions: a real company with a messy corner and an answer key, a few roles named in one line, asks at the right moment and handles a no, limits enforced in code with a record of every call, and a moment on stage with a score to back it.
11. Precision over recall: whatever the agent automates should be correct, and it should escalate when unsure rather than guess.
12. Rules from the Q&A:
    - It must be a corporate finance team. Personal finance does not count.
    - Government and public-sector finance teams are in scope.
    - Simulated data is encouraged, and the track doc lists public datasets.
    - Closed-period errors are fixed by reverse and repost, linked to the original event, never deleted.
    - They had no answer for a business with almost no history to learn from, and asked the questioner to follow up in Slack.
13. Top 5 teams get an expedited interview for every member, and with many submissions the top 10 to 15 have a reasonable chance.
14. In-person workshop and office hours: Friday Oct 23, 7pm, Theater, with Hyphenate's founding engineers.

## Where Stochastic stands (inferred)

Strong points:
- The covenant-blocker moment is a real "caught what others missed, then recovered" beat.
- The proposer and approver split matches their separation-of-duties example.
- Special-situations financing is an unusual corner, which helps "did we see something new".

Gaps against what they said they want:
1. No learning source. Their examples learn from a year of company history. We have no table of past deals, lender terms, or approver rejections for the agent to learn policies from.
2. No self-improvement loop. Today the human only approves. They want a rejection to become a general policy with evidence, backtested, and approved by a controller.
3. The covenant block is prose, not a denied transition. To match their "limits enforced in code" test, the blocked plan should be a logged denied action that cites the clause as evidence.
4. No time dimension. The brief says what happened in March should change what the system does in June, and a one-shot structuring ends at "send to human".
5. No answer key. We need planted covenant traps in a realistic credit agreement and a catch-rate score.
6. Unclear seat. They frame the work as a function a CFO would delegate (billing, cash, close), and a deal desk that runs a few times a year is advisory work.
7. Monte Carlo is not in their blueprint. Keep it as a seeded, reproducible tool, and put the demo time on the loop.

## The seat choice (revised 2026-10-23)

Revised the same day: Cayden asked why the system must track a company over quarters, and the answer is that it does not.
Option A below is dropped.
The plan is a deal in motion: one special-situations deal worked from start to human approval, with events during the deal (a lender changes terms, a rate moves, the reviewer rejects a plan, a late document arrives).
The options stay below as history.

- A. Standing capital-markets seat: agents keep running after the deal closes, watch covenant headroom each simulated quarter, re-plan when a revenue miss threatens a covenant, and learn policies from approver decisions. Recommended, because it supplies the time dimension, the learning loop, and a hireable function.
- B. One-shot deal desk: cheaper to build but nearest to their "one-shot extractor" weak list.

## Sponsor stacking from Slack (see `sponsors/slack-channel-notes.md`)

- CRS: a credit API with a sandbox and MCP, but it is consumer credit data, so the honest use for corporate financing is thin. Possible only as a borrower or guarantor credit check in the intake step. Do not force it.
- Microsoft: names finance as an example domain, and its criteria (customer understanding, measurable usefulness, responsible design, path to production) overlap with Hyphenate's "would you hire it".
  Confirm at the booth whether Microsoft products are required.
- Coinbase: the x402 and trading tracks do not fit corporate structuring. Skip.
- Bright Data forbids mocked data, which conflicts with the seeded company the Hyphenate brief wants. Skip.

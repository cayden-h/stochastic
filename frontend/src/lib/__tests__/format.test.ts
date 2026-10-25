// Run with `npm run test:lib` (node --test; Node strips the types).
import assert from "node:assert/strict";
import { test } from "node:test";
import { canStart, isUnsure, mappingCounts, openQuestionLines, runInFlight } from "../format.ts";

test("a run is in flight only when the gateway says a job runs, not because of the stage", () => {
  // After a restart with STORE=postgres the deal was loaded at `mapping` with no job; the stage alone kept Run off.
  assert.equal(runInFlight(false, { running: false }), false);
  assert.equal(runInFlight(false, { running: true }), true);
  assert.equal(runInFlight(true, { running: false }), true, "the click before the gateway answers");
  assert.equal(runInFlight(false, null), false);
  assert.equal(runInFlight(false, {}), false, "an older gateway without the field");
});

test("Run is offered on a new deal and after a failed or interrupted run", () => {
  assert.equal(canStart("new"), true);
  assert.equal(canStart("run_failed"), true);
  assert.equal(canStart("mapping"), false);
});

test("unsure means in an open question; totals, accepted, approved and policy lines are not", () => {
  const lines = [
    { id: "sl_1", is_total: false }, // in the open mapping question
    { id: "sl_2", is_total: false }, // low confidence, accepted without a question
    { id: "sl_3", is_total: true }, // a total: no platform line, confidence 0
    { id: "sl_4", is_total: false }, // placed by a policy
    { id: "sl_5", is_total: false }, // in an answered question
  ];
  const mappings = lines.map((l) => ({ target_line_id: l.id }));
  const flags = [
    { id: "wi_002", state: "NEEDS_INFO" as const, payload: { kind: "mapping", line_ids: ["sl_1"] } },
    { id: "wi_003", state: "POSTED" as const, payload: { kind: "mapping", line_ids: ["sl_5"] } },
    { id: "wi_004", state: "NEEDS_INFO" as const, payload: { kind: "covenant_tag", line_ids: ["sl_9"] } },
  ];
  const asking = openQuestionLines(flags);
  assert.deepEqual([...asking].sort(), ["sl_1", "sl_9"]);
  assert.equal(isUnsure({ target_line_id: "sl_1" }, asking), true);
  assert.equal(isUnsure({ target_line_id: "sl_5" }, asking), false, "an answered question is not open");
  assert.deepEqual(mappingCounts(mappings, lines, asking), { placed: 4, sure: 3, unsure: 1, totals: 1 });
  // The case's open_flags list wins over the item state when given (the Brief's own questions are left out there).
  assert.deepEqual(mappingCounts(mappings, lines, openQuestionLines(flags, ["wi_004"])), { placed: 4, sure: 4, unsure: 0, totals: 1 });
  // After the answers, nothing waits: the second run asks nothing.
  assert.deepEqual(mappingCounts(mappings, lines, openQuestionLines([])), { placed: 4, sure: 4, unsure: 0, totals: 1 });
});

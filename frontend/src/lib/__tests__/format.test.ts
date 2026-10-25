// Run with `npm run test:lib` (node --test; Node strips the types).
import assert from "node:assert/strict";
import { test } from "node:test";
import { canStart, runInFlight } from "../format.ts";

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

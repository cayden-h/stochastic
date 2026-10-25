// Run with `npm run test:lib` (node --test; Node strips the types).
import assert from "node:assert/strict";
import { test } from "node:test";
import { toSummary } from "../api.ts";

test("a GET /deals row in the summary shape reads as a case row", () => {
  const row = toSummary({
    deal_id: "d_harbor", platform: "Harbor Labs", target: "Clearwater", stage: "posted",
    verdict: { leverage: 0.76, limit: 2.5, verdict: "ok" }, updated_at: "2026-10-25T04:44:09Z",
    data_source: "sample", note: "Made-up figures",
  });
  assert.deepEqual(row, {
    id: "d_harbor", name: "Harbor Labs acquires Clearwater", platform: "Harbor Labs", target: "Clearwater", stage: "posted",
    verdict: { leverage: 0.76, limit: 2.5, verdict: "ok" }, updated_at: "2026-10-25T04:44:09Z", data_source: "sample", note: "Made-up figures",
  });
});

test("the older full Deal row still reads, with no verdict, time, or source", () => {
  const row = toSummary({ id: "d_kequ_nuaire", name: "Kewaunee Scientific acquires Nu Aire", platform: "Kewaunee", target: "Nu Aire", stage: "new", brief: null });
  assert.equal(row.id, "d_kequ_nuaire");
  assert.equal(row.name, "Kewaunee Scientific acquires Nu Aire");
  assert.equal(row.verdict, null);
  assert.equal(row.updated_at, null);
  assert.equal(row.data_source, null);
});

test("an unknown data source is not shown as sample or filings", () => {
  assert.equal(toSummary({ deal_id: "d_x", platform: "A", target: "B", stage: "new", data_source: "other" as never }).data_source, null);
});

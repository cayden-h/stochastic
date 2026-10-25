// The Review page's "Check the math" panel: the ribbon's button opens a slide-over that walks the five steps behind
// the verdict (EBITDA, debt, leverage, the limit, the tie-out), each with its checks and the tool run that produced it.
// On the demo deal every check passes. The test starts from a fresh backend and runs the deal to the Reviewer's
// hand-off (no pacing).
import { expect, open, test } from "./support/fixtures";
import { toReview } from "./support/flows";

const STEPS = ["ebitda", "debt", "leverage", "limit", "tie_out"];

test.beforeEach(async ({ page }) => {
  await open(page, "/");
  await toReview(page);
});

test("Check the math: five steps, every check passes, each with its tool run; Close the math closes it", async ({ page, shot }) => {
  const button = page.getByTestId("check-math");
  await expect(button).toBeVisible();
  await expect(button).toHaveText("Check the math");
  await button.click();

  const panel = page.getByRole("dialog", { name: "Check the math" });
  await expect(panel).toBeVisible();

  // The summary: "N of N checks pass", all of them on the demo deal.
  const summary = panel.getByTestId("math-summary");
  await expect(summary).toHaveText(/^\s*\d+ of \d+ checks pass\s*$/);
  const [, passed, total] = /(\d+) of (\d+)/.exec((await summary.textContent()) ?? "")!.map(Number);
  expect(total).toBeGreaterThan(0);
  expect(passed).toBe(total);

  // The five steps, in order, each with its tool run id.
  const steps = panel.locator("[data-step]");
  await expect(steps).toHaveCount(STEPS.length);
  expect(await steps.evaluateAll((els) => els.map((el) => el.getAttribute("data-step")))).toEqual(STEPS);
  for (const step of STEPS) {
    await expect(panel.locator(`[data-step="${step}"]`)).toContainText(/run_\d+/);
  }
  await expect(panel.locator('[data-step="leverage"]')).toContainText("0.76×");

  // Every check row passes.
  await expect(panel.locator('[data-check-ok="true"]').first()).toBeVisible();
  await expect(panel.locator('[data-check-ok="false"]')).toHaveCount(0);
  await shot("math-open");

  // Close the math: the slide-over goes, the Review page stays.
  await panel.getByRole("button", { name: "Close the math" }).click();
  await expect(panel).toHaveCount(0);
  await expect(button).toBeVisible();
  await shot("math-closed");
});

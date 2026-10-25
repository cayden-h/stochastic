// The Factory beat (docs/demo-script.md section 2): Upload the demo deal's two statement CSVs and its Brief as JSON,
// then Begin. Begin resets with memory cleared, creates the deal, and runs it at pace "factory" (about 30 s of agent
// time): the recorded Claude Haiku 5.5 run replays on the uploaded lines, asks its questions, and hands off.
import fs from "node:fs";
import path from "node:path";
import { expect, open, readCase, test } from "./support/fixtures";
import { writeDemoCsvs } from "./support/demo-files";
import { DEMO_DEAL, answerSuggested, expectCleanCase, handoff, watchRunBody } from "./support/flows";

test("the Factory beat: Upload, Begin at pace factory, the recorded Haiku run asks, answer, hand-off", async ({ page, backend, shot }, testInfo) => {
  test.setTimeout(150_000);
  const csv = writeDemoCsvs(testInfo.outputDir);
  const brief = path.join(testInfo.outputDir, "brief.json");
  fs.writeFileSync(brief, JSON.stringify((await readCase(backend, DEMO_DEAL)).deal.brief));

  await open(page, "/");
  await expect(page.getByRole("button", { name: "Begin", exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Upload", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "New deal" });
  await dialog.locator("input[type=file][multiple]").setInputFiles([csv.platform, csv.target, brief]);
  await expect(dialog.getByRole("button", { name: /^brief\.json Limit 2\.50×$/ })).toBeVisible();
  await shot("upload");
  const run = await watchRunBody(page);
  await dialog.getByRole("button", { name: "Begin", exact: true }).click();
  await expect(page).toHaveURL(/\/case$/);
  expect(run.body()).toEqual({ sync: false, pace: "factory" });
  await expect(page.getByRole("complementary").getByText("Kewaunee · Nu Aire", { exact: true })).toBeVisible();

  // The questions come after about 14 s, from the recorded run, and the model card names it.
  await expect(page.getByText("The Mapper is asking you")).toBeVisible({ timeout: 40_000 });
  await expect(page.getByRole("complementary").locator("[title]").filter({ hasText: "Claude Haiku 5.5" })).toContainText("recorded run");
  await shot("asking");
  const later = page.getByRole("alert").getByRole("button", { name: "Later" });
  if (await later.count()) await later.click();
  await answerSuggested(page);
  await answerSuggested(page);
  await answerSuggested(page);
  await expect(page.getByText("The Mapper is asking you")).toHaveCount(0);
  await expect(handoff(page)).toBeVisible({ timeout: 40_000 });
  await expectCleanCase(page);
  await shot("handoff");
});

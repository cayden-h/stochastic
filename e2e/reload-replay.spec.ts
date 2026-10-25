// A page reloaded in the middle of a paced run (DEMO_PACE=1) reads the conversation again and follows the live run:
// nothing said before the reload is lost, and the run goes on to the Mapper's questions.
import { expect, open, test } from "./support/fixtures";
import { begin } from "./support/flows";

test("a reload mid-run replays the conversation and keeps following the run", async ({ page, shot }) => {
  await open(page, "/");
  await begin(page);
  const process = page.getByRole("region", { name: "The process" });
  const counter = process.getByText(/^\d+ messages?$/);
  const count = async () => Number(/\d+/.exec((await counter.textContent()) ?? "0")![0]);

  // Mid-run: the Mapper has proposed and is placing lines, and has not asked yet.
  await expect.poll(count, { timeout: 20_000 }).toBeGreaterThanOrEqual(3);
  await expect(page.getByText("The Mapper is asking you")).toHaveCount(0);
  const before = await process.getByRole("list").last().getByRole("listitem").allInnerTexts();
  expect(before.length).toBeGreaterThanOrEqual(3);
  await shot("before-reload");

  await page.reload();
  await expect(page.getByRole("status", { name: "Loading Stochastic" })).toHaveCount(0, { timeout: 15_000 });
  await expect(process).toBeVisible();
  // Every line from before the reload is back, in the same order, with the same text.
  await expect.poll(async () => (await process.getByRole("list").last().getByRole("listitem").allInnerTexts()).slice(0, before.length))
    .toEqual(before);
  await shot("after-reload");

  // And the page keeps following the live run.
  await expect(page.getByText("The Mapper is asking you")).toBeVisible({ timeout: 40_000 });
  expect(await count()).toBeGreaterThan(before.length);
  await expect(process.getByText(/Where does the target's 'Certificates of Deposit' belong/)).toBeVisible();
  await shot("asking-after-reload");
});

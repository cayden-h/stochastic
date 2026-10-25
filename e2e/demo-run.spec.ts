// The Dashboard's five cases and the 15-second demo (docs/demo-script.md section 2): every case opens fully on every
// page, then Run the demo resets the demo deal, the question arrives as a notification, Decide opens its card, each
// answer shows what was learned, and the books go to Review, the Mapping tab, approval, and the final files.
// These need the backend's demo contract (GET /deals with data_source, pace "demo", `notify`, `policy_id`).
import fs from "node:fs";
import path from "node:path";
import type { Page } from "@playwright/test";
import type { Backend } from "./support/backend";
import { expect, open, readCase, test } from "./support/fixtures";
import { NUAIRE_GA, bubble, editAmount, flagOptions, handoff, nav, reviewVerdict } from "./support/flows";

interface DealRow { deal_id: string; platform: string; target: string; stage: string; data_source?: string; note?: string; updated_at?: string }

async function deals(backend: Backend): Promise<DealRow[]> {
  const r = await fetch(`${backend.url}/deals`);
  expect(r.ok).toBeTruthy();
  return r.json();
}

/** Why this backend cannot run these tests, or null when it has the demo contract. */
async function missingContract(backend: Backend): Promise<string | null> {
  const list = await deals(backend);
  if (list.length < 5) return `GET /deals has ${list.length} deals, not 5`;
  if (!list.every((d) => d.deal_id && "data_source" in d && "updated_at" in d)) return "GET /deals rows have no deal_id, data_source, or updated_at";
  return null;
}

/** Answers every open question with its Suggested option, one card after the other. */
async function answerAll(page: Page): Promise<number> {
  let answered = 0;
  for (;;) {
    const suggested = flagOptions(page).filter({ hasText: "Suggested" });
    if (!(await suggested.count())) return answered;
    const heading = (await page.getByRole("main").getByRole("heading", { level: 2 }).first().textContent()) ?? "";
    await suggested.first().click();
    answered += 1;
    await expect(page.getByRole("main").getByRole("heading", { level: 2, name: heading, exact: true })).toHaveCount(0);
  }
}

test.beforeEach(async ({ backend }) => {
  const missing = await missingContract(backend);
  test.skip(missing !== null, `the backend lacks the demo contract: ${missing}`);
});

test("five cases on the Dashboard, and each one opens on every page", async ({ page, backend, shot }) => {
  test.setTimeout(120_000);
  const list = await deals(backend);
  await open(page, "/");
  await expect(page.locator("[data-deal]")).toHaveCount(list.length);
  // The stat cards count across every case.
  const open_ = list.filter((d) => d.stage !== "posted").length;
  await expect(page.locator('[data-stat="Open cases"], [data-stat="Open case"]')).toHaveText(String(open_));
  for (const d of list) {
    const row = page.locator(`[data-deal="${d.deal_id}"]`);
    await expect(row).toContainText(d.target);
    const tag = row.getByText("Sample data", { exact: true });
    if (d.data_source === "sample") {
      await expect(tag).toBeVisible();
      if (d.note) await expect(tag).toHaveAttribute("title", d.note);
    } else {
      await expect(tag).toHaveCount(0);
    }
  }
  await shot("dashboard");

  for (const d of list) {
    await nav(page, "Dashboard").click();
    await page.locator(`[data-deal="${d.deal_id}"]`).click();
    await expect(page).toHaveURL(/\/case$/);
    await expect(page.getByRole("heading", { name: "Case", level: 1 })).toBeVisible();
    // The sidebar's Deal names the case that was picked, and the Case speaks of its companies.
    await expect(page.getByRole("complementary").getByText(`${d.platform} · ${d.target}`, { exact: true })).toBeVisible();
    await shot(`${d.deal_id}-case`);
    const kase = await readCase(backend, d.deal_id);
    await nav(page, "Mapping").click();
    await expect(page.getByRole("heading", { name: "Mapping", level: 1 })).toBeVisible();
    if (kase.mappings.length) await expect(page.locator("[data-mapping-id]").first()).toBeVisible();
    await shot(`${d.deal_id}-mapping`);
    await nav(page, "Log").click();
    await expect(page.getByRole("heading", { name: "Log", level: 1 })).toBeVisible();
    await expect(page.getByText(new RegExp(`Chain intact\\. ${kase.audit.rows} rows?`))).toBeVisible();
    await shot(`${d.deal_id}-log`);
    await nav(page, "Review").click();
    await expect(page.getByRole("heading", { name: "Review", level: 1 })).toBeVisible();
    await expect(page.getByText(`${d.platform} + ${d.target} combined books`, { exact: true })).toBeVisible();
    if (kase.verdict) {
      await expect(page.getByText(new RegExp(`^${kase.verdict.leverage.toFixed(2)}× of`))).toBeVisible();
      await expect(page.getByText(`Platform · ${d.platform}`, { exact: true })).toBeAttached();
    }
    await shot(`${d.deal_id}-review`);
    await page.getByRole("tablist", { name: "Review tabs" }).getByRole("tab", { name: "Mapping" }).click();
    await expect(page.locator("[data-mapping-sheet]")).toBeVisible();
    await shot(`${d.deal_id}-review-mapping`);
  }
});

test("run the demo: the notification, Decide, Learned, Ready, then Review and Mapping, approve, download", async ({ page, backend, shot }, testInfo) => {
  test.setTimeout(120_000);
  await open(page, "/");
  // Start from another case, so the demo also switches the current deal.
  const other = (await deals(backend)).find((d) => d.data_source === "sample");
  if (other) {
    await page.locator(`[data-deal="${other.deal_id}"]`).click();
    await expect(page).toHaveURL(/\/case$/);
    await nav(page, "Dashboard").click();
  }
  await page.getByRole("button", { name: "Run the demo" }).click();
  const started = Date.now();
  await expect(page).toHaveURL(/\/case$/);
  const demo = (await deals(backend)).find((d) => d.data_source === "filings") ?? (await deals(backend))[0];
  await expect(page.getByRole("complementary").getByText(`${demo.platform} · ${demo.target}`, { exact: true })).toBeVisible();

  // The question arrives as a toast with the agent, the question, and Decide, and the Case item gets a badge.
  const toast = page.getByRole("alert").filter({ hasText: "Needs your decision" });
  await expect(toast).toBeVisible({ timeout: 20_000 });
  const toQuestion = (Date.now() - started) / 1000;
  expect(toQuestion).toBeLessThan(12);
  await expect(toast.getByRole("button", { name: "Decide" })).toBeVisible();
  await expect(page.locator("[data-badge]")).toBeVisible();
  await shot("notification");
  const item = await toast.getAttribute("data-notice");
  await toast.getByRole("button", { name: "Decide" }).click();
  await expect(toast).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => document.activeElement?.getAttribute("data-flag") ?? null)).toBe(item);
  // Nothing vague: every option shows its effect, and the card says what happens next.
  const options = flagOptions(page);
  const count = await options.count();
  expect(count).toBeGreaterThan(1);
  for (let i = 0; i < count; i++) await expect(options.nth(i).locator("[data-effect]")).not.toBeEmpty();
  await expect(page.locator("[data-next]").first()).toContainText("What happens next");
  await shot("decide");

  // Answer: the agent says what it learned, and the Policies counter pulses.
  await answerAll(page);
  const answered = Date.now();
  await expect(page.locator("[data-learned]").first()).toBeVisible();
  await expect(page.locator("[data-learned]").first()).toContainText(/learned p_\d+/i);
  await expect(page.locator('[data-counter="Policies"]')).toHaveClass(/counter-pulse/);
  await shot("learned");

  // Ready for approval about 7 s after the last answer.
  await expect(handoff(page)).toBeVisible({ timeout: 30_000 });
  expect((Date.now() - answered) / 1000).toBeLessThan(12);
  await shot("ready");

  // Review: the sidebar stays, two tabs, and Back to case works.
  await page.getByRole("link", { name: "Review the books" }).click();
  await expect(page).toHaveURL(/\/review$/);
  await expect(page.getByRole("navigation", { name: "Pages" })).toBeVisible();
  await expect(page.getByRole("tablist", { name: "Review tabs" }).getByRole("tab")).toHaveText(["Review", "Mapping"]);
  await page.getByRole("link", { name: "Back to case" }).click();
  await expect(page).toHaveURL(/\/case$/);
  await nav(page, "Review").click();
  await expect(reviewVerdict(page)).toBeVisible();
  await shot("review");

  // An amount: the Reviewer asks why.
  await editAmount(page, NUAIRE_GA, "5663");
  await expect(bubble(page)).toBeVisible();
  await shot("reviewer-asks");
  await page.keyboard.press("1");
  await page.keyboard.press("Enter");
  await expect(bubble(page)).toHaveCount(0);

  // A remap on the Mapping tab: the Reviewer asks again.
  await page.getByRole("tablist", { name: "Review tabs" }).getByRole("tab", { name: "Mapping" }).click();
  await page.getByRole("button", { name: /^Research and Development goes to Operating expenses\./ }).click();
  await page.getByRole("listbox", { name: `Map to a ${demo.platform} line` }).getByRole("option", { name: "Cost of products sold" }).click();
  await expect(bubble(page)).toBeVisible();
  await shot("remap-asks");
  await page.keyboard.press("1");
  await page.keyboard.press("Enter");
  await expect(bubble(page)).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Your edits" })).toContainText("Your edits (2)");

  // Approve, then the final files.
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByText("Approved and posted").first()).toBeVisible();
  const dir = path.join(testInfo.outputDir, "downloads");
  fs.mkdirSync(dir, { recursive: true });
  const names: string[] = [];
  page.on("download", async (d) => { names.push(d.suggestedFilename()); await d.saveAs(path.join(dir, d.suggestedFilename())); });
  await page.getByRole("button", { name: "Download final files" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Downloaded 2 files." })).toBeVisible();
  await expect.poll(() => names.length).toBe(2);
  expect(names).toContain(`${demo.platform} + ${demo.target} combined books.xlsx`);
  await shot("downloaded");

  const kase = await readCase(backend, demo.deal_id);
  expect(kase.verdict.posted).toBeTruthy();
  expect(kase.edits.filter((e: { status: string }) => e.status === "reasoned")).toHaveLength(2);
});

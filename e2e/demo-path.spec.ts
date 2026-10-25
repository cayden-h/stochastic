// The whole demo path, as on stage (docs/demo-script.md section 2, docs/design/review-companion.md section 9), on the
// scripted backend at DEMO_PACE=1. One screenshot per step goes to e2e/artifacts/screenshots/demo-path/.
import fs from "node:fs";
import path from "node:path";
import { expect, open, readCase, test } from "./support/fixtures";
import {
  NUAIRE_GA, answerSuggested, begin, bubble, centre, companion, editAmount, handoff, nav, reviewVerdict,
} from "./support/flows";
import { readWorkbook } from "./support/xlsx";

test("the demo path: run, answer, review, edit with a reason, approve, download", async ({ page, backend, shot }, testInfo) => {
  test.setTimeout(180_000);

  // Splash: only the mark and the name, centered, until the console has read the deal.
  await page.goto("/");
  const splash = page.getByRole("status", { name: "Loading Stochastic" });
  await expect(splash).toBeVisible();
  // The lockup (the circle mark over the name) is the splash's only child, centered on the page.
  const lockup = splash.locator(":scope > *");
  await expect(lockup).toHaveCount(1);
  await expect(lockup.locator("svg").first()).toBeVisible();
  await expect(splash).toContainText("stochastic");
  const box = (await lockup.boundingBox())!;
  expect(Math.abs(box.x + box.width / 2 - 720)).toBeLessThan(3);
  expect(Math.abs(box.y + box.height / 2 - 450)).toBeLessThan(3);
  await expect(splash).toHaveAccessibleName("Loading Stochastic");
  await shot("splash");
  await expect(splash).toHaveCount(0, { timeout: 15_000 });

  // Dashboard.
  await expect(page.getByRole("button", { name: /Kewaunee Scientific.*Not started/ })).toBeVisible();
  await shot("dashboard");

  // Begin: the Case opens and the run plays live, the Mapper first.
  await begin(page);
  const pipeline = page.getByRole("list", { name: "The agents' progress" });
  await expect(pipeline).toBeVisible();
  await expect(pipeline.getByRole("listitem").filter({ hasText: "Mapper" })).toContainText(/Working|Mapping/i);
  const conversation = page.getByRole("region", { name: "The process" });
  await expect(conversation.getByText("Map the 53 lines of Nu Aire to Kewaunee")).toBeVisible();
  await shot("case-live");

  // Mapping fills line by line while the Mapper works.
  await nav(page, "Mapping").click();
  await expect(page.getByRole("heading", { name: "Mapping", level: 1 })).toBeVisible();
  const count = page.getByText(/\d+ lines? · \d+ sure/);
  await expect(count).toBeVisible();
  await expect(page.getByText("Mapper is placing lines")).toBeVisible();
  const lines = async () => Number(/(\d+) lines? ·/.exec((await count.textContent()) ?? "")?.[1] ?? 0);
  const first = await lines();
  await expect.poll(lines, { timeout: 20_000 }).toBeGreaterThan(first);
  const second = await lines();
  expect(second).toBeLessThan(53);
  await shot("mapping-filling");
  await expect.poll(lines, { timeout: 30_000 }).toBe(53);

  // Agents: the 3D house, notes flying, and the Mapper asking.
  await nav(page, "Agents").click();
  const house = page.getByRole("group", { name: /The agents' office/ });
  await expect(house.locator("canvas")).toBeVisible();
  const mapper = house.locator(".agent-house-label").filter({ has: page.locator(".agent-house-pill > b", { hasText: /^Mapper$/ }) });
  await expect(mapper).toHaveAttribute("data-state", "asking", { timeout: 30_000 });
  await expect(mapper).toContainText("MAPPER · ASKING");
  // (Notes flying between rooms is checked in agents-3d.spec.ts, from a page opened before the agents talk.)
  await shot("agents-asking");

  // Case: the Mapper is asking. Answer both flags.
  await nav(page, "Case").click();
  await expect(page.getByText("The Mapper is asking you")).toBeVisible();
  await expect(page.getByText("2 questions hold the agents.")).toBeVisible();
  await shot("case-asking");
  await answerSuggested(page);
  await expect(page.getByText("Answer it and the run goes on.")).toBeVisible();
  await shot("case-one-answered");
  await answerSuggested(page);
  await expect(page.getByText("The Mapper is asking you")).toHaveCount(0);

  // The agents resume: the Preparer, then the Reviewer, then the hand-off.
  await expect(pipeline.getByRole("listitem").filter({ hasText: "Preparer" })).toContainText(/Working|Done|Drafting/i, { timeout: 30_000 });
  await shot("case-resumed");
  await expect(handoff(page)).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("link", { name: "Review the books" })).toBeVisible();
  await shot("case-handoff");

  // Log: the audit rows, and the conversation toggle.
  await page.getByRole("main").getByRole("link", { name: "See the log" }).click();
  await expect(page).toHaveURL(/\/log/);
  const view = page.getByRole("group", { name: "What the log shows" });
  await expect(view).toBeVisible();
  await expect(page.getByText(/chain/i).first()).toBeVisible();
  await shot("log-audit");
  await view.getByRole("button", { name: /Conversation/ }).click();
  await expect(page.getByText("Ready for your approval").first()).toBeVisible();
  await shot("log-conversation");

  // Review the books.
  await nav(page, "Case").click();
  await page.getByRole("link", { name: "Review the books" }).click();
  await expect(page).toHaveURL(/\/review$/);
  await expect(reviewVerdict(page)).toHaveText("0.76× of 2.50×");
  await shot("review-open");

  // Edit Nu Aire's General and Administrative, 6,163 -> 5,663: the verdict reads 0.75x.
  await editAmount(page, NUAIRE_GA, "5663");
  await expect(reviewVerdict(page)).toHaveText("0.75× of 2.50×");
  // The Reviewer glides to the cell and asks why.
  const cell = page.getByLabel(/^Nu Aire, General and Administrative: 5,663, edited from 6,163\. Needs a reason\.$/);
  await expect(cell).toBeVisible();
  await expect(companion(page)).toHaveAttribute("data-companion", "asking");
  await expect(bubble(page)).toBeVisible();
  await expect.poll(async () => {
    const c = await centre(cell), m = await centre(companion(page));
    return Math.hypot(c.x - m.x, c.y - m.y);
  }).toBeLessThan(260);
  await shot("review-asking");

  // Press 1, then Enter: the learned note, Edits 1.
  await page.keyboard.press("1");
  await expect(bubble(page).getByRole("radio", { name: /One-time acquisition cost/ })).toHaveAttribute("aria-checked", "true");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status").filter({ hasText: "Learned: allowed add-back, for the next add-on." })).toBeVisible();
  await expect(bubble(page)).toHaveCount(0);
  await expect(page.getByRole("tab", { name: /Edits\s*1/ })).toBeVisible();
  await expect(page.getByLabel(/^Nu Aire, General and Administrative: 5,663, edited from 6,163\. Reason: One-time acquisition cost/)).toBeVisible();
  await shot("review-learned");

  // Approve, then Download final files.
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByText("Approved and posted").first()).toBeVisible();
  await shot("review-approved");
  const downloads: { name: string; file: string }[] = [];
  const dir = path.join(testInfo.outputDir, "downloads");
  fs.mkdirSync(dir, { recursive: true });
  page.on("download", async (d) => {
    const file = path.join(dir, d.suggestedFilename());
    await d.saveAs(file);
    downloads.push({ name: d.suggestedFilename(), file });
  });
  await page.getByRole("button", { name: "Download final files" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Downloaded 2 files." })).toBeVisible();
  await expect.poll(() => downloads.length).toBe(2);
  await shot("review-downloaded");

  // The workbook: the edited cell is amber and carries its note.
  const xlsx = downloads.find((d) => d.name.endsWith(".xlsx"))!;
  expect(xlsx.name).toBe("Kewaunee + Nu Aire combined books.xlsx");
  const wb = await readWorkbook(xlsx.file);
  const amber = wb.get("Combined")!.cells.filter((c) => c.fill === "FBEBC8");
  expect(amber).toHaveLength(1);
  // A target edit is marked on the platform row its line maps onto: Nu Aire's column of Operating expenses.
  const row = /\d+/.exec(amber[0].ref)![0];
  expect(amber[0].ref).toBe(`D${row}`);
  expect(wb.get("Combined")!.cells.find((c) => c.ref === `A${row}`)?.text).toBe("Operating expenses");
  expect(amber[0].note).toContain("Line was 6,162.806");
  expect(amber[0].note).toContain("Reason: One-time acquisition cost, an allowed add-back.");
  const edits = wb.get("Edits")!;
  expect(edits.rows).toBe(2);
  expect(edits.cells.map((c) => c.text)).toContain("General and Administrative");

  // The certificate lists the edit and its reason.
  const cert = downloads.find((d) => d.name.endsWith(".md"))!;
  expect(cert.name).toBe("Compliance certificate (draft).md");
  const text = fs.readFileSync(cert.file, "utf8");
  expect(text).toContain("General and Administrative");
  expect(text).toContain("One-time acquisition cost, an allowed add-back");

  // The record agrees: posted, one reasoned edit, chain intact.
  const kase = await readCase(backend);
  expect(kase.verdict.posted).toBeTruthy();
  expect(kase.edits.filter((e: { status: string }) => e.status === "reasoned")).toHaveLength(1);
  expect(kase.audit.chain_valid).toBe(true);
});

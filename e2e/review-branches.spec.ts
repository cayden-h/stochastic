// The Review page's other branches (docs/design/review-companion.md sections 4 to 7): an edit left for Later and the
// waiting dot that reopens it, a remap with its roll-up through the subtotals, a large change that asks first, and
// Undo. Each test starts from a fresh backend and runs the deal to the Reviewer's hand-off (no pacing).
import { expect, open, readCase, test } from "./support/fixtures";
import { NUAIRE_GA, bubble, companion, editAmount, reviewVerdict, sheetRow, toReview } from "./support/flows";

test.beforeEach(async ({ page }) => {
  await open(page, "/");
  await toReview(page);
});

test("Later leaves the edit waiting; the companion's dot reopens the bubble", async ({ page, shot }) => {
  await editAmount(page, NUAIRE_GA, "5663");
  await expect(bubble(page)).toBeVisible();
  await bubble(page).getByRole("button", { name: "Later" }).click();
  await expect(bubble(page)).toHaveCount(0);

  // The edit waits: amber chip, approval refused, the companion shows its violet dot.
  await expect(page.getByText("1 edit needs a reason").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve", exact: true })).toBeDisabled();
  await expect(companion(page)).toHaveAttribute("data-companion", "waiting");
  const dot = page.getByRole("button", { name: "1 edit needs a reason. Give it now." });
  await expect(dot).toBeVisible();
  await shot("waiting");

  // The dot reopens the bubble on that edit; a typed reason saves it.
  await dot.click();
  await expect(bubble(page)).toBeVisible();
  await expect(companion(page)).toHaveAttribute("data-companion", "asking");
  await bubble(page).getByRole("textbox", { name: "Add your reason" }).fill("Audit fee booked twice");
  await bubble(page).getByRole("button", { name: "Save reason" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Learned: audit fee booked twice, for the next add-on." })).toBeVisible();
  await expect(companion(page)).not.toHaveAttribute("data-companion", "waiting");
  await expect(page.getByText("1 edit, reason given")).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve", exact: true })).toBeEnabled();
  await shot("reason-given");
});

test("remap a target line: the subtotals roll, leverage holds, the rule is learned", async ({ page, backend, shot }) => {
  const before = { gross: await sheetRow(page, "Gross profit"), operating: await sheetRow(page, "Operating profit") };
  expect(before.gross.c).toBe("23,682");
  const n = (s: string) => Number(s.replace(/[(),]/g, "")) * (s.startsWith("(") ? -1 : 1);

  // The line cell's menu lists the platform's lines; pick Cost of products sold.
  await page.getByRole("button", { name: "Nu Aire, Research and Development. Map it to a Kewaunee line" }).click();
  const menu = page.getByRole("listbox", { name: "Map to a Kewaunee line" });
  await expect(menu).toBeVisible();
  await shot("remap-menu");
  await menu.getByRole("option", { name: "Cost of products sold" }).click();

  // The remap bubble: its own chips and the platform-wide rule.
  await expect(bubble(page)).toBeVisible();
  await expect(bubble(page).getByText("Apply to every add-on on this platform")).toBeVisible();
  await expect(page.getByRole("button", { name: "Nu Aire, Research and Development: remapped to Cost of products sold" })).toBeVisible();
  await shot("remap-asking");
  await page.keyboard.press("1");
  await expect(bubble(page).getByRole("radio", { name: /Not a cash equivalent/ })).toHaveAttribute("aria-checked", "true");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status").filter({ hasText: "Learned: mapping rule, for this platform." })).toBeVisible();

  // The roll-up: Nu Aire's Gross profit falls by the 532 moved into cost of sales; Operating profit and leverage hold.
  await expect.poll(async () => (await sheetRow(page, "Gross profit")).c).toBe("23,150");
  const after = { gross: await sheetRow(page, "Gross profit"), operating: await sheetRow(page, "Operating profit") };
  expect(n(after.gross.d)).toBe(n(before.gross.d) - 532);
  expect(after.operating.d).toBe(before.operating.d);
  expect(after.operating.c).toBe(before.operating.c);
  await expect(reviewVerdict(page)).toHaveText("0.76× of 2.50×");
  await expect(page.getByText("Ties out", { exact: true })).toBeVisible();
  await shot("remap-learned");

  // The record: a reasoned remap, its policy, and the target's gross profit to the dollar.
  const kase = await readCase(backend);
  const remap = kase.edits.find((e: { kind: string }) => e.kind === "remap");
  expect(remap.status).toBe("reasoned");
  expect(remap.policy_id).toBeTruthy();
  const gp = kase.result.rows.find((r: { line: string }) => r.line === "Gross profit");
  expect(gp.target).toBeCloseTo(23149.519, 3);
});

test("a large change asks first; Change it goes back to the cell, Yes saves it", async ({ page, shot }) => {
  await editAmount(page, NUAIRE_GA, "1000");
  const confirm = page.getByRole("dialog", { name: "Confirm a large change" });
  await expect(confirm).toBeVisible();
  await expect(confirm.getByText("This is a large change.")).toBeVisible();
  await shot("large-change");

  // Change it: back in the cell, nothing saved.
  await confirm.getByRole("button", { name: "Change it" }).click();
  await expect(confirm).toHaveCount(0);
  const input = page.getByRole("textbox", { name: `${NUAIRE_GA}, USD thousands` });
  await expect(input).toBeFocused();
  await expect(reviewVerdict(page)).toHaveText("0.76× of 2.50×");

  // The same value again, then Yes: the edit is saved and the bubble asks why.
  await input.fill("1000");
  await input.press("Enter");
  await expect(confirm).toBeVisible();
  await confirm.getByRole("button", { name: "Yes, save it" }).click();
  await expect(bubble(page)).toBeVisible();
  await expect(page.getByLabel(/^Nu Aire, General and Administrative: 1,000, edited from 6,163\. Needs a reason\.$/)).toBeVisible();
  await expect(reviewVerdict(page)).not.toHaveText("0.76× of 2.50×");
  await shot("large-change-saved");
});

test("Undo brings the agents' value and verdict back", async ({ page, backend, shot }) => {
  await editAmount(page, NUAIRE_GA, "5663");
  await expect(reviewVerdict(page)).toHaveText("0.75× of 2.50×");
  await expect(bubble(page)).toBeVisible();
  await page.keyboard.press("1");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("tab", { name: /Edits\s*1/ })).toBeVisible();

  const strip = page.getByRole("region", { name: "Your edits" });
  await strip.getByRole("button", { name: "Undo" }).click();
  await expect(reviewVerdict(page)).toHaveText("0.76× of 2.50×");
  await expect(page.getByRole("button", { name: `${NUAIRE_GA}: 6,163. Edit` })).toBeVisible();
  await expect(page.getByText("None yet. Click a platform or target amount to change it.")).toBeVisible();
  await expect(page.getByRole("tab", { name: /Edits\s*0/ })).toBeVisible();
  await shot("undone");

  const kase = await readCase(backend);
  expect(kase.edits.every((e: { status: string }) => e.status === "reverted")).toBe(true);
});

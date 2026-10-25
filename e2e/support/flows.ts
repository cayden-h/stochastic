// The demo path's steps, as a controller clicks them. Every wait is on something the screen shows.
import { type Locator, type Page, expect } from "@playwright/test";

export const NUAIRE_GA = "Nu Aire, General and Administrative";

/** The sidebar link to a page (Dashboard, Case, Review, Mapping, Agents, Log). */
export function nav(page: Page, name: string): Locator {
  return page.getByRole("navigation", { name: "Pages" }).getByRole("link", { name, exact: true });
}

/** The open flag card's options: buttons whose name starts with "a.", "b.", "c.". */
export function flagOptions(page: Page): Locator {
  return page.getByRole("main").getByRole("button", { name: /^[a-e]\. / });
}

/** The demo deal, the one the gateway's fixture seeds (backend/app/db/fixtures/kewaunee.py). */
export const DEMO_DEAL = "d_kequ_nuaire";

/** Dashboard -> the demo deal's row -> the Case page -> Run the deal, at the gateway's own pace (DEMO_PACE).
 * The Dashboard has no Begin: its buttons are Run the demo (pace "demo") and Upload (Begin there is pace "factory"). */
export async function begin(page: Page): Promise<void> {
  await expect(page.getByRole("heading", { name: "Dashboard", level: 1 })).toBeVisible();
  await expect(page.getByRole("button", { name: "Begin", exact: true })).toHaveCount(0);
  await page.locator(`[data-deal="${DEMO_DEAL}"]`).click();
  await expect(page).toHaveURL(/\/case$/);
  await expect(page.getByRole("heading", { name: "Case", level: 1 })).toBeVisible();
  await page.getByRole("button", { name: "Run the deal", exact: true }).click();
}

/** The Case's Combined books toggle: the books start hidden behind Show combined books. */
/** The Case after the Reviewer's hand-off: the flag card, the pipeline, and the limit check's four figure tiles. No
 * conversation, no verdict sentence (the leverage against the limit, the as-filed reading, Download final files: those
 * are on Review), and the combined books hidden until Show combined books. */
export async function expectCleanCase(page: Page): Promise<void> {
  const main = page.getByRole("main");
  const figures = main.getByRole("region", { name: "The limit check" });
  await expect(figures).toBeVisible();
  for (const label of ["Senior Funded Bank Debt", "Covenant EBITDA", "Room (turns of EBITDA)", "Covenant headroom"]) {
    await expect(figures.getByText(label, { exact: true })).toBeVisible();
  }
  await expect(figures.getByText("21,633K", { exact: true })).toBeVisible();
  await expect(figures.getByText(/^\d+\.\d\d×$/)).toBeVisible();
  await expect(figures.getByText(/^\$\d+\.\dM of debt$/)).toBeVisible();
  await expect(main.getByText(/× against \d/)).toHaveCount(0);
  await expect(main.getByText(/Read as filed/)).toHaveCount(0);
  await expect(main.getByText(/Download final files/)).toHaveCount(0);
  await expect(main.getByText("Reviewer pass", { exact: true })).toHaveCount(0);
  await expect(main.getByText(/^Conversation$/i)).toHaveCount(0);
  await expect(main.getByRole("list", { name: "The agents' progress" })).toBeVisible();
  // The books start hidden; the toggle shows them and hides them again.
  await expect(main.getByText("Balance sheet", { exact: true })).toHaveCount(0);
  await booksToggle(page).click();
  await expect(main.getByText("Balance sheet", { exact: true })).toBeVisible();
  await expect(booksToggle(page, true)).toHaveAttribute("aria-expanded", "true");
  await booksToggle(page, true).click();
  await expect(main.getByText("Balance sheet", { exact: true })).toHaveCount(0);
  await expect(booksToggle(page)).toHaveAttribute("aria-expanded", "false");
}

/** Every agent character on the page is drawn from the one v3 file for its role, served as it is (not through
 * /_next/image), and the Mapper's is the teal star. Returns how many Mapper characters the page shows. */
export async function expectOneIconSource(page: Page): Promise<number> {
  const imgs = page.getByRole("main").locator("img[data-agent]");
  await expect(imgs.first()).toBeVisible();
  const all = await imgs.evaluateAll((els) => els.map((e) => ({ role: e.getAttribute("data-agent"), src: e.getAttribute("src") })));
  for (const { role, src } of all) expect(src).toBe(`/v3/agent-${role!.replace("_", "-")}.png`);
  // No agent art from anywhere else: no optimizer URL and no other file.
  const others = await page.locator("img").evaluateAll((els) => els.map((e) => e.getAttribute("src") ?? "").filter((s) => /agent|_next\/image/.test(s) && !/^\/v3\/agent-/.test(s)));
  expect(others).toEqual([]);
  return all.filter((a) => a.role === "mapper").length;
}

export function booksToggle(page: Page, shown = false): Locator {
  return page.getByRole("button", { name: shown ? "Hide combined books" : "Show combined books" });
}

/** Watches the Upload modal's run request and returns the body it sent, so a test can check Begin asks for pace
 * "factory". */
export async function watchRunBody(page: Page): Promise<{ body: () => Record<string, unknown> | null }> {
  let sent: Record<string, unknown> | null = null;
  await page.route(/\/deals\/[^/]+\/run$/, async (route) => {
    if (route.request().method() === "POST") sent ??= (route.request().postDataJSON() ?? {}) as Record<string, unknown>;
    return route.fallback();
  });
  return { body: () => sent };
}

/** Answers the open flag with its Suggested option and waits until that flag has left the card. */
export async function answerSuggested(page: Page): Promise<string> {
  const question = page.getByRole("main").getByRole("heading", { level: 2 }).first();
  const asked = (await question.textContent()) ?? "";
  const option = flagOptions(page).filter({ hasText: "Suggested" });
  await expect(option).toHaveCount(1);
  await option.click();
  await expect(page.getByText("Answered", { exact: false }).first()).toBeVisible();
  await expect(page.getByRole("main").getByRole("heading", { level: 2, name: asked, exact: true })).toHaveCount(0);
  return asked;
}

/** Waits for the Mapper's questions, then answers both with the suggested option. */
export async function answerBothFlags(page: Page): Promise<void> {
  await expect(page.getByText("The Mapper is asking you")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("2 questions hold the agents.")).toBeVisible();
  await answerSuggested(page);
  await expect(page.getByText("Answer it and the run goes on.")).toBeVisible();
  await answerSuggested(page);
  await expect(page.getByText("The Mapper is asking you")).toHaveCount(0);
}

/** The Reviewer's hand-off card on the Case. */
export function handoff(page: Page): Locator {
  return page.getByText("The Reviewer passed the books. Ready for your approval.");
}

/** The whole first run on the Case: answer both flags and wait for the hand-off. */
export async function runToHandoff(page: Page): Promise<void> {
  await answerBothFlags(page);
  await expect(handoff(page)).toBeVisible({ timeout: 60_000 });
}

/** The Review page's verdict figure, "0.76× of 2.50×". */
export function reviewVerdict(page: Page): Locator {
  return page.getByText(/^\d+\.\d\d× of \d+\.\d\d×$/);
}

/** The reason bubble (a dialog), once the companion has reached the cell. */
export function bubble(page: Page): Locator {
  return page.getByRole("dialog", { name: "Why did you make this change?" });
}

/** Clicks an amount cell on Review, types the new value, and presses Enter. */
export async function editAmount(page: Page, cell: string, value: string): Promise<void> {
  await page.getByRole("button", { name: new RegExp(`^${escape(cell)}: [\\d,()]+\\. Edit$`) }).click();
  const input = page.getByRole("textbox", { name: `${cell}, USD thousands` });
  await expect(input).toBeFocused();
  await input.fill(value);
  await input.press("Enter");
}

export function escape(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** The companion's mark: data-companion is idle, asking, or waiting. */
export function companion(page: Page): Locator {
  return page.locator("[data-companion]");
}

/** The centre of an element's box, in page pixels. */
export async function centre(l: Locator): Promise<{ x: number; y: number }> {
  const b = await l.boundingBox();
  if (!b) throw new Error("no box");
  return { x: b.x + b.width / 2, y: b.y + b.height / 2 };
}

/** Dashboard to the Review page with the agents' books: Begin, answer both flags, wait for the hand-off, Review. */
export async function toReview(page: Page): Promise<void> {
  await begin(page);
  await runToHandoff(page);
  await page.getByRole("link", { name: "Review the books" }).click();
  await expect(page).toHaveURL(/\/review$/);
  await expect(reviewVerdict(page)).toHaveText("0.76× of 2.50×");
}

/** The texts of a Review sheet row's cells, A to E, found by the line in column A. */
export async function sheetRow(page: Page, line: string): Promise<{ a: string; b: string; c: string; d: string; e: string }> {
  const row = page.locator("[data-sheet-row]").filter({ has: page.getByText(line, { exact: true }) }).first();
  const cells = await row.evaluate((el) => [...el.children].map((c) => (c as HTMLElement).innerText.trim()));
  // cells[0] is the row number; a struck-through agent value sits above an edited amount, so keep the last line.
  const last = (s: string | undefined) => (s ?? "").split("\n").pop()!.trim();
  return { a: last(cells[1]), b: last(cells[2]), c: last(cells[3]), d: last(cells[4]), e: last(cells[5]) };
}

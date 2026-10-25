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

/** Dashboard -> Begin -> the Case page. */
export async function begin(page: Page): Promise<void> {
  await expect(page.getByRole("heading", { name: "Dashboard", level: 1 })).toBeVisible();
  await page.getByRole("button", { name: "Begin", exact: true }).click();
  await expect(page).toHaveURL(/\/case$/);
  await expect(page.getByRole("heading", { name: "Case", level: 1 })).toBeVisible();
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

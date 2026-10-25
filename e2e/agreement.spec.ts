// The agreement-text path (D20): upload the two statement CSVs and the credit agreement as text. The Brief Reader
// drafts the Brief, the controller answers its questions and enters the add-back amounts from the books, approves the
// Brief, and the run goes on as on the demo deal: map, flags, books, review, approval.
import { expect, open, test } from "./support/fixtures";
import { writeDemoCsvs } from "./support/demo-files";
import { AGREEMENT } from "./support/env";
import { handoff, reviewVerdict, runToHandoff } from "./support/flows";

test("a deal from the agreement text: Brief card, answer and correct, approve the Brief, map, review", async ({ page, backend, shot }, testInfo) => {
  const csv = writeDemoCsvs(testInfo.outputDir);
  await open(page, "/");
  await page.getByRole("button", { name: "Upload", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "New deal" });
  await dialog.locator("input[type=file][multiple]").setInputFiles([csv.platform, csv.target, AGREEMENT]);
  await expect(dialog.getByRole("button", { name: /^Kewaunee\.csv \d+ rows · as Kewaunee$/ })).toBeVisible();
  await expect(dialog.getByRole("button", { name: /^Nu-Aire\.csv \d+ rows · as Nu Aire$/ })).toBeVisible();
  await expect(dialog.getByRole("button", { name: /kewaunee_ex101_excerpt\.txt Agreement text/ })).toBeVisible();
  await shot("upload");
  await dialog.getByRole("button", { name: "Begin", exact: true }).click();
  await expect(page).toHaveURL(/\/case$/);

  // The Brief card: every field quoted, six questions before approval.
  const brief = page.getByRole("region", { name: "Brief" });
  await expect(brief.getByRole("heading", { name: "Check the Brief before the agents map." })).toBeVisible();
  await expect(brief.getByText("6 questions left before you can approve")).toBeVisible();
  const approveBrief = brief.getByRole("button", { name: "Approve the Brief and map" });
  await expect(approveBrief).toBeDisabled();
  await expect(page.getByRole("list", { name: "The agents' progress" }).getByRole("listitem").filter({ hasText: "Brief Reader" })).toContainText("Done");
  await shot("brief-card");

  // Answer the reader's question, enter three amounts from the books with their source, keep 0 on the other two.
  await brief.getByRole("button", { name: "Keep the reader's value" }).click();
  await expect(brief.getByText("5 questions left before you can approve")).toBeVisible();
  const amounts: [string, string, string][] = [
    ["Noncash pension termination expense", "4019", "10-K FY2025, pension termination"],
    ["Stock-based compensation", "1018", "10-K FY2025, cash flow statement"],
    ["Cash rent on the Statesville property", "1970", "10-K FY2025, lease note"],
  ];
  let left = 5;
  for (const [name, value, source] of amounts) {
    await brief.getByRole("textbox", { name: `${name}: amount in USD thousands` }).fill(value);
    await brief.getByRole("textbox", { name: `${name}: source` }).fill(source);
    await brief.getByRole("textbox", { name: `${name}: source` }).press("Enter");
    left -= 1;
    await expect(brief.getByText(`${left} question${left === 1 ? "" : "s"} left before you can approve`)).toBeVisible();
    await expect(brief.getByRole("textbox", { name: `${name}: amount in USD thousands` })).toHaveCount(0);
  }
  for (const name of ["Transaction costs (capped)", "Integration costs (capped)"]) {
    await brief.getByRole("textbox", { name: `${name}: amount in USD thousands` }).locator("..").getByRole("button", { name: "Keep 0" }).click();
    left -= 1;
    await expect(brief.getByRole("textbox", { name: `${name}: amount in USD thousands` })).toHaveCount(0);
  }
  await expect(brief.getByText("Every question answered")).toBeVisible();
  await expect(brief.getByText("4,019K")).toBeVisible();
  await shot("brief-answered");

  // Approve the Brief: the Mapper starts.
  await approveBrief.click();
  await expect(brief).toHaveCount(0);
  await runToHandoff(page);
  await expect(handoff(page)).toBeVisible();
  await expect(page.getByText(/0\.76× against 2\.50×/).first()).toBeVisible();
  await shot("handoff");

  // The rest of the path: review and approve.
  await page.getByRole("link", { name: "Review the books" }).click();
  await expect(reviewVerdict(page)).toHaveText("0.76× of 2.50×");
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByText("Approved and posted").first()).toBeVisible();
  await shot("approved");

  // The record: the uploaded deal is posted, on the Brief the controller approved.
  const deals = await (await fetch(`${backend.url}/deals`)).json();
  const uploaded = deals.find((d: { id: string }) => d.id !== "d_kequ_nuaire");
  expect(uploaded.brief_status).toBe("approved");
  expect(uploaded.stage).toBe("posted");
});

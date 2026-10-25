// The second run (docs/demo-script.md section 2): after an approval, "Run it again with what was learned" keeps the
// Mapper's policies, so the run asks nothing and shows the Learned chips. "Fresh deal (clear memory)" drops them, and
// the next run asks again.
import { expect, open, readCase, test } from "./support/fixtures";
import { handoff, nav, toReview } from "./support/flows";

test("run it again with what was learned, then a fresh deal", async ({ page, backend, shot }) => {
  await open(page, "/");
  await toReview(page);
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByText("Approved and posted").first()).toBeVisible();
  const learned = (await readCase(backend)).policies.length;
  expect(learned).toBeGreaterThan(0);

  // Back on the Case: run it again with what was learned.
  await page.getByRole("link", { name: "Back to case" }).click();
  await expect(page.getByText("Approved and posted").first()).toBeVisible();
  await page.getByRole("button", { name: "Run it again with what was learned" }).click();
  await expect(page.getByRole("heading", { name: "Run again. The Mapper now applies what you decided." })).toBeVisible();
  await shot("ready-again");
  await page.getByRole("button", { name: "Run again", exact: true }).click();

  // No questions this time: the hand-off comes straight through, with the Learned chips.
  await expect(handoff(page)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("The Mapper is asking you")).toHaveCount(0);
  await expect(page.getByText(/No flag this time\. The Mapper applied your (earlier answer|\d+ earlier answers) to \d+ lines?/)).toBeVisible();
  // Nothing is unsure on the second run: no question is open, and the lines a policy placed are not unsure (37 is the
  // 53 target lines less the 16 totals, which are not counted).
  await expect(page.getByRole("link", { name: /^Mapping 37 placed Learned 37 sure · 0 unsure · \d+ lines? learned$/ })).toBeVisible();
  const again = await readCase(backend);
  expect(again.flags.filter((f: { answer: string | null }) => f.answer)).toHaveLength(0);
  expect(again.policies.length).toBe(learned);
  await shot("learned");

  // Mapping shows the lines placed by policy.
  await nav(page, "Mapping").click();
  const byPolicy = page.getByRole("group", { name: "Filter the mappings" }).getByRole("button", { name: "By policy" });
  await byPolicy.click();
  await expect(byPolicy).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText("Certificates of Deposit", { exact: true })).toBeVisible();
  await expect(page.getByText(/^37 lines · 37 sure · 0 unsure · 16 totals$/)).toBeVisible();
  await shot("mapping-by-policy");
  const unsure = page.getByRole("group", { name: "Filter the mappings" }).getByRole("button", { name: "Unsure" });
  await unsure.click();
  await expect(page.getByText(/^No line waits on you\./)).toBeVisible();

  // Fresh deal (clear memory): the policies are gone and the next run asks again.
  await nav(page, "Case").click();
  await page.getByRole("button", { name: "Fresh deal (clear memory)" }).click();
  await expect(page.getByRole("heading", { name: "Two sets of books. One lender's limit." })).toBeVisible();
  expect((await readCase(backend)).policies).toHaveLength(0);
  await expect(page.getByRole("complementary").getByText(/Policies\s*0/)).toBeVisible();
  await page.getByRole("button", { name: "Run the deal", exact: true }).click();
  await expect(page.getByText("The Mapper is asking you")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("2 questions hold the agents.")).toBeVisible();
  await shot("fresh-asks-again");
});

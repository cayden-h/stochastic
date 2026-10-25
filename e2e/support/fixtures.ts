// The test fixtures: a fresh backend per test (scripted agents, memory store), the console page, and screenshots.
import fs from "node:fs";
import path from "node:path";
import { test as base, expect, type Page, type TestInfo } from "@playwright/test";
import { type Backend, startBackend } from "./backend";
import { ARTIFACTS, SCREENSHOTS, ensureDir, ports } from "./env";

export interface Options {
  /** DEMO_PACE for this test's backend: 1 plays the run at reading speed, 0 runs it as fast as it goes. */
  pace: number;
  /** DEMO_CASES for this test's backend: the Dashboard's seeded cases beside the demo deal. Off by default, so a test
   * sees only the demo deal and the policies it teaches; demo-run.spec.ts turns it on. */
  cases: boolean;
  /** DEMO_FROM_AGREEMENT: the demo deal starts from its agreement text (D23). Off by default, so the other specs start
   * at the Mapper as before; demo-run.spec.ts turns it on. */
  fromAgreement: boolean;
}

interface Fixtures {
  backend: Backend;
  /** Saves a screenshot to e2e/artifacts/screenshots/<spec>/<nn>-<name>.png and attaches it to the report. */
  shot: (name: string, target?: Page) => Promise<void>;
  /** Every request the page made to a host other than localhost. */
  external: string[];
}

const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export const test = base.extend<Fixtures & Options>({
  pace: [0, { option: true }],
  cases: [false, { option: true }],
  fromAgreement: [false, { option: true }],

  backend: [async ({ pace, cases, fromAgreement }, use, testInfo) => {
    const logDir = ensureDir(path.join(ARTIFACTS, "logs"));
    const logFile = path.join(logDir, `${slug(path.basename(testInfo.file, ".spec.ts"))}-${slug(testInfo.title)}-r${testInfo.retry}.log`);
    fs.writeFileSync(logFile, "");
    const backend = await startBackend({ port: ports().backend, consolePort: ports().console, pace, cases, fromAgreement, logFile });
    await use(backend);
    await backend.stop({ dumpThreads: testInfo.status !== testInfo.expectedStatus });
    if (testInfo.status !== testInfo.expectedStatus) await testInfo.attach("backend.log", { path: logFile, contentType: "text/plain" });
  }, { auto: true }],

  external: async ({ page }, use) => {
    const seen: string[] = [];
    page.on("request", (r) => {
      const host = new URL(r.url()).hostname;
      if (!/^(localhost|127\.0\.0\.1|\[::1\])$/.test(host) && !r.url().startsWith("data:") && !r.url().startsWith("blob:")) seen.push(r.url());
    });
    await use(seen);
  },

  shot: async ({ page }, use, testInfo) => {
    let n = 0;
    const dir = ensureDir(path.join(SCREENSHOTS, slug(path.basename(testInfo.file, ".spec.ts")), slug(testInfo.title)));
    await use(async (name, target = page) => {
      n += 1;
      const file = path.join(dir, `${String(n).padStart(2, "0")}-${slug(name)}.png`);
      await target.screenshot({ path: file });
      await testInfo.attach(name, { path: file, contentType: "image/png" });
    });
  },
});

export { expect };

/** Opens a console page and waits for the launch splash to finish and the first read of the deal. */
export async function open(page: Page, route = "/"): Promise<void> {
  await page.goto(route);
  await expect(page.getByRole("status", { name: "Loading Stochastic" })).toHaveCount(0, { timeout: 15_000 });
}

/** The current deal's case, read straight from the API (for assertions on the record, not to drive the UI). */
export async function readCase(backend: Backend, dealId = "d_kequ_nuaire"): Promise<Record<string, any>> {
  const r = await fetch(`${backend.url}/deals/${dealId}/case`);
  expect(r.ok).toBeTruthy();
  return r.json();
}

export function info(): TestInfo {
  return test.info();
}

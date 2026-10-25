import path from "node:path";
import { defineConfig, devices } from "@playwright/test";
import type { Options } from "./support/fixtures";
import { ARTIFACTS, DIST_DIR, FRONTEND_DIR, resolvePorts } from "./support/env";

// Free ports for this run (never 8000 or 3000, which the installed app uses). Written into process.env here, so the
// worker processes get the same ones.
const ports = resolvePorts();
const apiUrl = `http://localhost:${ports.backend}`;

// One backend port is baked into the console build (NEXT_PUBLIC_API_URL), and each test starts its own backend on
// it, so the tests run one at a time.
export default defineConfig<Options>({
  testDir: ".",
  outputDir: path.join(ARTIFACTS, "test-results"),
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  timeout: 120_000,
  expect: { timeout: 10_000 },
  reporter: [["list"], ["html", { outputFolder: path.join(ARTIFACTS, "report"), open: "never" }]],
  use: {
    baseURL: `http://localhost:${ports.console}`,
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    acceptDownloads: true,
  },
  projects: [
    {
      // The functional branches, on a backend with no pacing: each run finishes in about a second. demo-run.spec.ts
      // asks for pace "demo" on its run, the 15-second demo, and factory-upload.spec.ts for pace "factory", the 30-second one.
      name: "fast",
      testMatch: ["review-branches.spec.ts", "second-run.spec.ts", "agreement.spec.ts", "demo-run.spec.ts", "factory-upload.spec.ts", "check-math.spec.ts"],
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 }, pace: 0 },
    },
    {
      // The live demo path, at DEMO_PACE=1: the run plays at reading speed, as on stage.
      name: "paced",
      testMatch: ["demo-path.spec.ts", "reload-replay.spec.ts", "agents-3d.spec.ts"],
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
        pace: 1,
        // WebGL in headless Chromium, in software, so the 3D house renders on any Mac.
        launchOptions: { args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] },
      },
    },
    {
      // The Mac app (desktop/main.js) through Playwright's Electron driver. It starts its own backend and console.
      name: "electron",
      testMatch: ["electron.spec.ts"],
      timeout: 180_000,
    },
  ],
  webServer: {
    // Builds the console for this run's backend port into frontend/.next-e2e (about 10 s), then serves it.
    command: `npx next build && npx next start -p ${ports.console}`,
    cwd: FRONTEND_DIR,
    url: `http://127.0.0.1:${ports.console}/`,
    env: { NEXT_DIST_DIR: DIST_DIR, NEXT_PUBLIC_API_URL: apiUrl, NEXT_TELEMETRY_DISABLED: "1" },
    reuseExistingServer: false,
    timeout: 240_000,
    stdout: "ignore",
    stderr: "pipe",
  },
});

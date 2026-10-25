// The Mac app (desktop/main.js), launched through Playwright's Electron driver: the splash first, the main window only
// once the backend answers and the console has loaded and read the deal, a shortened demo path inside the app with
// window.stochastic.saveFiles writing the final files, and a quit that leaves nothing listening.
// The app starts its own backend (on the suite's backend port, which the console build points at) and its own console
// (on a third free port), from this checkout, with the scripted agents. No backend fixture runs for this project.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { _electron as electron, expect, test as base } from "@playwright/test";
import { portBusy, until } from "./support/backend";
import { DESKTOP_DIR, DIST_DIR, ROOT, SCREENSHOTS, backendEnv, ensureDir, ports } from "./support/env";
import { NUAIRE_GA, answerBothFlags, begin, bubble, editAmount, handoff, reviewVerdict } from "./support/flows";
import { readWorkbook } from "./support/xlsx";

const test = base;

interface WinState { url: string; visible: boolean; bounds: { width: number; height: number }; content: { width: number; height: number }; background: string; destroyed: boolean }

test("the Mac app: splash, then the console, the demo path with saveFiles, and a clean quit", async ({}, testInfo) => {
  const { backend, appConsole } = ports();
  for (const p of [backend, appConsole]) expect(await portBusy(p), `port ${p} is free before the app starts`).toBe(false);
  const userData = fs.mkdtempSync(path.join(os.tmpdir(), "stochastic-e2e-profile-"));
  const saveDir = ensureDir(path.join(testInfo.outputDir, "saved"));
  const shots = ensureDir(path.join(SCREENSHOTS, "electron"));
  let n = 0;
  const shot = async (page: import("@playwright/test").Page, name: string) => {
    const file = path.join(shots, `${String(++n).padStart(2, "0")}-${name}.png`);
    await page.screenshot({ path: file });
    await testInfo.attach(name, { path: file, contentType: "image/png" });
  };

  const env = backendEnv(0, appConsole);
  delete env.CORS_ORIGINS; // the app sets it for its own console
  delete env.ELECTRON_RUN_AS_NODE;
  const app = await electron.launch({
    executablePath: require(path.join(DESKTOP_DIR, "node_modules", "electron")) as unknown as string,
    args: [DESKTOP_DIR],
    cwd: DESKTOP_DIR,
    env: {
      ...env,
      STOCHASTIC_ROOT: ROOT,
      STOCHASTIC_BACKEND_PORT: String(backend),
      STOCHASTIC_CONSOLE_PORT: String(appConsole),
      NEXT_PUBLIC_API_URL: `http://localhost:${backend}`,
      NEXT_DIST_DIR: DIST_DIR,
      STOCHASTIC_USER_DATA: userData,
    } as Record<string, string>,
    timeout: 60_000,
  });
  let closed = false;
  try {
    // Watch the windows from the start: which are open and visible, polled from the main process.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- the electron module is typed from desktop/, not here
    // Each sample carries the main process's own clock, read with the window states, so the times do not include
    // the round trip to the test.
    const sample = (): Promise<{ now: number; states: WinState[] }> => app.evaluate(({ BrowserWindow }) => ({
      now: Date.now(),
      states: BrowserWindow.getAllWindows().map((w: any) => ({
        url: w.webContents.getURL(), visible: w.isVisible(), bounds: w.getBounds(), content: w.getContentBounds(),
        background: w.getBackgroundColor(), destroyed: w.isDestroyed(),
      })),
    }));
    const windows = async (): Promise<WinState[]> => (await sample()).states;
    const t0 = Date.now();
    // Sample the windows every 50 ms from launch until the main window shows, while the splash is checked below.
    const timeline: { at: number; states: WinState[] }[] = [];
    let mainSampled = 0;
    const watched = until("the main window to show", async () => {
      const { now, states } = await sample();
      timeline.push({ at: now - t0, states });
      const main = states.find((w) => w.url.startsWith(`http://localhost:${appConsole}`));
      if (main?.visible) { mainSampled = now - t0; return true; }
      return false;
    }, 90_000, 50);
    // The first window is the splash: only the mark and the name, on a transparent page.
    const first = await app.firstWindow();
    expect(first.url()).toContain("splash.html");
    await expect(first.locator("body")).toContainText("stochastic");
    await expect(first.locator("svg").first()).toBeVisible();
    const backgrounds = await first.evaluate(() => [getComputedStyle(document.documentElement).backgroundColor, getComputedStyle(document.body).backgroundColor]);
    expect(backgrounds).toEqual(["rgba(0, 0, 0, 0)", "rgba(0, 0, 0, 0)"]);
    await shot(first, "splash");
    await watched;

    // The splash came first: a 360 by 420 window on splash.html, frameless (content fills it) and transparent,
    // visible while the main window was hidden.
    const splashSeen = timeline.filter((t) => t.states.some((w) => w.url.includes("splash.html") && w.visible));
    expect(splashSeen.length, "the splash was on screen before the main window").toBeGreaterThan(0);
    const splash = splashSeen[0].states.find((w) => w.url.includes("splash.html"))!;
    expect(splash.bounds).toMatchObject({ width: 360, height: 420 });
    expect(splash.content).toMatchObject({ width: 360, height: 420 });
    // Electron reports a fully transparent window's colour without its alpha.
    expect(splash.background.toUpperCase()).toMatch(/^#(00)?000000$/);
    // Every sample before the one where the main window showed had it hidden (the splash fades out after it shows).
    for (const t of timeline.slice(0, -1)) {
      expect(t.states.find((w) => w.url.startsWith(`http://localhost:${appConsole}`))?.visible ?? false).toBe(false);
    }
    // It held for its draw (the app holds it 2.1 s). The samples see each change up to one poll and one round trip
    // late, so the bound allows 300 ms.
    expect(mainSampled - splashSeen[0].at).toBeGreaterThanOrEqual(1800);

    // When the main window showed, the backend answered and the console had read the deal.
    const health = await fetch(`http://127.0.0.1:${backend}/health`);
    expect(health.ok).toBe(true);
    expect((await health.json()).backend.configured).toBe("scripted");
    const page = app.windows().find((p) => p.url().startsWith(`http://localhost:${appConsole}`))!;
    await expect(page.getByRole("heading", { name: "Dashboard", level: 1 })).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("data-electron", "");
    expect(await page.evaluate(() => Boolean((window as unknown as { stochastic?: { isDesktop?: boolean } }).stochastic?.isDesktop))).toBe(true);
    // The browser splash never shows in the app, and the Electron splash has closed.
    await expect(page.getByRole("status", { name: "Loading Stochastic" })).toHaveCount(0);
    await until("the splash to close", async () => !(await windows()).some((w: WinState) => w.url.includes("splash.html")), 5000);
    await shot(page, "dashboard");

    // The demo path, shortened: run, answer, review, edit with a reason, approve.
    await begin(page);
    await answerBothFlags(page);
    await expect(handoff(page)).toBeVisible({ timeout: 30_000 });
    await shot(page, "handoff");
    await page.getByRole("link", { name: "Review the books" }).click();
    await expect(reviewVerdict(page)).toHaveText("0.76× of 2.50×");
    await editAmount(page, NUAIRE_GA, "5663");
    await expect(reviewVerdict(page)).toHaveText("0.75× of 2.50×");
    await expect(bubble(page)).toBeVisible();
    await page.keyboard.press("1");
    await page.keyboard.press("Enter");
    await expect(page.getByRole("status").filter({ hasText: "Learned: allowed add-back, for the next add-on." })).toBeVisible();
    await page.getByRole("button", { name: "Approve", exact: true }).click();
    await expect(page.getByText("Approved and posted").first()).toBeVisible();
    await shot(page, "approved");

    // Download final files goes through window.stochastic.saveFiles: the folder dialog (answered here with a test
    // folder) and Finder (not opened) are stubbed in the main process; the download and the write are the app's own.
    // First the controller closes the folder dialog: nothing is written and nothing says "Saved.".
    await app.evaluate(({ dialog, shell }) => {
      const g = globalThis as unknown as { shown: string[]; asked: number };
      g.shown = []; g.asked = 0;
      dialog.showOpenDialog = (async () => { g.asked += 1; return { canceled: true, filePaths: [] }; }) as typeof dialog.showOpenDialog;
      shell.showItemInFolder = (p: string) => { g.shown.push(p); };
    });
    const download = page.getByRole("button", { name: "Download final files" });
    await download.click();
    await expect.poll(() => app.evaluate(() => (globalThis as unknown as { asked: number }).asked)).toBe(1);
    await expect(download).toBeEnabled();
    await expect(page.getByText("Saved.")).toHaveCount(0);
    expect(fs.readdirSync(saveDir)).toEqual([]);
    await app.evaluate(({ dialog }, folder) => {
      dialog.showOpenDialog = (async () => ({ canceled: false, filePaths: [folder] })) as typeof dialog.showOpenDialog;
    }, saveDir);
    await download.click();
    await expect(page.getByRole("status").filter({ hasText: "Saved." })).toBeVisible();
    await shot(page, "saved");
    const xlsx = path.join(saveDir, "Kewaunee + Nu Aire combined books.xlsx");
    const cert = path.join(saveDir, "Compliance certificate (draft).md");
    expect(fs.existsSync(xlsx) && fs.existsSync(cert)).toBe(true);
    const amber = (await readWorkbook(xlsx)).get("Combined")!.cells.filter((c) => c.fill === "FBEBC8");
    expect(amber).toHaveLength(1);
    expect(amber[0].note).toContain("One-time acquisition cost, an allowed add-back");
    expect(fs.readFileSync(cert, "utf8")).toContain("One-time acquisition cost, an allowed add-back");
    expect(await app.evaluate(() => (globalThis as unknown as { shown: string[] }).shown)).toEqual([xlsx]);

    // Quit: the app stops the backend and the console before it exits.
    await app.close();
    closed = true;
    await until("the app's ports to be free", async () => !(await portBusy(backend)) && !(await portBusy(appConsole)), 10_000);
  } finally {
    if (!closed) await app.close().catch(() => {});
    fs.rmSync(userData, { recursive: true, force: true });
  }
});

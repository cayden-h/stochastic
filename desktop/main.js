// Electron main process for the Stochastic desktop app (design/review-companion.md section 11).
// It shows the launch splash (splash.html, design/brand.md), starts the backend and the built console as child
// processes, waits for both to answer and for the console to load in a hidden window, then shows that window,
// fades the splash out, and stops both children on quit.
// STOCHASTIC_DEV=1 loads an already running `next dev` on port 3000 and starts nothing.
// Packaged as Stochastic.app (`npm run package`), it still runs the backend and console from this repo,
// whose path is written into the app's package.json at package time.

const { app, BrowserWindow, Menu, dialog, ipcMain, shell } = require("electron");
const { execFileSync, spawn } = require("node:child_process");
const fs = require("node:fs");
const net = require("node:net");
const path = require("node:path");

const ROOT = process.env.STOCHASTIC_ROOT
  || (app.isPackaged ? require("./package.json").stochasticRoot : null)
  || path.resolve(__dirname, "..");
const BACKEND_DIR = path.join(ROOT, "backend");
const FRONTEND_DIR = path.join(ROOT, "frontend");
// The ports can be moved (for a second copy next to a running one); the console must then be built with the
// matching NEXT_PUBLIC_API_URL.
const BACKEND_PORT = Number(process.env.STOCHASTIC_BACKEND_PORT) || 8000;
const CONSOLE_PORT = Number(process.env.STOCHASTIC_CONSOLE_PORT) || 3000;
const API_BASE = process.env.NEXT_PUBLIC_API_URL || `http://localhost:${BACKEND_PORT}`;
const CONSOLE_URL = `http://localhost:${CONSOLE_PORT}`;
const READY_TIMEOUT_MS = 30_000;
const STOP_TIMEOUT_MS = 5_000;
const DEV = process.env.STOCHASTIC_DEV === "1";
const BACKGROUND = "#F7F4EC";
// The splash plays its whole draw (1.77 s) and holds the finished lockup until 2.1 s, the approved prototype's
// handover, before it may close, so it never cuts mid-draw (design/brand.md).
const SPLASH_MIN_MS = 2100;
const SPLASH_FADE_MS = 200;
// After the console page loads, wait for its first deal read (window.stochastic.appReady) up to this long.
const APP_READY_CAP_MS = 8_000;

app.setName("Stochastic");
// STOCHASTIC_USER_DATA puts the app's profile (and its single-instance lock) in another folder, so the e2e suite can
// run a copy while the installed Stochastic.app is open (e2e/electron.spec.ts).
if (process.env.STOCHASTIC_USER_DATA) app.setPath("userData", process.env.STOCHASTIC_USER_DATA);

// ---- running from Finder ----

// An app opened from Finder gets a bare PATH, so `node` (for next) and `droid` (for the Droid backend)
// would not be found. Take the PATH the user's login shell sets up instead.
function useLoginShellPath() {
  const fallback = ["/opt/homebrew/bin", "/usr/local/bin", path.join(process.env.HOME || "", ".local", "bin")];
  try {
    const shellPath = process.env.SHELL || "/bin/zsh";
    const out = execFileSync(shellPath, ["-ilc", 'printf "__PATH__%s__PATH__" "$PATH"'], { encoding: "utf8", timeout: 5000, stdio: ["ignore", "pipe", "ignore"] });
    const found = /__PATH__(.*)__PATH__/.exec(out);
    if (found && found[1]) { process.env.PATH = found[1]; return; }
  } catch { /* fall through to the usual folders */ }
  process.env.PATH = [...fallback, process.env.PATH].join(":");
}
if (app.isPackaged) useLoginShellPath();

// Run from a terminal, output goes there. Packaged, it also goes to ~/Library/Logs/Stochastic/desktop.log.
let logStream = null;
function log(line) {
  console.log(line);
  if (!app.isPackaged) return;
  if (!logStream) {
    const file = path.join(app.getPath("logs"), "desktop.log");
    fs.mkdirSync(path.dirname(file), { recursive: true });
    logStream = fs.createWriteStream(file, { flags: "a" });
    logStream.write(`\n---- ${new Date().toISOString()} start, root ${ROOT}\n`);
  }
  logStream.write(line + "\n");
}

const services = []; // { name, child, tail, exited }
let mainWindow = null;
let splashWindow = null;
let quitting = false;

// ---- child processes ----

function startService(name, command, args, cwd, env = {}) {
  if (quitting) throw new ServiceError(name, "Stochastic is quitting");
  // detached puts the child in its own process group, so stopping it also stops anything it spawned
  const child = spawn(command, args, { cwd, env: { ...process.env, ...env }, detached: true, stdio: ["ignore", "pipe", "pipe"] });
  const service = { name, child, tail: [], exited: null };
  const keep = (chunk) => {
    for (const line of chunk.toString().split("\n")) {
      if (!line.trim()) continue;
      log(`[${name}] ${line}`);
      service.tail.push(line);
      if (service.tail.length > 30) service.tail.shift();
    }
  };
  child.stdout.on("data", keep);
  child.stderr.on("data", keep);
  child.on("error", (error) => { service.exited = `could not start: ${error.message}`; });
  child.on("exit", (code, signal) => { service.exited = service.exited || `exited with ${signal || `code ${code}`}`; });
  services.push(service);
  return service;
}

function groupAlive(pid) {
  try { process.kill(-pid, 0); return true; } catch { return false; }
}

async function stopService(service) {
  const { pid } = service.child;
  if (!pid || !groupAlive(pid)) return;
  try { process.kill(-pid, "SIGTERM"); } catch { /* already gone */ }
  const deadline = Date.now() + STOP_TIMEOUT_MS;
  while (groupAlive(pid) && Date.now() < deadline) await sleep(100);
  if (groupAlive(pid)) {
    log(`[${service.name}] did not stop in ${STOP_TIMEOUT_MS / 1000}s, killing it`);
    try { process.kill(-pid, "SIGKILL"); } catch { /* already gone */ }
  }
}

function stopAll() {
  return Promise.all(services.map(stopService));
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// A port counts as busy if anything accepts a connection on it, on IPv4 or IPv6.
function portBusy(port) {
  const tryHost = (host) => new Promise((resolve) => {
    const socket = net.connect({ port, host });
    socket.setTimeout(500);
    socket.once("connect", () => { socket.destroy(); resolve(true); });
    socket.once("timeout", () => { socket.destroy(); resolve(false); });
    socket.once("error", () => resolve(false));
  });
  return Promise.all([tryHost("127.0.0.1"), tryHost("::1")]).then((r) => r.some(Boolean));
}

// Polls url until isReady(response) is true. Fails early if the service process exits.
async function waitFor(name, url, isReady, service) {
  const deadline = Date.now() + READY_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (service && service.exited) throw new ServiceError(name, `the ${name} ${service.exited}`, service.tail);
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(1000) });
      if (isReady(response)) return;
    } catch { /* not up yet */ }
    await sleep(300);
  }
  throw new ServiceError(name, `the ${name} did not answer at ${url} within ${READY_TIMEOUT_MS / 1000} seconds`, service ? service.tail : []);
}

class ServiceError extends Error {
  constructor(name, message, tail = []) {
    super(message);
    this.service = name;
    this.tail = tail;
  }
}

function runToEnd(name, command, args, cwd) {
  return new Promise((resolve, reject) => {
    const service = startService(name, command, args, cwd);
    service.child.on("exit", (code) => {
      services.splice(services.indexOf(service), 1);
      if (code === 0) resolve();
      else reject(new ServiceError("console", `the console build failed (${service.exited})`, service.tail));
    });
    service.child.on("error", () => reject(new ServiceError("console", `the console build ${service.exited}`, service.tail)));
  });
}

async function startEverything() {
  const uvicorn = path.join(BACKEND_DIR, ".venv", "bin", "uvicorn");
  const next = path.join(FRONTEND_DIR, "node_modules", ".bin", "next");
  if (!fs.existsSync(uvicorn)) throw new ServiceError("backend", `the backend is not installed: ${uvicorn} is missing. Stochastic looks for the repo at ${ROOT} (see README.md, "Getting started")`);
  if (!fs.existsSync(next)) throw new ServiceError("console", "the console is not installed: run `npm install` in frontend/");
  if (await portBusy(BACKEND_PORT)) throw new ServiceError("backend", `port ${BACKEND_PORT} is already in use. Stop the other backend, then open Stochastic again.`);
  if (await portBusy(CONSOLE_PORT)) throw new ServiceError("console", `port ${CONSOLE_PORT} is already in use. Stop the other console (or use STOCHASTIC_DEV=1), then open Stochastic again.`);

  // NEXT_DIST_DIR (frontend/next.config.ts) points at another build, as the e2e suite does.
  if (!fs.existsSync(path.join(FRONTEND_DIR, process.env.NEXT_DIST_DIR || ".next", "BUILD_ID"))) {
    log("[console] no build found, running next build first");
    await runToEnd("console build", next, ["build"], FRONTEND_DIR);
  }

  const backend = startService("backend", uvicorn, ["app.main:app", "--port", String(BACKEND_PORT), "--timeout-graceful-shutdown", "2"], BACKEND_DIR,
    process.env.CORS_ORIGINS ? {} : { CORS_ORIGINS: `http://localhost:${CONSOLE_PORT},http://127.0.0.1:${CONSOLE_PORT}` });
  const consoleApp = startService("console", next, ["start", "-p", String(CONSOLE_PORT)], FRONTEND_DIR, { NODE_ENV: "production" });
  await Promise.all([
    waitFor("backend", `http://127.0.0.1:${BACKEND_PORT}/health`, (r) => r.ok, backend),
    waitFor("console", `http://127.0.0.1:${CONSOLE_PORT}/`, (r) => r.status < 500, consoleApp),
  ]);
}

// ---- windows ----

// The launch splash: only the circle mark and the name, centered on the screen, on a transparent background.
// Its ink follows the macOS appearance, because Electron maps nativeTheme to the page's prefers-color-scheme.
// Resolves with the time the splash became visible, when its animation starts.
function createSplash() {
  splashWindow = new BrowserWindow({
    title: "Stochastic",
    width: 360,
    height: 420,
    center: true,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    hasShadow: false,
    resizable: false,
    movable: false,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    show: false,
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  const win = splashWindow;
  win.on("closed", () => { if (splashWindow === win) splashWindow = null; });
  const shown = new Promise((resolve) => {
    win.once("ready-to-show", () => {
      if (win.isDestroyed()) return resolve(Date.now());
      win.show();
      win.webContents.executeJavaScript("window.splashPlay()").catch(() => {});
      resolve(Date.now());
    });
  });
  win.loadFile(path.join(__dirname, "splash.html"), { query: { wait: "1" } });
  // If the splash never paints, do not hold the app for it.
  return Promise.race([shown, sleep(3000).then(() => Date.now() - SPLASH_MIN_MS)]);
}

async function closeSplash({ fade }) {
  const win = splashWindow;
  splashWindow = null;
  if (!win || win.isDestroyed()) return;
  if (fade) {
    await win.webContents.executeJavaScript("window.splashOut()").catch(() => {});
    await sleep(SPLASH_FADE_MS + 20);
  }
  if (!win.isDestroyed()) win.destroy();
}

let appReady = null; // resolves when the console reports its first deal read
ipcMain.on("stochastic:app-ready", (event) => {
  if (mainWindow && event.sender === mainWindow.webContents && appReady) appReady();
});

// Opens the console in a hidden window. Resolves once the page has loaded and painted and the console has
// finished its first read of the deal (or APP_READY_CAP_MS after the load, for a console that does not report it).
function createMainWindow() {
  mainWindow = new BrowserWindow({
    title: "Stochastic",
    width: 1440,
    height: 900,
    minWidth: 1280,
    minHeight: 800,
    titleBarStyle: "hiddenInset",
    trafficLightPosition: { x: 20, y: 20 },
    backgroundColor: BACKGROUND,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  const win = mainWindow;
  const reported = new Promise((resolve) => { appReady = resolve; });
  const loaded = Promise.all([
    new Promise((resolve) => win.once("ready-to-show", resolve)),
    new Promise((resolve, reject) => {
      win.webContents.once("did-finish-load", resolve);
      win.webContents.on("did-fail-load", (_event, code, description, url, isMainFrame) => {
        if (isMainFrame && code !== -3) reject(new ServiceError("console", `the console page did not load (${description}, ${url})`));
      });
    }),
  ]).then(() => Promise.race([reported, sleep(APP_READY_CAP_MS)]));
  mainWindow.on("closed", () => { if (mainWindow === win) mainWindow = null; });

  // Links to other sites open in the browser; the window itself stays on the console.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  mainWindow.webContents.on("will-navigate", (event, url) => {
    if (new URL(url).origin !== new URL(CONSOLE_URL).origin) {
      event.preventDefault();
      if (/^https?:/.test(url)) shell.openExternal(url);
    }
  });
  mainWindow.loadURL(CONSOLE_URL).catch(() => { /* did-fail-load reports it */ });
  return loaded;
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function showErrorWindow(error) {
  const which = error.service ? `The ${error.service} failed to start.` : "Stochastic failed to start.";
  const tail = error.tail && error.tail.length ? `<pre>${escapeHtml(error.tail.join("\n"))}</pre>` : "";
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Stochastic</title><style>
    body { margin: 0; padding: 48px 32px 32px; background: ${BACKGROUND}; color: #1d1d1b; font: 14px/1.5 -apple-system, system-ui, sans-serif; }
    h1 { font-size: 18px; margin: 0 0 8px; }
    pre { background: #fff; border: 1px solid #ddd6c6; padding: 12px; font: 11px/1.4 ui-monospace, Menlo, monospace; white-space: pre-wrap; max-height: 260px; overflow: auto; }
    </style></head><body><h1>${escapeHtml(which)}</h1><p>${escapeHtml(error.message.charAt(0).toUpperCase() + error.message.slice(1))}</p>${tail}
    <p>Quit with Cmd+Q. Nothing is left running.</p></body></html>`;
  const win = new BrowserWindow({
    title: "Stochastic", width: 640, height: error.tail && error.tail.length ? 520 : 300,
    titleBarStyle: "hiddenInset", trafficLightPosition: { x: 20, y: 20 }, backgroundColor: BACKGROUND,
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true, javascript: false },
  });
  win.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
}

function buildMenu() {
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { role: "appMenu" }, // About, Hide, and Quit, all labelled with app.name ("Stochastic")
    { role: "editMenu" }, // copy and paste in the review table's inputs
    {
      label: "View",
      submenu: [
        { role: "reload" },
        { role: "toggleDevTools" },
        { type: "separator" },
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" },
      ],
    },
    { role: "windowMenu" },
  ]));
}

// ---- window.stochastic.saveFiles ----

ipcMain.handle("stochastic:save-files", async (event, files) => {
  if (new URL(event.senderFrame.url).origin !== new URL(CONSOLE_URL).origin) throw new Error("saveFiles is only for the console");
  if (!Array.isArray(files) || files.length === 0) throw new Error("saveFiles needs a list of { url, name }");
  const apiOrigin = new URL(API_BASE).origin;
  const planned = files.map(({ url, name } = {}) => {
    if (typeof url !== "string" || typeof name !== "string") throw new Error("each file needs a url and a name");
    const resolved = new URL(url, API_BASE);
    if (resolved.origin !== apiOrigin) throw new Error(`saveFiles only downloads from the API (${apiOrigin}), not ${resolved.origin}`);
    const safeName = path.basename(name);
    if (!safeName || safeName === "." || safeName === "..") throw new Error(`not a file name: ${name}`);
    return { url: resolved.href, name: safeName };
  });

  const window = BrowserWindow.fromWebContents(event.sender);
  const choice = await dialog.showOpenDialog(window, {
    title: "Save the final files",
    buttonLabel: "Save here",
    properties: ["openDirectory", "createDirectory"],
  });
  if (choice.canceled || !choice.filePaths[0]) return { canceled: true, folder: null, files: [] };

  const folder = choice.filePaths[0];
  const written = [];
  for (const file of planned) {
    const response = await fetch(file.url);
    if (!response.ok) throw new Error(`${file.name}: the API answered ${response.status}`);
    const target = path.join(folder, file.name);
    await fs.promises.writeFile(target, Buffer.from(await response.arrayBuffer()));
    written.push(target);
  }
  shell.showItemInFolder(written[0]);
  return { canceled: false, folder, files: written };
});

// ---- app lifecycle ----

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) { if (mainWindow.isMinimized()) mainWindow.restore(); mainWindow.focus(); }
  });

  app.whenReady().then(async () => {
    app.setAboutPanelOptions({ applicationName: "Stochastic" });
    const icon = path.join(__dirname, "assets", "icon.png");
    if (process.platform === "darwin" && fs.existsSync(icon)) app.dock.setIcon(icon);
    buildMenu();
    const splashShown = createSplash();
    try {
      if (DEV) await waitFor("console", `http://127.0.0.1:${CONSOLE_PORT}/`, (r) => r.status < 500);
      else await startEverything();
      if (quitting) return;
      await createMainWindow();
      await sleep(Math.max(0, (await splashShown) + SPLASH_MIN_MS - Date.now()));
      if (quitting || !mainWindow) return;
      mainWindow.show();
      await closeSplash({ fade: true });
    } catch (error) {
      log(error.message);
      await stopAll();
      if (quitting) return;
      // Open the error window before closing the others, so the app never has zero windows and quits.
      showErrorWindow(error);
      await closeSplash({ fade: false });
      if (mainWindow) mainWindow.destroy();
    }
  });

  app.on("window-all-closed", () => app.quit());

  // Hold the quit until both child processes have stopped, so nothing stays on ports 8000 or 3000.
  app.on("before-quit", (event) => {
    if (quitting) return;
    quitting = true;
    event.preventDefault();
    // close the windows first, so the console's open event stream does not hold the backend's shutdown
    for (const win of BrowserWindow.getAllWindows()) win.destroy();
    stopAll().finally(() => app.exit(0));
  });

  // Ctrl+C in the terminal that runs `npm run desktop` quits cleanly too.
  for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) process.on(signal, () => app.quit());
}

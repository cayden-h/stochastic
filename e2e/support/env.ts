// Paths and ports for the suite. The config runs first in the runner process and writes the ports into process.env,
// so the worker processes (which inherit the runner's env) read the same ports.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

export const E2E_DIR = path.resolve(__dirname, "..");
export const ROOT = path.resolve(E2E_DIR, "..");
export const BACKEND_DIR = path.join(ROOT, "backend");
export const FRONTEND_DIR = path.join(ROOT, "frontend");
export const DESKTOP_DIR = path.join(ROOT, "desktop");
export const ARTIFACTS = path.join(E2E_DIR, "artifacts");
export const SCREENSHOTS = path.join(ARTIFACTS, "screenshots");
/** The console build the suite serves. A separate folder, so it never overwrites frontend/.next (the Mac app's). */
export const DIST_DIR = ".next-e2e";
export const PYTHON = process.env.E2E_PYTHON || path.join(BACKEND_DIR, ".venv", "bin", "python");
export const AGREEMENT = path.join(BACKEND_DIR, "tests", "fixtures", "kewaunee_ex101_excerpt.txt");

// The installed Mac app uses these. The suite never binds them.
const RESERVED = new Set([8000, 3000]);

/** Free TCP ports from the OS, picked in a child process because the config must be synchronous. */
function freePorts(count: number): number[] {
  const script = `
    const net = require("node:net");
    const out = [];
    const servers = [];
    const next = () => {
      if (out.length === ${count}) { servers.forEach((s) => s.close()); console.log(out.join(",")); return; }
      const s = net.createServer();
      s.listen(0, "127.0.0.1", () => { const p = s.address().port; servers.push(s); if (!${JSON.stringify([...RESERVED])}.includes(p)) out.push(p); next(); });
    };
    next();`;
  return execFileSync(process.execPath, ["-e", script], { encoding: "utf8" }).trim().split(",").map(Number);
}

/** The ports for this run: E2E_BACKEND_PORT, E2E_CONSOLE_PORT and E2E_APP_CONSOLE_PORT if set, else free ones. */
export function resolvePorts(): { backend: number; console: number; appConsole: number } {
  if (!process.env.E2E_BACKEND_PORT || !process.env.E2E_CONSOLE_PORT || !process.env.E2E_APP_CONSOLE_PORT) {
    const [b, c, a] = freePorts(3);
    process.env.E2E_BACKEND_PORT ||= String(b);
    process.env.E2E_CONSOLE_PORT ||= String(c);
    process.env.E2E_APP_CONSOLE_PORT ||= String(a);
  }
  const ports = {
    backend: Number(process.env.E2E_BACKEND_PORT),
    console: Number(process.env.E2E_CONSOLE_PORT),
    appConsole: Number(process.env.E2E_APP_CONSOLE_PORT),
  };
  for (const p of Object.values(ports)) {
    if (RESERVED.has(p)) throw new Error(`port ${p} is the installed app's; the suite must not use it`);
  }
  return ports;
}

export const ports = () => ({
  backend: Number(process.env.E2E_BACKEND_PORT),
  console: Number(process.env.E2E_CONSOLE_PORT),
  appConsole: Number(process.env.E2E_APP_CONSOLE_PORT),
});
export const apiUrl = () => `http://localhost:${ports().backend}`;

/** The backend's environment: the scripted agents only, the memory store, no keys, no Tiger. Never a live model.
 * `cases` seeds the Dashboard's sample cases (DEMO_CASES) beside the demo deal. */
export function backendEnv(pace: number, consolePort: number, cases = false): NodeJS.ProcessEnv {
  return {
    ...process.env,
    AGENT_BACKEND: "scripted",
    AGENT_FALLBACK: "scripted",
    STORE: "memory",
    FORKS: "off",
    DATABASE_URL: "",
    TIMESCALE_SERVICE_URL: "",
    FACTORY_API_KEY: "",
    ANTHROPIC_API_KEY: "",
    DEMO_PACE: pace ? String(pace) : "0",
    DEMO_CASES: cases ? "1" : "0",
    CORS_ORIGINS: `http://localhost:${consolePort},http://127.0.0.1:${consolePort}`,
    PYTHONUNBUFFERED: "1",
  };
}

export function ensureDir(dir: string): string {
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

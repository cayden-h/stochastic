// Starts and stops the gateway API (uvicorn) for one test, so every test begins on a freshly seeded deal.
import { type ChildProcess, spawn } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import { BACKEND_DIR, PYTHON, backendEnv } from "./env";

/** True if anything accepts a connection on the port, on IPv4 or IPv6. */
export async function portBusy(port: number): Promise<boolean> {
  const probe = (host: string) => new Promise<boolean>((resolve) => {
    const s = net.connect({ port, host });
    s.setTimeout(500);
    s.once("connect", () => { s.destroy(); resolve(true); });
    s.once("timeout", () => { s.destroy(); resolve(false); });
    s.once("error", () => resolve(false));
  });
  const [v4, v6] = await Promise.all([probe("127.0.0.1"), probe("::1")]);
  return v4 || v6;
}

/** Polls until check() is true, or throws after timeoutMs. The interval is a poll, never a fixed wait for an outcome. */
export async function until(what: string, check: () => Promise<boolean> | boolean, timeoutMs = 15_000, everyMs = 100): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    if (await check()) return;
    if (Date.now() > deadline) throw new Error(`timed out after ${timeoutMs} ms waiting for ${what}`);
    await new Promise((r) => setTimeout(r, everyMs));
  }
}

export interface Backend {
  url: string;
  port: number;
  /** Stops the backend. With dumpThreads, it first prints every Python thread's stack to the log (on a failure). */
  stop: (opts?: { dumpThreads?: boolean }) => Promise<void>;
}

export async function startBackend({ port, consolePort, pace, cases = false, fromAgreement = false, logFile }: { port: number; consolePort: number; pace: number; cases?: boolean; fromAgreement?: boolean; logFile: string }): Promise<Backend> {
  if (!fs.existsSync(PYTHON)) {
    throw new Error(`the backend is not installed: ${PYTHON} is missing (README.md, "Getting started", or set E2E_PYTHON)`);
  }
  if (await portBusy(port)) throw new Error(`port ${port} is already in use; the backend cannot start`);
  // The backend writes its log straight to the file, not through a pipe this process must drain, so a busy test
  // process can never block the backend on a full pipe.
  const out = fs.openSync(logFile, "a");
  const log = { write: (text: string) => fs.appendFileSync(logFile, text), end: () => fs.closeSync(out) };
  const child: ChildProcess = spawn(
    PYTHON,
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(port), "--timeout-graceful-shutdown", "1"],
    { cwd: BACKEND_DIR, env: { ...backendEnv(pace, consolePort, cases, fromAgreement), PYTHONFAULTHANDLER: "1" }, detached: true, stdio: ["ignore", out, out] },
  );
  let exited: string | null = null;
  const done = new Promise<void>((resolve) => child.once("exit", (code, signal) => { exited = `${signal ?? code}`; resolve(); }));
  const url = `http://127.0.0.1:${port}`;
  try {
    await until("the backend's /health", async () => {
      if (exited) throw new Error(`the backend exited (${exited}); see ${logFile}`);
      const r = await fetch(`${url}/health`).catch(() => null);
      return Boolean(r?.ok);
    }, 20_000);
  } catch (e) {
    try { process.kill(-child.pid!, "SIGKILL"); } catch { /* gone */ }
    throw e;
  }
  return {
    url,
    port,
    stop: async ({ dumpThreads = false } = {}) => {
      const note = (text: string) => log.write(`[e2e ${new Date().toISOString()}] ${text}\n`);
      if (!exited && dumpThreads) {
        // PYTHONFAULTHANDLER prints every thread's stack on SIGABRT, so a hung run shows where it waits.
        note("test failed: dumping the backend's threads");
        try { process.kill(child.pid!, "SIGABRT"); } catch { /* gone */ }
        const timer = setTimeout(() => { try { process.kill(-child.pid!, "SIGKILL"); } catch { /* gone */ } }, 4000);
        await done;
        clearTimeout(timer);
      }
      note("stopping");
      if (!exited) {
        try { process.kill(-child.pid!, "SIGTERM"); } catch { /* gone */ }
        const timer = setTimeout(() => { try { process.kill(-child.pid!, "SIGKILL"); } catch { /* gone */ } }, 4000);
        await done;
        clearTimeout(timer);
      }
      note("stopped");
      log.end();
      await until(`port ${port} to be free`, async () => !(await portBusy(port)), 5000);
    },
  };
}

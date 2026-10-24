# desktop

The Mac desktop app: an Electron shell around the console, with no browser chrome.
The spec is `docs/design/review-companion.md` section 11.
On launch it starts the backend and the built console as child processes, waits until both answer, and then opens one window on the console.
On quit it stops both, so nothing stays on ports 8000 or 3000.

## Install

The backend and the console must be installed first (`README.md`, "Getting started").

```
cd frontend && npm install && npm run build
cd desktop && npm install
```

## Run

```
cd desktop && npm run desktop
```

If `frontend/.next` has no build, the app runs `next build` first, which takes about a minute.
After you change the console, rebuild it with `npm run build:console`, or the app keeps serving the old build.
The backend reads the repo-root `.env` as usual, so `AGENT_BACKEND` and `STORE` work the same as in a terminal.
The backend's and the console's output is printed in the terminal that ran `npm run desktop`, as `[backend]` and `[console]` lines.

If the backend or the console does not answer within 30 seconds, or exits, or its port is already in use, the app shows an error window that names which one failed, with its last output.

## Package it as Stochastic.app

```
cd desktop && npm run package   # builds dist/mac-arm64/Stochastic.app, unsigned
npm run open                    # opens it, the same as a double-click in Finder
```

The packaged app shows "Stochastic" in the menu bar, the Dock, and Cmd+Tab.
It does not bundle Python or the console: it runs `backend/` and `frontend/` from this repo, whose path is written into the app at package time.
So package it on the laptop that runs the demo, and package again if the repo moves. `STOCHASTIC_ROOT=/path/to/repo` overrides the path.
Opened from Finder, the app takes its PATH from your login shell, so `node` and `droid` are found the same as in a terminal.
Its output goes to `~/Library/Logs/Stochastic/desktop.log`.
The app is not signed. It opens on the Mac that built it. Copied to another Mac, Gatekeeper will likely block it until you allow it under System Settings, Privacy and Security, Open Anyway (not tried).
You can drag `Stochastic.app` into `/Applications`.

## Dev mode

```
cd frontend && npm run dev          # terminal 1, with the backend running in another
cd desktop && npm run desktop:dev   # terminal 2
```

`STOCHASTIC_DEV=1` loads `http://localhost:3000` from the running `next dev`, so hot reload works, and starts nothing.
Quitting in dev mode stops nothing either.

## Quit cleanly

Quit with Cmd+Q, by closing the window, or with Ctrl+C in the terminal.
Each one stops the backend and the console before the app exits.
Check with `lsof -nP -iTCP:8000 -iTCP:3000 -sTCP:LISTEN`, which should print nothing.
If the app is force-killed (Activity Monitor, `kill -9`), the children can stay behind; stop them with `pkill -f "uvicorn app.main"` and `pkill -f "next start"`.

## What the page gets

`preload.js` exposes `window.stochastic` through `contextBridge`.
The page has no Node access: `contextIsolation` is on, `nodeIntegration` is off, and the renderer is sandboxed.

- `isDesktop: true`, so the console can tell it is in the app.
- `saveFiles([{ url, name }])`: asks for a folder, downloads each file from the API (an absolute URL, or a path relative to `NEXT_PUBLIC_API_URL`), writes it there, and shows it in Finder.
  It resolves to `{ canceled, folder, files }` and rejects if a download fails.
  It only downloads from the API's origin, and it keeps only the base name of each `name`.

Links to other sites open in the default browser, not in the app window.

## Known limits

- Run from source (`npm run desktop`), the bold app name in the menu bar and the Dock label say "Electron", because they come from Electron's own app bundle. Use the packaged app for the demo.
- The app icon is used when `desktop/assets/icon.png` exists (Josie's mark, at least 512 by 512). Until then the Dock shows Electron's icon. Package again after adding it.

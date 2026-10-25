# e2e

End-to-end tests over the whole demo path, in the browser and in the Mac app, with Playwright Test.
They drive the real console against the real gateway API, with no live model.
Every backend the suite starts has `AGENT_BACKEND=scripted`, `AGENT_FALLBACK=scripted`, `STORE=memory`, and empty API keys.
A run at pace `demo` or `factory` replays the recorded Claude Haiku 5.5 run (`backend/recordings/haiku-5-5-run2/`) whatever `AGENT_BACKEND` says, so `demo-run.spec.ts` and `factory-upload.spec.ts` show the recorded run; every other run is scripted.

## Run

The backend and the desktop app must be installed first (`README.md`, "Getting started", and `desktop/README.md`).
The suite looks for the backend's Python at `backend/.venv/bin/python`; set `E2E_PYTHON` to use another one.

```
cd frontend && npm ci
cd desktop && npm ci
cd e2e && npm ci
npm run e2e              # everything: the browser specs, then the Mac app
npm run e2e:browser      # only the browser specs
npm run e2e:electron     # only the Mac app
npm run report           # the HTML report of the last run
```

Playwright 1.63.0 uses Chromium 1243.
If it is not in `~/Library/Caches/ms-playwright`, run `npx playwright install chromium` once.

## How it runs

- The config picks three free ports at the start of each run (never 8000 or 3000, which the installed app uses): the backend, the console, and the Mac app's console.
  `E2E_BACKEND_PORT`, `E2E_CONSOLE_PORT` and `E2E_APP_CONSOLE_PORT` fix them.
- The console is built for the run's backend port into `frontend/.next-e2e` (`NEXT_DIST_DIR`, about 10 seconds), so `frontend/.next`, which the Mac app serves, is never touched.
  It is served with `next start`.
- Every browser test starts its own backend (uvicorn) on a freshly seeded deal and stops it after the test, so no test sees another's state.
  The backend port is baked into the console build, so the tests run one at a time.
- The `fast` project runs the backend with no pacing; the `paced` project runs it with `DEMO_PACE=1`, as on stage.
- The `electron` project launches `desktop/main.js` through Playwright's Electron driver.
  The app starts its own backend and console from this checkout, as the packaged app does.
  `STOCHASTIC_USER_DATA` gives it its own profile, so it runs while the installed Stochastic.app is open.
  The folder dialog and Finder are stubbed in the main process; the download and the file writes are the app's own.
- Every wait is on something the screen or the API shows.
  There are no fixed sleeps.

## The specs

| Spec | Project | What it covers |
| --- | --- | --- |
| `demo-path.spec.ts` | paced | The splash (mark and name, centered, until the deal is read), the Dashboard (no Begin), the demo deal's Case and Run the deal, the live pipeline with no conversation on the Case, Mapping filling line by line, the 3D house with the Mapper asking, both flags answered, the agents resuming, the Reviewer's hand-off, the clean Case (the four figure tiles, no verdict sentence, no "Download final files", the combined books hidden until Show combined books, which shows and hides them), the Agents rows and timeline and the Log drawing every agent character from its one `/v3/agent-*.png` file (the Mapper the teal star, none through `/_next/image`), the Log (audit rows and the Conversation view), Review (the sidebar in its order, the two tabs, no sideways scroll, Back to case and back): Nu Aire General and Administrative 6,163 to 5,663, the verdict 0.76x to 0.75x, the Reviewer gliding to the cell, 1 and Enter, the learned note, Edits 1, Approve, Download final files. It opens the workbook (one amber cell with its note, an Edits row) and the certificate. One screenshot per step. |
| `review-branches.spec.ts` | fast | Later and the companion's waiting dot that reopens the bubble; a remap (Nu Aire Research and Development to Cost of products sold: target Gross profit 23,150, combined Gross profit down 532, Operating profit and leverage unchanged, the mapping rule learned); the same remap from the Mapping tab (the two tabs, the Reviewer at the row, Your edits, approval waiting, Back to case); a large change that asks first ("Change it", then "Yes, save it"); Undo. |
| `demo-run.spec.ts` | fast | The Dashboard's five cases (stage, Sample data and its note, the stat cards), each opened on Case, Mapping, Log, Review, and the Review Mapping tab; then Run the demo from another case (`fromAgreement`: the demo deal starts from its agreement, D23): the verification card at 22 of 22 checks within 10 s, the 22 checks listed, Approve the Brief and map, then the Mapper's one notification ("The Mapper needs 2 decisions") within 8 s of the approval, the Case badge, Decide focusing the flag card, each option's effect and "What happens next", the Learned note and the Policies pulse, the model card "Claude Haiku 5.5, recorded run", the Edits counter at 4 across the seeded cases and 5 after the demo's edit, Ready within 12 s of the last answer, the clean Case, Review with Back to case, an amount edit and a Mapping-tab remap with their reasons, approval, and the two files. It asks for `"pace": "demo"` and skips on a backend without the demo contract (`GET /deals` with five rows and `data_source`). |
| `second-run.spec.ts` | fast | After an approval, "Run it again with what was learned": no questions, the Learned chip on the Mapping tile, the lines placed by policy. Then "Fresh deal (clear memory)": no policies, and the next run asks again. |
| `agreement.spec.ts` | fast | Upload of the two demo CSVs (written from the backend fixture) and `backend/tests/fixtures/kewaunee_ex101_excerpt.txt`; the Brief card with the verification card (22 of 22); five amount questions (the second covenant is noted on the report, not asked); three add-back amounts entered with their source and two kept at 0; the Brief approved; then map, flags, the hand-off and the clean Case, review, approval. Begin in the Upload modal must send `{"sync": false, "pace": "factory"}`. (`watchRunBody` in `support/flows.ts`); Begin also resets with memory cleared first. |
| `reload-replay.spec.ts` | paced | On the Log's Conversation view (the Case no longer shows the conversation), a reload in the middle of the run brings back every line in order, and the page keeps following the run to the Mapper's question. |
| `agents-3d.spec.ts` | paced | The WebGL canvas draws a real picture (a pixel check, with `--use-angle=swiftshader`), the agents' states follow the run, notes fly between rooms (`data-notes-sent`, and `data-notes-in-flight` recorded by a MutationObserver in the page, since a note is in the air for under a second), and the page requests nothing outside localhost. The answers go to the gateway's API while the house stays open, so the hand-offs after them always play live. |
| `factory-upload.spec.ts` | fast | The Factory beat: no Begin on the Dashboard; Upload with the demo deal's two CSVs and its Brief as JSON; Begin sends `{"sync": false, "pace": "factory"}` after a fresh reset; the recorded Claude Haiku 5.5 run asks its two questions and the model card says "Claude Haiku 5.5, recorded run"; both answered; the hand-off and the clean Case. |
| `electron.spec.ts` | electron | The splash window first (360 by 420, frameless, transparent, the mark and the name), the main window shown only after the backend answers and the console has read the deal, and not before 2.1 s; a shortened demo path in the app; Download final files through `window.stochastic.saveFiles` (the workbook with its amber cell and the certificate written to the chosen folder); and a quit that leaves nothing listening on the app's ports. |

The Dashboard has no Begin: `begin()` in `support/flows.ts` opens the demo deal's row and presses the Case's Run the deal, which runs at the backend's `DEMO_PACE` as Begin did.

## Timings

Measured on 2026-10-24 on an Apple Silicon Mac, the last three of six green runs in a row: 3.0, 2.9 and 2.8 minutes for the whole suite, including the console build (about 10 seconds).
On 2026-10-25, with the demo run and the Mapping tab added, two green runs in a row took 3.8 and 3.9 minutes.

| Spec | Time per run |
| --- | --- |
| `agreement.spec.ts` | 4.5 s |
| `review-branches.spec.ts` | 4 to 6 s per test, 5 tests |
| `demo-run.spec.ts` | 7 s (the five cases) and 21 s (the demo, at pace demo) |
| `second-run.spec.ts` | 4.6 s |
| `agents-3d.spec.ts` | 54 s (paced) |
| `demo-path.spec.ts` | 51 s (paced) |
| `reload-replay.spec.ts` | 26 s (paced) |
| `electron.spec.ts` | 5 s |

On a failure the backend fixture sends the backend SIGABRT first (`PYTHONFAULTHANDLER=1`), so its log in `artifacts/logs/` ends with every Python thread's stack.

## Output

Everything goes to `e2e/artifacts/` (git-ignored):

- `screenshots/<spec>/<test>/NN-step.png`: one per step; `screenshots/electron/` for the app.
- `logs/`: each test's backend output.
- `report/`: the HTML report.
  `test-results/`: traces, failure screenshots, and the downloaded files.

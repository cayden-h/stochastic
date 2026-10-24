# Stage shortcuts. Source it once per terminal: `source scripts/demo.sh` from the repo root.
# API is the gateway the console talks to; change it if the API runs on another port.
API="${API:-http://localhost:8000}"
DEAL="${DEAL:-d_kequ_nuaire}"

# Between judges: a fresh deal with memory cleared, so the next judge sees the flag. Refused (409) during a run.
demo_fresh() { curl -s -X POST "$API/dev/reset?keep_memory=false"; echo; }
# The second-run moment: reset but keep what was learned.
demo_again() { curl -s -X POST "$API/dev/reset?keep_memory=true"; echo; }
# Run the deal on one backend without editing .env or restarting: scripted, replay, droid.
demo_run() { curl -s -X POST "$API/deals/$DEAL/run" -H 'Content-Type: application/json' -d "{\"backend\": \"${1:-droid}\"}"; echo; }
demo_scripted() { demo_run scripted; }
demo_replay() { demo_run replay; }
# What the badge reads: store, forks, backend, last runs, credits.
demo_health() { curl -s "$API/health" | python3 -m json.tool | head -60; }

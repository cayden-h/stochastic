# scripts

Helper scripts. Owner: Eric (data pulls) and Cayden (agent probes).

| Script | What it does |
| --- | --- |
| `droid_probe.py` | Lists the models our Factory key can run and makes one `run()` call with structured output in an empty directory. Answers "can Droid run Claude?" |
| `record_run.py` | Runs the whole deal on a chosen backend and saves each agent's output to `backend/recordings/`, the replay fallback for the demo. |

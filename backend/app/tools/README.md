# tools

Pure functions in `finance.py`: `consolidate`, `tie_out`, `ebitda`, `covenant_debt`, `leverage`, `limit_test`.
The same inputs give the same result.
The gateway wraps every call in a `ToolRun` with a run id, so every number on screen traces to one call.
Tools have no write access and never see a model.
The EBITDA and debt definitions come from the deal's `Brief`, never from the code.
Owner: Tri. Cayden wrote the first version so the agents had something to call.

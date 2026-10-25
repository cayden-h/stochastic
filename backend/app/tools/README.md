# tools

Pure functions in `finance.py`: `consolidate`, `tie_out`, `ebitda`, `covenant_debt`, `leverage`, `limit_test`.
`edits.py` applies the controller's amount edits and remaps to the lines first, and rolls the change up into every subtotal that the edited line feeds.
The same inputs give the same result.
The gateway wraps every call in a `ToolRun` with a run id, so every number on screen traces to one call.
Tools have no write access and never see a model.
The EBITDA and debt definitions come from the deal's `Brief`, never from the code.
Owner: Tri.
Cayden wrote the first version so the agents had something to call.
`gl_detail.py` makes simulated account-level detail under each statement line for the Review page (`GET /deals/{id}/gl`).
It is display data, labeled simulated, seeded from the line names, and sums exactly to each filed line; it is not a gateway tool and no deal math reads it.

# api

HTTP routes in `routes.py`, the event stream in `events.py`, the final workbook in `export.py`, and the certificate in `certificate.py`.
Each route validates input and calls the gateway.
No business rules live here.
The console reads `GET /deals/{id}/case` for each screen, follows a run on `GET /deals/{id}/stream` (audit rows, stages, and the live `conversation`, `mapping`, and `notify` events), and reads `GET /health` for the model card and the cross-deal counters (`memory_counts`, the same as `GET /memory/counts`).
It writes through `POST /deals` (the upload), `POST /deals/{id}/run`, the Brief routes (`/brief/amounts`, `/brief/approve`), the work-item routes (`answer`, `hold`, `approve`, `reject`), the edit routes (`POST /deals/{id}/edits`, `POST /edits/{id}/reason`, `DELETE /edits/{id}`), and `POST /dev/reset`.
See `docs/architecture/gateway-and-api.md` for the route list and the JSON shapes.

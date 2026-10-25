# api

HTTP routes in `routes.py`.
Each route validates input and calls the gateway.
No business rules live here.
The console reads `GET /deals/{id}/case` for the whole screen and writes through `POST /deals/{id}/run`, `/work-items/{id}/answer`, and `/work-items/{id}/approve`.
See `docs/architecture/gateway-and-api.md` for the route list and the JSON shapes.

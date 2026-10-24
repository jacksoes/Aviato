# Travel Agent Backend

A Django API starter configured to connect to a local MongoDB server through MongoDB's official Django database backend.

## Requirements

- Python 3.10 or newer
- MongoDB running locally on `127.0.0.1:27017` (the default)

## Run locally (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000/`. Check the server and MongoDB connection at `http://127.0.0.1:8000/api/health/`.

By default, the server connects to `mongodb://127.0.0.1:27017` and uses the `viato` database. Set `MONGODB_URI` and `MONGODB_NAME` in `.env` to use a different local URI or database. For a MongoDB instance that requires authentication, put the credentials in the URI and URL-encode special characters in the username or password.

Flight lookup uses Aviationstack. Set `AVIATIONSTACK_API_KEY` in the backend `.env`; the browser calls Django and never receives this key. The endpoint accepts either `{"flightNumber":"B6 1023","departure":"JFK","arrival":"LAX","date":"2026-10-26"}` or `{"departure":"JFK","arrival":"LAX","date":"2026-10-26"}` at `POST /api/flights/lookup/`. Route lookup expects airport codes (IATA or ICAO). The Free plan supports real-time flights and 100 requests per month; future and historical schedule lookups require a paid plan, so the default October 26, 2026 flight needs an eligible schedule plan until that date is current. See [Aviationstack plans](https://aviationstack.com/pricing).

`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, and `DJANGO_ALLOWED_HOSTS` are also read from `.env`. Keep `.env` private; `.env.example` contains development defaults only.

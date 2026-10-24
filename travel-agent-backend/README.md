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

By default, the server connects to `mongodb://127.0.0.1:27017` and uses the `travel_agent` database. Set `MONGODB_URI` and `MONGODB_NAME` in `.env` to use a different local URI or database. For a MongoDB instance that requires authentication, put the credentials in the URI and URL-encode special characters in the username or password.

`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, and `DJANGO_ALLOWED_HOSTS` are also read from `.env`. Keep `.env` private; `.env.example` contains development defaults only.

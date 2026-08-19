# Deployment — FastAPI backend (Phase 10)

Single-service deploy. No Redis, Celery, or Kubernetes. Frontend and ML training are out of scope.

YAML agronomy files live at **repository root** (`agronomy/`, `data/`). Deploy the **full repo**, not `backend/` alone.

## Startup

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Local Windows PowerShell:

```powershell
cd backend
$env:PORT = "8000"
uvicorn app.main:app --host 0.0.0.0 --port $env:PORT
```

Health check: `GET /api/v1/health`

## Environment

| Variable | Production | Local fallback |
|---|---|---|
| `APP_ENV` | `production` | `development` |
| `DATABASE_URL` | `postgresql+asyncpg://USER:PASSWORD@HOST:5432/DB` | `sqlite+aiosqlite:///./fertilizer_rec_dev.db` |
| `SECRET_KEY` | strong random value (required in production) | placeholder rejected if `APP_ENV=production` |
| `ML_ENABLED` | `false` | `false` |
| `CORS_ORIGINS` | comma-separated frontend origins | localhost Vite/React ports |
| `PORT` | injected by host | `8000` |
| `LOG_LEVEL` | `INFO` | `INFO` |

Never commit `.env`. Copy `backend/.env.example`.

SHC and DigiLocker adapters remain **mocks** (`is_mock: true`). They are not live government APIs.

## Docker

From repository root:

```bash
docker build -t fertilizer-rec-api .
docker run --rm -p 8000:8000 \
  -e APP_ENV=production \
  -e SECRET_KEY=replace-with-strong-random \
  -e ML_ENABLED=false \
  -e DATABASE_URL=sqlite+aiosqlite:///./fertilizer_rec_dev.db \
  fertilizer-rec-api
```

PostgreSQL is supported when `DATABASE_URL` uses `postgresql+asyncpg://`. Do not claim PostGIS is live unless a PostgreSQL+PostGIS instance is actually reachable. Alembic revision `001` creates the PostGIS geometry column only on PostgreSQL.

## Render (or equivalent PaaS)

1. Create a Python web service from this Git repository (root directory = repo root).
2. Build: `pip install -r backend/requirements.txt`
3. Pre-deploy: `cd backend && alembic upgrade head`
4. Start: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Health: `/api/v1/health`
6. Set `DATABASE_URL`, `SECRET_KEY`, `APP_ENV=production`, `ML_ENABLED=false`, `CORS_ORIGINS`.

`render.yaml` at the repo root encodes the same service. You still must attach a Postgres instance (or accept SQLite, which is not durable on most PaaS filesystems).

## Remaining manual step if you cannot log into a host

Create the web service in Render/Railway/Fly, set the env vars above, attach PostgreSQL if required, and deploy. No public URL exists until that account step is done.

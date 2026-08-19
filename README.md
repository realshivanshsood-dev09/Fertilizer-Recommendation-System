# SIH 2026 — Fertilizer Recommendation System
### Malwa Region, Punjab | Adaptive Precision Agriculture

> **Status**: Phase 10 — FastAPI backend ready for single-service deploy. ML disabled. Frontend excluded.
> **Crops**: Wheat · Rice live STCR · Cotton placeholder
> **Districts**: Bathinda · Mansa · Muktsar · Moga · Faridkot
> **Integrations**: Soil Health Card and DigiLocker adapters are **mocks** (`is_mock: true`)

---

## Architecture Overview

```
Farmer Input
  → Soil-Data Resolver
  → Soil Profile
  → STCR Baseline          ← agronomic science layer
  → ML Correction           ← tabular ML layer (residual/correction only)
  → Final N/P/K Recommendation
  → Fertilizer-Product Translation
  → Biofertilizer Recommendation
  → Cost Estimate
  → Application Timing
  → Explanation (SHAP-backed)
```

## Directory Layout

```
fertilizer_rec/
├── backend/          FastAPI application
├── ml/               ML training pipeline
├── agronomy/         STCR equations + biofertilizer logic
├── data/             Raw soil / weather / agronomy data (placeholders)
├── frontend/         React PWA (future)
├── docs/             Science notes + dataset requirements
└── scripts/          Dev / CI utilities
```

## Quick Start (development)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# API docs: http://localhost:8000/docs
# Health: GET http://localhost:8000/api/v1/health
```

SQLite is the local default. PostgreSQL is selected by setting `DATABASE_URL=postgresql+asyncpg://...`.

## Production (single service)

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

See [`docs/deployment.md`](docs/deployment.md). Deploy the **full repository** (YAML data lives outside `backend/`).

## Scientific Status

See [`docs/science_status.md`](docs/science_status.md) for a complete list of:
- What is real vs. placeholder
- STCR data still required
- Dataset requirements for ML training

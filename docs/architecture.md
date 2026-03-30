# Architecture

## System Overview

RetailPulse is a full-stack demand intelligence platform with four main layers:

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                     │
│  Dashboard | Forecasts | Anomalies | Insights | Chat     │
├─────────────────────────────────────────────────────────┤
│                    API Layer (FastAPI)                    │
│  REST endpoints | Model serving | Chat (Claude tools)    │
├──────────────────┬──────────────────────────────────────┤
│   ML Pipeline    │         ETL Pipelines                 │
│  XGBoost model   │  Weather | Holidays | Seed            │
│  Feature eng.    │  Data generators                      │
│  Anomaly detect  │                                       │
├──────────────────┴──────────────────────────────────────┤
│                  PostgreSQL 16                            │
│  8 tables: stores, categories, products, transactions,   │
│  weather_daily, holidays, events, daily_aggregates       │
└─────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Seed pipeline** generates synthetic retail data and fetches real Canadian holidays
2. **Feature builder** joins aggregates + weather + holidays + events into a 30-feature matrix
3. **XGBoost model** trains on the feature matrix with chronological split
4. **API** loads the trained model at startup and serves predictions
5. **Dashboard** fetches from the API and renders charts
6. **Chat** uses Claude API with tool use to query the database and synthesize answers

## Key Design Decisions

### Shared ORM Models (`data/scripts/db/`)
The SQLAlchemy models live in `data/scripts/db/` rather than inside `api/` because they're imported by three modules: data generators, ETL pipelines, and the API layer. This avoids duplicating table definitions.

### Sync vs Async Database
- **Sync** (psycopg2): Used by data generators, ETL pipelines, ML training, and the chat service. These are batch operations that don't benefit from async.
- **Async** (asyncpg): Used by FastAPI endpoints. Async sessions allow the API to handle concurrent requests efficiently.

### Synthetic + Real Data
Historical weather is synthetic (sinusoidal temperature models with noise) because OpenWeatherMap's free tier doesn't include historical data. Holidays are real, fetched from the Nager.Date API. This hybrid approach is documented and explainable.

### Feature Engineering in Python (not SQL)
Features are built in pandas rather than SQL views. This keeps the feature logic co-located with the ML code and makes it easier to test and iterate on features.

### Claude Tool Use for Chat
The chat endpoint doesn't let Claude generate data. It provides 8 tightly-scoped tools that query the real database. Claude calls these tools, receives JSON results, and synthesizes a natural language answer. This ensures all responses are grounded in actual data.

## Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Database | PostgreSQL 16 | Robust, good for time-series queries, standard in production |
| ORM | SQLAlchemy 2.0 | Type-safe Mapped columns, async support, widely adopted |
| API | FastAPI | Auto-generated OpenAPI docs, async support, Pydantic integration |
| ML | XGBoost | Best-in-class for tabular data, fast training, feature importance |
| Frontend | Next.js 14 | App Router for modern React patterns, TypeScript, SSR capable |
| Charts | Recharts | React-native charting, simpler API than D3 |
| Chat | Claude API | Superior tool use / structured output vs alternatives |
| Infrastructure | Docker Compose | Single-command deployment, service orchestration |

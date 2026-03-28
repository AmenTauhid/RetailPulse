# RetailPulse - AI-Powered Retail Demand Intelligence Platform

## WHY

RetailPulse is a portfolio project that mirrors Canadian Tire's MOSaiC retail intelligence platform. It combines synthetic retail transaction data with real external signals (weather, holidays, local events) to predict demand patterns and surface actionable insights for retail decision-making. The goal is to demonstrate end-to-end ownership of an AI-powered data product: ingestion, modeling, serving, and a polished user-facing application.

This project exists to be demo-ready for interviews. Every feature should be something I can walk through live and explain the reasoning behind.

## WHAT

### Architecture

```
retailpulse/
├── CLAUDE.md
├── docker-compose.yml
├── .github/
│   └── workflows/          # GitHub Actions CI/CD
├── data/
│   ├── scripts/            # Data generation and seeding scripts
│   └── sample/             # Sample datasets for dev/testing
├── etl/
│   ├── pipelines/          # ETL pipeline modules
│   ├── schedulers/         # Automated scheduling (cron/Azure Functions)
│   └── tests/
├── ml/
│   ├── features/           # Feature engineering modules
│   ├── models/             # Model training and evaluation
│   ├── serving/            # Model serving and prediction API
│   └── tests/
├── api/
│   ├── app/                # FastAPI application
│   │   ├── routers/        # API route handlers
│   │   ├── services/       # Business logic layer
│   │   ├── models/         # Pydantic schemas
│   │   └── core/           # Config, auth, middleware
│   └── tests/
├── web/
│   ├── src/
│   │   ├── app/            # Next.js App Router pages
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── lib/            # Utilities, API client, types
│   │   └── styles/         # Tailwind config and globals
│   └── tests/
└── docs/
    ├── architecture.md
    ├── api-spec.md
    └── data-dictionary.md
```

### Tech Stack

- **Data & ML:** Python 3.11+, pandas, scikit-learn, XGBoost, Prophet, PyTorch (if LSTM needed)
- **Backend API:** FastAPI, Pydantic, SQLAlchemy, Alembic (migrations)
- **Database:** PostgreSQL 16
- **Frontend:** React 19, Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts
- **AI Chat Layer:** Google Gemini API or Anthropic Claude API for conversational insights
- **External APIs:** OpenWeatherMap, public holidays API (Nager.Date), Ticketmaster/Eventbrite
- **Infrastructure:** Docker, Docker Compose, GitHub Actions CI/CD
- **Cloud (deployment target):** Azure (App Service, Azure Functions, Azure Database for PostgreSQL)

### Key Modules

- **ETL pipelines:** Ingest and normalize synthetic retail data + external signals into PostgreSQL. Scheduled via cron or Azure Functions.
- **Feature engineering:** Transform raw data into ML-ready features. Weather impact encoding, holiday proximity, event density, day-of-week/seasonality features, rolling sales averages.
- **Demand forecasting models:** XGBoost for tabular demand prediction. Prophet or LSTM for time-series forecasting. Anomaly detection for unexpected demand spikes/drops.
- **Prediction API:** FastAPI endpoints serving model predictions, historical data, and anomaly alerts.
- **Dashboard:** Next.js app with demand forecast visualizations by product category and location, alert panels for predicted demand shifts, and drill-down into the "why" behind forecasts.
- **Conversational AI:** A chat interface where users ask natural language questions like "What should I stock more of this weekend?" and get answers grounded in the actual data and model outputs.
- **Automated reporting:** Weekly demand summary generation and export (similar to SheetJS export pattern).

## HOW

### Environment Setup

```bash
# Clone and setup
git clone <repo-url> && cd retailpulse
cp .env.example .env  # Fill in API keys

# Start all services
docker-compose up -d

# Backend
cd api && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd web && npm install && npm run dev

# Run ETL seed
cd etl && python -m pipelines.seed
```

### Commands

```bash
# Tests
cd api && pytest                          # Backend tests
cd web && npm test                        # Frontend tests
cd ml && pytest                           # ML pipeline tests

# Linting and formatting
ruff check .                              # Python linting
ruff format .                             # Python formatting
cd web && npx eslint . && npx prettier --check .  # Frontend

# Type checking
cd web && npx tsc --noEmit

# Database migrations
cd api && alembic upgrade head            # Apply migrations
cd api && alembic revision --autogenerate -m "description"  # New migration

# ML training
cd ml && python -m models.train --config configs/xgboost.yaml
cd ml && python -m models.evaluate --model-path outputs/latest
```

### Development Conventions

- Python: Use type hints everywhere. Google-style docstrings. snake_case for variables and functions.
- TypeScript: Strict mode enabled. Functional components only. Props interfaces defined in the component file.
- API routes follow REST conventions. All endpoints return Pydantic models. Error responses use a consistent `{detail: string, status_code: int}` shape.
- Every new feature gets a test. Backend uses pytest with fixtures. Frontend uses Jest + React Testing Library.
- Git commits use conventional commits format: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
- Branch naming: `feat/short-description`, `fix/short-description`.
- Never commit API keys or secrets. All sensitive config goes in `.env` and is loaded via `pydantic-settings`.

### Important Gotchas

- The OpenWeatherMap free tier is limited to 60 calls/minute. The ETL pipeline should cache weather data aggressively and batch requests.
- Prophet requires pystan. On some systems this needs a C++ compiler. The Dockerfile handles this, but local dev on Windows may need extra setup.
- The conversational AI layer should never hallucinate data. It must be grounded in actual model outputs and database queries. If the model does not have data for a question, it should say so.
- PostgreSQL connection pooling: use SQLAlchemy async sessions with a pool size of 5 for dev, configurable via env vars.
- Next.js App Router: do not use the Pages Router. All routing goes through `app/` directory.
- Recharts is the charting library. Do not install Chart.js or D3 unless there is a specific need Recharts cannot handle.

### Build Phases

This project is built incrementally. Each phase should be fully working and testable before moving to the next.

**Phase 1 - Data Foundation:**
Set up PostgreSQL schema, generate synthetic retail data (products, stores, transactions), build ETL pipeline for weather and holiday data, seed the database.

**Phase 2 - Feature Engineering & Models:**
Build feature engineering pipeline, train XGBoost demand forecasting model, evaluate and iterate. Add Prophet for time-series comparison.

**Phase 3 - API Layer:**
FastAPI app serving predictions, historical data, and anomaly alerts. JWT auth if needed. Full test coverage.

**Phase 4 - Dashboard:**
Next.js dashboard with forecast visualizations, anomaly alerts, and drill-down views. Connect to API. Responsive design.

**Phase 5 - Conversational AI:**
Chat interface backed by Gemini or Claude API. Grounded in real data. Natural language queries produce data-backed answers.

**Phase 6 - Automation & DevOps:**
Dockerize everything. GitHub Actions CI/CD. Automated model retraining pipeline. Weekly report generation. Azure deployment.

**Phase 7 - Polish:**
Documentation, demo script, edge case handling, performance optimization, README with screenshots.

# RetailPulse

AI-powered retail demand intelligence platform that combines synthetic retail transaction data with real external signals (weather, holidays, local events) to predict demand patterns and surface actionable insights.

Built as a full-stack data product: data generation, ETL pipelines, ML forecasting, REST API, and interactive dashboard.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Next.js    │────▶│   FastAPI    │────▶│  PostgreSQL  │
│  Dashboard   │     │   REST API   │     │   Database   │
└──────────────┘     └──────┬───────┘     └──────▲───────┘
                            │                     │
                     ┌──────▼───────┐     ┌───────┴──────┐
                     │   XGBoost    │     │     ETL      │
                     │    Model     │     │  Pipelines   │
                     └──────────────┘     └──────────────┘
```

| Layer | Tech |
|-------|------|
| **Database** | PostgreSQL 16 |
| **Data & ETL** | Python, pandas, SQLAlchemy, Faker |
| **ML** | XGBoost, scikit-learn |
| **API** | FastAPI, Pydantic, async SQLAlchemy |
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, Recharts |
| **External APIs** | Nager.Date (holidays), OpenWeatherMap (weather) |
| **Infrastructure** | Docker Compose |

## Features

- **Synthetic data generation** — 10 Canadian retail stores, 14 product categories, 56 SKUs, ~139K transactions with realistic seasonal/weather/holiday demand patterns
- **Real external data** — Canadian public holidays fetched from Nager.Date API, weather pipeline for OpenWeatherMap
- **30-feature ML pipeline** — temporal, weather, holiday proximity, event density, and lag features
- **XGBoost demand forecasting** — R² = 0.75, with feature importance and confidence intervals
- **Anomaly detection** — Z-score and Isolation Forest on prediction residuals
- **REST API** — 9 endpoints serving forecasts, historical data, anomalies, and insights
- **Interactive dashboard** — KPI overview, demand forecast charts, anomaly feed, weather-impact analysis

## Quick Start

### Prerequisites

- Docker (for PostgreSQL)
- Python 3.11+
- Node.js 18+

### 1. Setup

```bash
git clone <repo-url> && cd RetailPulse
cp .env.example .env

# Start PostgreSQL
docker compose up -d

# Install Python dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r data/scripts/requirements.txt -r api/requirements.txt -r ml/requirements.txt
```

### 2. Seed the Database

```bash
PYTHONPATH=. python -m etl.pipelines.seed
```

This creates all tables, generates synthetic data, and fetches real Canadian holidays. Takes ~20 seconds.

```
stores               10 rows
categories           14 rows
products             56 rows
weather_daily        7,310 rows
events               388 rows
holidays             106 rows    (real, from Nager.Date API)
transactions         139,140 rows
daily_aggregates     69,472 rows
```

### 3. Train the ML Model

```bash
PYTHONPATH=. python -m ml.models.train
```

Builds features, trains XGBoost, and runs anomaly detection. Model artifacts are saved to `ml/outputs/`.

### 4. Start the API

```bash
PYTHONPATH=. uvicorn api.app.main:app --reload --port 8000
```

Swagger docs at [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Start the Dashboard

```bash
cd web && npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check and model status |
| GET | `/api/v1/stores` | List all 10 stores |
| GET | `/api/v1/categories` | List all 14 product categories |
| GET | `/api/v1/historical/{store_id}/{category_id}` | Daily demand time series |
| GET | `/api/v1/forecasts/{store_id}/{category_id}` | Demand forecast with confidence intervals |
| GET | `/api/v1/anomalies` | Demand anomalies with severity scores |
| GET | `/api/v1/weather/{store_id}` | Weather data per store |
| GET | `/api/v1/insights/top-movers` | Biggest demand changes vs prior period |
| GET | `/api/v1/insights/weather-impact` | Temperature-demand correlation |
| GET | `/api/v1/model/info` | Model metrics and feature importance |

## Dashboard Pages

- **Dashboard** (`/`) — KPI cards, feature importance chart, top movers
- **Forecasts** (`/forecasts`) — Historical + predicted demand with confidence bands, store/category selectors
- **Anomalies** (`/anomalies`) — Filterable anomaly feed with severity badges
- **Insights** (`/insights`) — Weather-impact chart (Winter Tires vs BBQ by temperature), top gainers/decliners

## Project Structure

```
RetailPulse/
├── data/scripts/          # Synthetic data generators + shared DB models
│   ├── db/                #   SQLAlchemy ORM (8 tables)
│   ├── generate_*.py      #   Stores, products, weather, events, transactions
├── etl/
│   ├── pipelines/         # ETL: holiday (Nager.Date), weather (OpenWeatherMap), seed orchestrator
│   └── tests/             # 30 generator + pipeline tests
├── ml/
│   ├── features/          # 30-feature engineering pipeline
│   ├── models/            # XGBoost, anomaly detection, train/evaluate CLIs
│   ├── configs/           # Model hyperparameters (YAML)
│   └── tests/             # 19 ML tests
├── api/
│   ├── app/               # FastAPI application
│   │   ├── routers/       #   7 route modules
│   │   ├── models/        #   Pydantic schemas
│   │   └── core/          #   Config, async DB
│   └── tests/             # 12 API integration tests
├── web/
│   └── src/
│       ├── app/           # Next.js pages (dashboard, forecasts, anomalies, insights)
│       ├── components/    # Sidebar, charts, selectors, cards
│       └── lib/           # Typed API client, TypeScript interfaces
├── docker-compose.yml     # PostgreSQL 16
└── pyproject.toml         # Ruff + pytest config
```

## Testing

```bash
# All tests (61 total)
PYTHONPATH=. python -m pytest etl/tests/ ml/tests/ api/tests/ -v

# By module
PYTHONPATH=. python -m pytest etl/tests/    # Data generators + ETL pipelines
PYTHONPATH=. python -m pytest ml/tests/     # Feature builder + model + anomaly detection
PYTHONPATH=. python -m pytest api/tests/    # API endpoint integration tests
```

## Data Design

The synthetic transaction data is not random — it encodes real retail demand signals:

- **Seasonal curves** — Winter Tires peak Dec-Jan, BBQ Grills peak Jun-Aug
- **Day-of-week effects** — higher weekend sales, Tuesday dip
- **Holiday spikes** — 3-5x demand around Boxing Day, Canada Day, Labour Day
- **Weather sensitivity** — snow days boost winter products, warm weather boosts outdoor categories
- **Store scaling** — warehouse stores have 1.6x volume, express stores 0.6x
- **Year-over-year trend** — 3% annual growth baked in

This makes the ML model's learned features interpretable: the top features (`is_weekend`, `rolling_7d_qty`, `days_to_christmas`, `is_snow_day`) are exactly the signals embedded in the data.

## License

MIT

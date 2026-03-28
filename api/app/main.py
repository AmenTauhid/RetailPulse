"""FastAPI application entry point."""

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.app.core.config import get_settings
from api.app.routers import anomalies, categories, forecasts, health, historical, insights, stores

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML model on startup, cleanup on shutdown."""
    settings = get_settings()
    model_path = Path(settings.xgboost_model_path)
    metrics_path = Path(settings.xgboost_metrics_path)

    if model_path.exists():
        app.state.model = joblib.load(model_path)
        logger.info("Loaded XGBoost model from %s", model_path)
    else:
        app.state.model = None
        logger.warning("No model found at %s. Forecast endpoints will return errors.", model_path)

    if metrics_path.exists():
        with open(metrics_path) as f:
            app.state.model_meta = json.load(f)
    else:
        app.state.model_meta = {}

    yield

    app.state.model = None
    app.state.model_meta = {}


def create_app() -> FastAPI:
    app = FastAPI(
        title="RetailPulse API",
        description="AI-powered retail demand intelligence platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, tags=["Health"])
    app.include_router(stores.router, prefix="/api/v1", tags=["Stores"])
    app.include_router(categories.router, prefix="/api/v1", tags=["Categories"])
    app.include_router(forecasts.router, prefix="/api/v1", tags=["Forecasts"])
    app.include_router(historical.router, prefix="/api/v1", tags=["Historical"])
    app.include_router(anomalies.router, prefix="/api/v1", tags=["Anomalies"])
    app.include_router(insights.router, prefix="/api/v1", tags=["Insights"])

    return app


app = create_app()

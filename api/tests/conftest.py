"""Test fixtures for API tests."""

import json
from pathlib import Path

import joblib
import pytest
from httpx import ASGITransport, AsyncClient

from api.app.core.config import get_settings
from api.app.core.database import reset_engine
from api.app.main import create_app


@pytest.fixture(autouse=True)
def _reset_db():
    """Reset the DB engine between tests to avoid connection pool conflicts."""
    reset_engine()
    yield
    reset_engine()


@pytest.fixture
async def client():
    """Async test client with model state set."""
    app = create_app()

    settings = get_settings()
    model_path = Path(settings.xgboost_model_path)
    metrics_path = Path(settings.xgboost_metrics_path)

    if model_path.exists():
        app.state.model = joblib.load(model_path)
    else:
        app.state.model = None

    if metrics_path.exists():
        with open(metrics_path) as f:
            app.state.model_meta = json.load(f)
    else:
        app.state.model_meta = {}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

"""Integration tests for API endpoints against the seeded database."""

import pytest

pytestmark = pytest.mark.asyncio


class TestHealth:
    async def test_health_check(self, client):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestStores:
    async def test_list_stores(self, client):
        response = await client.get("/api/v1/stores")
        assert response.status_code == 200
        stores = response.json()
        assert len(stores) == 10
        assert stores[0]["store_code"] == "CTC-001"

    async def test_get_store(self, client):
        response = await client.get("/api/v1/stores/1")
        assert response.status_code == 200
        store = response.json()
        assert store["city"] == "Toronto"

    async def test_get_nonexistent_store(self, client):
        response = await client.get("/api/v1/stores/999")
        assert response.status_code == 404


class TestCategories:
    async def test_list_categories(self, client):
        response = await client.get("/api/v1/categories")
        assert response.status_code == 200
        categories = response.json()
        assert len(categories) == 14
        names = {c["name"] for c in categories}
        assert "Winter Tires" in names
        assert "BBQ Grills & Accessories" in names

    async def test_list_products_by_category(self, client):
        response = await client.get("/api/v1/categories/1/products")
        assert response.status_code == 200
        products = response.json()
        assert len(products) > 0
        for p in products:
            assert p["category_id"] == 1


class TestHistorical:
    async def test_get_historical(self, client):
        response = await client.get(
            "/api/v1/historical/1/1",
            params={"start_date": "2025-01-01", "end_date": "2025-01-31"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["store_id"] == 1
        assert data["category_id"] == 1
        assert len(data["data"]) > 0

    async def test_get_weather(self, client):
        response = await client.get("/api/v1/weather/1", params={"limit": 5})
        assert response.status_code == 200
        weather = response.json()
        assert len(weather) <= 5
        for w in weather:
            assert w["store_id"] == 1


class TestForecasts:
    async def test_get_forecast(self, client):
        response = await client.get("/api/v1/forecasts/1/1", params={"days": 7})
        assert response.status_code == 200
        data = response.json()
        assert data["store_id"] == 1
        assert data["model_type"] == "xgboost"
        assert len(data["forecasts"]) == 7
        for f in data["forecasts"]:
            assert f["predicted_quantity"] >= 0

    async def test_get_model_info(self, client):
        response = await client.get("/api/v1/model/info")
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "feature_importance" in data


class TestInsights:
    async def test_top_movers(self, client):
        response = await client.get("/api/v1/insights/top-movers", params={"days": 14, "limit": 5})
        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 14
        assert len(data["movers"]) <= 5
        for m in data["movers"]:
            assert m["direction"] in ("up", "down")

    async def test_weather_impact(self, client):
        response = await client.get("/api/v1/insights/weather-impact", params={"store_id": 1})
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) > 0
        for d in data["data"]:
            assert d["sample_count"] > 0

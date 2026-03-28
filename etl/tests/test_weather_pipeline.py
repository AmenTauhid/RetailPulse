"""Tests for the weather pipeline."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from data.scripts.db.models import Store
from etl.pipelines.weather_pipeline import fetch_current_weather, parse_weather_response


class TestFetchCurrentWeather:
    @patch("etl.pipelines.weather_pipeline.httpx.get")
    def test_successful_fetch(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "main": {"temp": -5.0, "temp_min": -8.0, "temp_max": -2.0},
            "weather": [{"icon": "13d", "description": "light snow"}],
            "wind": {"speed": 4.5},
            "rain": {},
            "snow": {"1h": 1.2},
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        store = Store(
            id=1,
            store_code="CTC-001",
            name="Test Store",
            city="Toronto",
            province="ON",
            latitude=Decimal("43.7066"),
            longitude=Decimal("-79.3985"),
            store_type="standard",
            opened_date=date(2020, 1, 1),
        )
        result = fetch_current_weather(store, "test_key")
        assert result is not None
        assert result["main"]["temp"] == -5.0

    @patch("etl.pipelines.weather_pipeline.httpx.get")
    def test_handles_api_error(self, mock_get):
        import httpx

        mock_get.side_effect = httpx.HTTPError("API error")

        store = Store(
            id=1,
            store_code="CTC-001",
            name="Test Store",
            city="Toronto",
            province="ON",
            latitude=Decimal("43.7066"),
            longitude=Decimal("-79.3985"),
            store_type="standard",
            opened_date=date(2020, 1, 1),
        )
        result = fetch_current_weather(store, "test_key")
        assert result is None


class TestParseWeatherResponse:
    def test_parses_complete_response(self):
        data = {
            "main": {"temp": -5.0, "temp_min": -8.0, "temp_max": -2.0},
            "weather": [{"icon": "13d", "description": "light snow"}],
            "wind": {"speed": 4.5},
            "rain": {},
            "snow": {"1h": 1.2},
        }

        record = parse_weather_response(data, store_id=1, target_date=date(2024, 1, 15))

        assert record["store_id"] == 1
        assert record["date"] == date(2024, 1, 15)
        assert record["temp_mean_c"] == Decimal("-5.0")
        assert record["temp_high_c"] == Decimal("-2.0")
        assert record["temp_low_c"] == Decimal("-8.0")
        assert record["weather_code"] == "13d"
        assert record["weather_description"] == "light snow"
        # wind: 4.5 m/s × 3.6 = 16.2 km/h
        assert record["wind_speed_kmh"] == Decimal("16.2")

    def test_handles_missing_optional_fields(self):
        data = {
            "main": {"temp": 10.0},
            "weather": [{}],
            "wind": {},
        }

        record = parse_weather_response(data, store_id=1, target_date=date(2024, 6, 15))
        assert record["temp_mean_c"] == Decimal("10.0")
        assert record["precipitation_mm"] == Decimal("0.0")
        assert record["snowfall_cm"] == Decimal("0.0")

"""Fetch current weather data from OpenWeatherMap API.

Used for real-time weather ingestion. Historical data is synthetic (see generate_weather.py).
The free tier allows 60 calls/minute — with 10 stores this is well within limits.
"""

import logging
import time
from datetime import date, datetime, timezone
from decimal import Decimal

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from data.scripts.db.models import Store, WeatherDaily
from etl.pipelines.config import get_settings

logger = logging.getLogger(__name__)

OWM_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"


def fetch_current_weather(store: Store, api_key: str) -> dict | None:
    """Fetch current weather for a store's location from OpenWeatherMap."""
    params = {
        "lat": float(store.latitude),
        "lon": float(store.longitude),
        "appid": api_key,
        "units": "metric",
    }
    try:
        response = httpx.get(OWM_CURRENT_URL, params=params, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error("Failed to fetch weather for store %s: %s", store.store_code, e)
        return None


def parse_weather_response(data: dict, store_id: int, target_date: date) -> dict:
    """Transform OpenWeatherMap API response into a weather_daily record."""
    main = data.get("main", {})
    weather = data.get("weather", [{}])[0]
    wind = data.get("wind", {})
    rain = data.get("rain", {})
    snow = data.get("snow", {})

    temp = main.get("temp", 0)
    temp_min = main.get("temp_min", temp - 3)
    temp_max = main.get("temp_max", temp + 3)

    return {
        "store_id": store_id,
        "date": target_date,
        "temp_high_c": Decimal(str(round(temp_max, 2))),
        "temp_low_c": Decimal(str(round(temp_min, 2))),
        "temp_mean_c": Decimal(str(round(temp, 2))),
        "precipitation_mm": Decimal(str(round(rain.get("1h", 0) + snow.get("1h", 0), 2))),
        "snowfall_cm": Decimal(str(round(snow.get("1h", 0) * 10, 2))),  # mm to cm approx
        "wind_speed_kmh": Decimal(str(round(wind.get("speed", 0) * 3.6, 1))),  # m/s to km/h
        "weather_code": str(weather.get("icon", "")),
        "weather_description": weather.get("description", ""),
        "fetched_at": datetime.now(timezone.utc),
    }


def load_current_weather(session: Session, stores: list[Store]) -> int:
    """Fetch and upsert today's weather for all stores.

    Returns the number of records upserted.
    """
    settings = get_settings()
    api_key = settings.openweathermap_api_key
    if not api_key or api_key == "your_key_here":
        logger.warning("OpenWeatherMap API key not configured. Skipping weather fetch.")
        return 0

    today = date.today()
    count = 0

    for store in stores:
        data = fetch_current_weather(store, api_key)
        if data is None:
            continue

        record = parse_weather_response(data, store.id, today)
        stmt = (
            pg_insert(WeatherDaily)
            .values(**record)
            .on_conflict_do_update(
                constraint="uq_weather_store_date",
                set_={
                    "temp_high_c": record["temp_high_c"],
                    "temp_low_c": record["temp_low_c"],
                    "temp_mean_c": record["temp_mean_c"],
                    "precipitation_mm": record["precipitation_mm"],
                    "snowfall_cm": record["snowfall_cm"],
                    "wind_speed_kmh": record["wind_speed_kmh"],
                    "weather_code": record["weather_code"],
                    "weather_description": record["weather_description"],
                    "fetched_at": record["fetched_at"],
                },
            )
        )
        session.execute(stmt)
        count += 1

        # Rate limiting: stay well under 60 calls/min
        time.sleep(1.0)

    session.commit()
    logger.info("Updated weather for %d stores", count)
    return count

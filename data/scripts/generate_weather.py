"""Generate synthetic weather data with realistic Canadian seasonal patterns."""

import math
import random
from datetime import date, timedelta
from decimal import Decimal

from data.scripts.db.models import Store, WeatherDaily

# City-level climate parameters: (mean_winter_temp_c, mean_summer_temp_c, annual_snowfall_cm)
CITY_CLIMATE: dict[str, tuple[float, float, float]] = {
    "Toronto": (-4.0, 22.0, 108.0),
    "Vancouver": (4.0, 18.0, 38.0),
    "Calgary": (-8.0, 17.0, 128.0),
    "Montreal": (-7.0, 21.0, 150.0),
    "Ottawa": (-9.0, 21.0, 175.0),
}

WEATHER_CONDITIONS = {
    "snow": ("13d", "heavy snow"),
    "light_snow": ("13d", "light snow"),
    "rain": ("10d", "moderate rain"),
    "light_rain": ("10d", "light rain"),
    "cloudy": ("04d", "overcast clouds"),
    "partly_cloudy": ("03d", "scattered clouds"),
    "clear": ("01d", "clear sky"),
}


def _seasonal_temp(day_of_year: int, mean_winter: float, mean_summer: float) -> float:
    """Sinusoidal temperature model. Coldest around Jan 15 (day 15), warmest around Jul 15 (day 196)."""
    amplitude = (mean_summer - mean_winter) / 2
    midpoint = (mean_summer + mean_winter) / 2
    # Shift so minimum is around day 15 (mid-January)
    phase_shift = 15
    return midpoint + amplitude * math.cos(2 * math.pi * (day_of_year - phase_shift - 182) / 365)


def _get_weather_condition(temp_mean: float, precip_mm: float, snow_cm: float) -> tuple[str, str]:
    """Determine weather code and description from conditions."""
    if snow_cm > 5:
        return WEATHER_CONDITIONS["snow"]
    if snow_cm > 0:
        return WEATHER_CONDITIONS["light_snow"]
    if precip_mm > 10:
        return WEATHER_CONDITIONS["rain"]
    if precip_mm > 2:
        return WEATHER_CONDITIONS["light_rain"]
    if random.random() < 0.4:
        return WEATHER_CONDITIONS["cloudy"]
    if random.random() < 0.5:
        return WEATHER_CONDITIONS["partly_cloudy"]
    return WEATHER_CONDITIONS["clear"]


def generate_weather(
    stores: list[Store],
    start_date: date,
    end_date: date,
) -> list[WeatherDaily]:
    """Generate synthetic daily weather records for each store."""
    random.seed(42)
    records: list[WeatherDaily] = []

    for store in stores:
        climate = CITY_CLIMATE.get(store.city, (-5.0, 20.0, 100.0))
        mean_winter, mean_summer, annual_snow = climate

        current = start_date
        while current <= end_date:
            day_of_year = current.timetuple().tm_yday

            # Temperature with noise
            base_temp = _seasonal_temp(day_of_year, mean_winter, mean_summer)
            temp_mean = base_temp + random.gauss(0, 3.0)
            temp_high = temp_mean + random.uniform(2.0, 6.0)
            temp_low = temp_mean - random.uniform(2.0, 6.0)

            # Precipitation — higher in spring/fall
            season_precip_factor = 1.0 + 0.3 * math.sin(2 * math.pi * (day_of_year - 90) / 365)
            precip_chance = 0.30 * season_precip_factor
            precip_mm = 0.0
            snow_cm = 0.0

            if random.random() < precip_chance:
                precip_mm = random.expovariate(1 / 8.0)  # mean ~8mm
                precip_mm = min(precip_mm, 50.0)

                if temp_mean < 0:
                    # Convert to snow (rough 1:10 ratio)
                    snow_cm = precip_mm * random.uniform(0.8, 1.5)
                elif temp_mean < 2:
                    # Mix of rain and snow
                    snow_cm = precip_mm * random.uniform(0.0, 0.5)

            # Wind
            wind_speed = max(0, random.gauss(15, 8))

            code, description = _get_weather_condition(temp_mean, precip_mm, snow_cm)

            records.append(
                WeatherDaily(
                    store_id=store.id,
                    date=current,
                    temp_high_c=Decimal(str(round(temp_high, 2))),
                    temp_low_c=Decimal(str(round(temp_low, 2))),
                    temp_mean_c=Decimal(str(round(temp_mean, 2))),
                    precipitation_mm=Decimal(str(round(precip_mm, 2))),
                    snowfall_cm=Decimal(str(round(snow_cm, 2))),
                    wind_speed_kmh=Decimal(str(round(wind_speed, 1))),
                    weather_code=code,
                    weather_description=description,
                )
            )

            current += timedelta(days=1)

    return records

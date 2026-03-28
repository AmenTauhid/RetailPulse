"""Generate synthetic retail transactions with realistic seasonal and contextual demand patterns.

Demand is modeled as:
    base_demand × seasonal_curve × day_of_week × holiday_effect × weather_effect × store_scale × noise

This produces data where ML models can learn meaningful feature-demand relationships.
"""

import math
import random
from datetime import date, timedelta
from decimal import Decimal

from data.scripts.db.models import (
    Category,
    Holiday,
    Product,
    Store,
    Transaction,
    WeatherDaily,
)

# Base daily demand per product (mean units sold per store per day in neutral conditions)
CATEGORY_BASE_DEMAND: dict[str, float] = {
    "Winter Tires": 1.5,
    "All-Season Tires": 1.0,
    "Snow Blowers": 0.3,
    "BBQ Grills & Accessories": 1.2,
    "Patio Furniture": 0.6,
    "Hockey Equipment": 1.8,
    "Camping Gear": 0.8,
    "Christmas Decor": 1.0,
    "Garden & Lawn": 1.2,
    "Tools & Hardware": 3.0,
    "Paint & Supplies": 2.5,
    "Plumbing": 1.5,
    "Electrical": 2.0,
    "Automotive Accessories": 2.0,
}

# Seasonal curves: (peak_month, amplitude). amplitude=1.0 means demand doubles at peak.
SEASON_PROFILES: dict[str, tuple[int, float]] = {
    "winter": (1, 2.5),  # Peaks January
    "summer": (7, 2.0),  # Peaks July
    "spring": (5, 1.8),  # Peaks May
    "fall": (10, 1.5),  # Peaks October
}

# Day-of-week multipliers (Mon=0 through Sun=6)
DOW_MULTIPLIER = [0.75, 0.70, 0.80, 0.85, 1.05, 1.40, 1.20]

# Store type volume multiplier
STORE_TYPE_SCALE: dict[str, float] = {
    "warehouse": 1.6,
    "standard": 1.0,
    "express": 0.6,
}

# City population scale (relative to Toronto)
CITY_SCALE: dict[str, float] = {
    "Toronto": 1.0,
    "Vancouver": 0.85,
    "Calgary": 0.75,
    "Montreal": 0.90,
    "Ottawa": 0.65,
}


def _seasonal_multiplier(day_of_year: int, peak_month: int, amplitude: float) -> float:
    """Cosine-based seasonal curve peaking at the given month."""
    peak_day = (peak_month - 1) * 30.5 + 15  # Approximate day of year for peak month
    return 1.0 + amplitude * max(0, math.cos(2 * math.pi * (day_of_year - peak_day) / 365))


def _christmas_multiplier(current_date: date) -> float:
    """Special multiplier for the shopping season (Nov 15 - Dec 25)."""
    christmas = date(current_date.year, 12, 25)
    days_to_christmas = (christmas - current_date).days

    if days_to_christmas < 0 or days_to_christmas > 40:
        return 1.0

    # Ramp up to 3x on Boxing Day sales lead-up
    if days_to_christmas <= 5:
        return 2.5 + (5 - days_to_christmas) * 0.3
    if days_to_christmas <= 15:
        return 1.5 + (15 - days_to_christmas) * 0.1
    return 1.0 + (40 - days_to_christmas) * 0.015


def _holiday_multiplier(
    current_date: date,
    holiday_dates: set[date],
) -> float:
    """Boost demand around holidays with exponential decay."""
    multiplier = 1.0
    for hd in holiday_dates:
        days_diff = abs((current_date - hd).days)
        if days_diff == 0:
            multiplier *= 1.8
        elif days_diff <= 3:
            multiplier *= 1.0 + 0.6 * math.exp(-days_diff / 1.5)
        elif days_diff <= 7:
            multiplier *= 1.0 + 0.2 * math.exp(-days_diff / 3.0)
    return min(multiplier, 4.0)  # Cap to avoid extreme values


def _weather_multiplier(
    weather: WeatherDaily | None,
    category: Category,
) -> float:
    """Adjust demand based on weather conditions and product category."""
    if weather is None:
        return 1.0

    temp = float(weather.temp_mean_c) if weather.temp_mean_c else 0.0
    snow = float(weather.snowfall_cm) if weather.snowfall_cm else 0.0
    rain = float(weather.precipitation_mm) if weather.precipitation_mm else 0.0

    peak = category.peak_season
    mult = 1.0

    if peak == "winter":
        # Cold and snow boost winter products
        if temp < -10:
            mult *= 1.5
        elif temp < -5:
            mult *= 1.3
        if snow > 5:
            mult *= 1.6
        elif snow > 0:
            mult *= 1.2
        # Warm weather reduces winter product demand
        if temp > 10:
            mult *= 0.3
        elif temp > 5:
            mult *= 0.5
    elif peak == "summer":
        # Warm sunny weather boosts summer products
        if temp > 25:
            mult *= 1.5
        elif temp > 20:
            mult *= 1.3
        # Cold weather kills summer demand
        if temp < 5:
            mult *= 0.2
        elif temp < 10:
            mult *= 0.4
        # Rain dampens outdoor purchases
        if rain > 10:
            mult *= 0.7
    elif peak == "spring":
        if 10 < temp < 20:
            mult *= 1.3
        if temp < 0:
            mult *= 0.4
    elif peak == "fall":
        if 5 < temp < 15:
            mult *= 1.2
    else:
        # Non-seasonal: extreme weather slightly reduces foot traffic
        if snow > 10 or temp < -20 or rain > 20:
            mult *= 0.8

    return mult


def generate_transactions(
    stores: list[Store],
    products: list[Product],
    categories: list[Category],
    weather_data: dict[tuple[int, date], WeatherDaily],
    holidays: list[Holiday],
    start_date: date,
    end_date: date,
) -> list[Transaction]:
    """Generate transaction records with realistic demand patterns.

    Args:
        stores: List of Store objects with ids.
        products: List of Product objects with ids and category_ids.
        categories: List of Category objects with ids.
        weather_data: Dict keyed by (store_id, date) -> WeatherDaily.
        holidays: List of Holiday objects.
        start_date: First date to generate.
        end_date: Last date to generate.

    Returns:
        List of Transaction ORM objects.
    """
    rng = random.Random(42)

    cat_map = {c.id: c for c in categories}
    holiday_dates = {h.date for h in holidays}

    # Group products by category for base demand lookup
    cat_name_map = {c.id: c.name for c in categories}

    transactions: list[Transaction] = []
    current = start_date
    (end_date - start_date).days + 1

    while current <= end_date:
        day_of_year = current.timetuple().tm_yday
        dow = current.weekday()
        dow_mult = DOW_MULTIPLIER[dow]
        holiday_mult = _holiday_multiplier(current, holiday_dates)
        christmas_mult = _christmas_multiplier(current)

        # Year-over-year growth (2-5% per year from start)
        years_from_start = (current - start_date).days / 365.0
        yoy_mult = 1.0 + 0.03 * years_from_start

        for store in stores:
            store_scale = STORE_TYPE_SCALE.get(store.store_type, 1.0) * CITY_SCALE.get(
                store.city, 0.8
            )
            weather = weather_data.get((store.id, current))

            for product in products:
                category = cat_map[product.category_id]
                cat_name = cat_name_map[product.category_id]
                base = CATEGORY_BASE_DEMAND.get(cat_name, 1.0)

                # Seasonal multiplier
                season_mult = 1.0
                if category.is_seasonal and category.peak_season:
                    profile = SEASON_PROFILES.get(category.peak_season, (7, 1.0))
                    season_mult = _seasonal_multiplier(day_of_year, profile[0], profile[1])

                # Weather multiplier
                weather_mult = _weather_multiplier(weather, category)

                # Christmas special boost for Christmas Decor
                xmas_mult = christmas_mult if cat_name == "Christmas Decor" else 1.0
                # General Christmas shopping lift for all categories
                general_xmas = (
                    1.0 + (christmas_mult - 1.0) * 0.3 if cat_name != "Christmas Decor" else 1.0
                )

                # Combined lambda for Poisson
                lam = (
                    base
                    * season_mult
                    * dow_mult
                    * holiday_mult
                    * weather_mult
                    * store_scale
                    * yoy_mult
                    * xmas_mult
                    * general_xmas
                )

                # Distribute demand per product (multiple products per category share demand)
                lam /= max(1, len([p for p in products if p.category_id == product.category_id]))
                lam = max(lam, 0.01)

                quantity = rng.poisson(lam) if hasattr(rng, "poisson") else _poisson(lam, rng)

                if quantity > 0:
                    # Slight price variation (+/- 5%) for sales/promotions
                    price_factor = rng.uniform(0.95, 1.05)
                    unit_price = round(float(product.unit_price) * price_factor, 2)
                    total = round(unit_price * quantity, 2)

                    transactions.append(
                        Transaction(
                            store_id=store.id,
                            product_id=product.id,
                            transaction_date=current,
                            quantity=quantity,
                            unit_price=Decimal(str(unit_price)),
                            total_amount=Decimal(str(total)),
                        )
                    )

        current += timedelta(days=1)

    return transactions


def _poisson(lam: float, rng: random.Random) -> int:
    """Pure-Python Poisson sampling using Knuth's algorithm."""
    if lam <= 0:
        return 0
    if lam > 30:
        # Normal approximation for large lambda
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p < L:
            return k - 1

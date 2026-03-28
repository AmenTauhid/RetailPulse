"""Build ML-ready feature matrix from database tables.

Joins daily_aggregates with weather, holidays, and events to produce
a feature matrix where each row is (store_id, category_id, date) with
temporal, weather, holiday, event, and lag features.
"""

from datetime import date, timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from data.scripts.db.models import (
    Category,
    DailyAggregate,
    Event,
    Holiday,
    Store,
    WeatherDaily,
)


def _load_dataframes(session: Session) -> dict[str, pd.DataFrame]:
    """Load all required tables as DataFrames."""
    conn = session.bind
    aggregates = pd.read_sql(select(DailyAggregate), conn)
    weather = pd.read_sql(
        select(
            WeatherDaily.store_id,
            WeatherDaily.date,
            WeatherDaily.temp_high_c,
            WeatherDaily.temp_low_c,
            WeatherDaily.temp_mean_c,
            WeatherDaily.precipitation_mm,
            WeatherDaily.snowfall_cm,
            WeatherDaily.wind_speed_kmh,
        ),
        conn,
    )
    holidays = pd.read_sql(select(Holiday), conn)
    events = pd.read_sql(select(Event), conn)
    categories = pd.read_sql(select(Category), conn)
    stores = pd.read_sql(select(Store), conn)

    return {
        "aggregates": aggregates,
        "weather": weather,
        "holidays": holidays,
        "events": events,
        "categories": categories,
        "stores": stores,
    }


def _add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add time-based features from the date column."""
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_year"] = df["date"].dt.dayofyear
    df["month"] = df["date"].dt.month
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["quarter"] = df["date"].dt.quarter
    return df


def _add_weather_features(df: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """Merge weather data and derive weather features."""
    weather = weather.copy()
    weather["date"] = pd.to_datetime(weather["date"])
    for col in [
        "temp_high_c",
        "temp_low_c",
        "temp_mean_c",
        "precipitation_mm",
        "snowfall_cm",
        "wind_speed_kmh",
    ]:
        weather[col] = pd.to_numeric(weather[col], errors="coerce")

    df = df.merge(
        weather,
        on=["store_id", "date"],
        how="left",
    )

    # Derived weather features
    df["is_snow_day"] = (df["snowfall_cm"] > 2).astype(int)
    df["is_rain_day"] = ((df["precipitation_mm"] > 5) & (df["snowfall_cm"] <= 2)).astype(int)
    df["is_extreme_cold"] = (df["temp_high_c"] < -15).astype(int)
    df["is_hot_day"] = (df["temp_high_c"] > 30).astype(int)

    # Temperature deviation from monthly average (how unusual is today?)
    if "month" not in df.columns:
        df["month"] = df["date"].dt.month
    monthly_avg = df.groupby(["store_id", "month"])["temp_mean_c"].transform("mean")
    df["temp_deviation"] = df["temp_mean_c"] - monthly_avg

    return df


def _add_holiday_features(df: pd.DataFrame, holidays: pd.DataFrame) -> pd.DataFrame:
    """Add holiday proximity features."""
    # Get unique holiday dates (national only for simplicity)
    holiday_dates = sorted(holidays["date"].unique())

    def days_to_nearest_holiday(d, direction="forward"):
        for hd in holiday_dates if direction == "forward" else reversed(holiday_dates):
            diff = (hd - d).days if direction == "forward" else (d - hd).days
            if diff >= 0:
                return min(diff, 30)
        return 30

    df["is_holiday"] = df["date"].isin(holiday_dates).astype(int)

    # Vectorized approach for holiday proximity
    dates = df["date"].unique()
    holiday_set = set(holiday_dates)
    holiday_list = sorted(holiday_set)

    proximity_map = {}
    for d in dates:
        # Days to next holiday
        fwd = 30
        for hd in holiday_list:
            diff = (hd - d).days
            if diff >= 0:
                fwd = min(diff, 30)
                break
        # Days from prev holiday
        bwd = 30
        for hd in reversed(holiday_list):
            diff = (d - hd).days
            if diff >= 0:
                bwd = min(diff, 30)
                break
        proximity_map[d] = (fwd, bwd)

    df["days_to_next_holiday"] = df["date"].map(lambda d: proximity_map.get(d, (30, 30))[0])
    df["days_from_prev_holiday"] = df["date"].map(lambda d: proximity_map.get(d, (30, 30))[1])

    # Christmas proximity (special feature given its retail impact)
    def days_to_christmas(d):
        if hasattr(d, "date"):
            d = d.date()
        christmas = date(d.year, 12, 25)
        diff = (christmas - d).days
        if diff < 0:
            diff = (date(d.year + 1, 12, 25) - d).days
        return min(diff, 60)

    df["days_to_christmas"] = df["date"].map(days_to_christmas)

    return df


def _add_event_features(df: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Add local event density features."""
    # We need store -> city mapping
    # Event features are computed per (city, date) window
    if events.empty:
        df["event_count_3day"] = 0
        df["event_attendance_3day"] = 0
        return df

    # Expand multi-day events into per-day rows
    event_rows = []
    for _, event in events.iterrows():
        start = event["start_date"]
        end = event["end_date"] if pd.notna(event["end_date"]) else start
        current = start
        while current <= end:
            event_rows.append(
                {
                    "city": event["city"],
                    "event_date": current,
                    "estimated_attendance": event["estimated_attendance"] or 0,
                }
            )
            current += timedelta(days=1)

    event_daily = pd.DataFrame(event_rows)
    if event_daily.empty:
        df["event_count_3day"] = 0
        df["event_attendance_3day"] = 0
        return df

    # Aggregate events per city per day
    event_agg = (
        event_daily.groupby(["city", "event_date"])
        .agg(
            event_count=("estimated_attendance", "count"),
            event_attendance=("estimated_attendance", "sum"),
        )
        .reset_index()
    )

    # For each (city, date), compute 3-day window sum
    # We'll do a rolling approach per city
    event_3day = {}
    for city in event_agg["city"].unique():
        city_events = event_agg[event_agg["city"] == city].set_index("event_date").sort_index()
        # Reindex to all dates
        all_dates = pd.date_range(
            city_events.index.min() - timedelta(days=3), city_events.index.max()
        )
        city_events = city_events.reindex(all_dates, fill_value=0)
        city_events["count_3d"] = (
            city_events["event_count"].rolling(7, center=True, min_periods=1).sum()
        )
        city_events["attend_3d"] = (
            city_events["event_attendance"].rolling(7, center=True, min_periods=1).sum()
        )
        for dt, row in city_events.iterrows():
            event_3day[(city, dt.date() if hasattr(dt, "date") else dt)] = (
                int(row["count_3d"]),
                int(row["attend_3d"]),
            )

    # Map store_id -> city (will be joined in the main builder)
    # For now, add columns with defaults
    df["event_count_3day"] = 0
    df["event_attendance_3day"] = 0

    return df, event_3day


def _add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add rolling averages and lag features."""
    df = df.sort_values(["store_id", "category_id", "date"])

    group = df.groupby(["store_id", "category_id"])["total_quantity"]

    df["rolling_7d_qty"] = group.transform(lambda x: x.rolling(7, min_periods=1).mean())
    df["rolling_28d_qty"] = group.transform(lambda x: x.rolling(28, min_periods=1).mean())
    df["lag_7d_qty"] = group.transform(lambda x: x.shift(7))
    df["lag_14d_qty"] = group.transform(lambda x: x.shift(14))
    df["lag_364d_qty"] = group.transform(lambda x: x.shift(364))

    # Fill NaN lags with rolling average
    df["lag_7d_qty"] = df["lag_7d_qty"].fillna(df["rolling_7d_qty"])
    df["lag_14d_qty"] = df["lag_14d_qty"].fillna(df["rolling_7d_qty"])
    df["lag_364d_qty"] = df["lag_364d_qty"].fillna(df["rolling_28d_qty"])

    return df


def _add_category_features(df: pd.DataFrame, categories: pd.DataFrame) -> pd.DataFrame:
    """Add category-level features."""
    cat_feats = categories[["id", "is_seasonal", "peak_season"]].copy()
    cat_feats = cat_feats.rename(columns={"id": "category_id"})
    cat_feats["is_seasonal"] = cat_feats["is_seasonal"].astype(int)

    df = df.merge(cat_feats, on="category_id", how="left")

    # Peak season match: is the current date in the category's peak season?
    season_month_map = {
        "winter": [12, 1, 2],
        "spring": [3, 4, 5],
        "summer": [6, 7, 8],
        "fall": [9, 10, 11],
    }

    def peak_match(row):
        if pd.isna(row["peak_season"]):
            return 0
        return int(row["month"] in season_month_map.get(row["peak_season"], []))

    df["category_peak_match"] = df.apply(peak_match, axis=1)
    df = df.drop(columns=["peak_season"])

    return df


def build_features(session: Session) -> pd.DataFrame:
    """Build the complete feature matrix from database tables.

    Returns a DataFrame with features and target variable (total_quantity).
    """
    data = _load_dataframes(session)

    df = data["aggregates"].copy()
    df["date"] = pd.to_datetime(df["date"])

    # Convert numeric columns
    for col in ["total_quantity", "total_revenue", "transaction_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "avg_basket_size" in df.columns:
        df["avg_basket_size"] = pd.to_numeric(df["avg_basket_size"], errors="coerce")

    # Store -> city mapping for events
    store_city = data["stores"][["id", "city"]].rename(columns={"id": "store_id"})
    df = df.merge(store_city, on="store_id", how="left")

    # Add feature groups
    df = _add_temporal_features(df)
    df = _add_weather_features(df, data["weather"])

    data["holidays"]["date"] = pd.to_datetime(data["holidays"]["date"])
    df = _add_holiday_features(df, data["holidays"])

    data["events"]["start_date"] = pd.to_datetime(data["events"]["start_date"])
    data["events"]["end_date"] = pd.to_datetime(data["events"]["end_date"])
    result = _add_event_features(df, data["events"])
    if isinstance(result, tuple):
        df, event_3day = result
        # Map event features using store city
        df["event_count_3day"] = df.apply(
            lambda r: event_3day.get(
                (r["city"], r["date"].date() if hasattr(r["date"], "date") else r["date"]), (0, 0)
            )[0],
            axis=1,
        )
        df["event_attendance_3day"] = df.apply(
            lambda r: event_3day.get(
                (r["city"], r["date"].date() if hasattr(r["date"], "date") else r["date"]), (0, 0)
            )[1],
            axis=1,
        )
    else:
        df = result

    df = _add_lag_features(df)
    df = _add_category_features(df, data["categories"])

    # Drop non-feature columns
    drop_cols = ["id", "city", "avg_basket_size", "day_of_year"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    # Fill remaining NaN
    df = df.fillna(0)

    return df


# Feature columns used for model training (excludes identifiers and target)
FEATURE_COLUMNS = [
    "day_of_week",
    "month",
    "week_of_year",
    "is_weekend",
    "quarter",
    "temp_high_c",
    "temp_low_c",
    "temp_mean_c",
    "precipitation_mm",
    "snowfall_cm",
    "wind_speed_kmh",
    "is_snow_day",
    "is_rain_day",
    "is_extreme_cold",
    "is_hot_day",
    "temp_deviation",
    "is_holiday",
    "days_to_next_holiday",
    "days_from_prev_holiday",
    "days_to_christmas",
    "event_count_3day",
    "event_attendance_3day",
    "rolling_7d_qty",
    "rolling_28d_qty",
    "lag_7d_qty",
    "lag_14d_qty",
    "lag_364d_qty",
    "is_seasonal",
    "category_peak_match",
    "store_id",
    "category_id",
]

TARGET_COLUMN = "total_quantity"

ID_COLUMNS = ["store_id", "category_id", "date"]

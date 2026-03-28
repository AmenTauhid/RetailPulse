"""Forecast endpoints — serve demand predictions from the trained XGBoost model."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.core.database import get_db
from api.app.models.schemas import ForecastPoint, ForecastResponse, ModelInfoResponse
from data.scripts.db.models import Category, DailyAggregate, Holiday, Store, WeatherDaily
from ml.features.feature_builder import FEATURE_COLUMNS

router = APIRouter()


async def _build_forecast_features(
    store_id: int,
    category_id: int,
    forecast_dates: list[date],
    db: AsyncSession,
) -> pd.DataFrame:
    """Build feature rows for future dates using latest available data."""
    # Get recent historical data for lag features
    lookback = date.today() - timedelta(days=400)
    hist_result = await db.execute(
        select(DailyAggregate)
        .where(
            DailyAggregate.store_id == store_id,
            DailyAggregate.category_id == category_id,
            DailyAggregate.date >= lookback,
        )
        .order_by(DailyAggregate.date)
    )
    hist_rows = hist_result.scalars().all()
    hist_qtys = {r.date: r.total_quantity for r in hist_rows}

    # Get weather for the store
    weather_result = await db.execute(
        select(WeatherDaily)
        .where(WeatherDaily.store_id == store_id)
        .order_by(WeatherDaily.date.desc())
        .limit(30)
    )
    recent_weather = weather_result.scalars().all()
    avg_temp = np.mean([float(w.temp_mean_c) for w in recent_weather]) if recent_weather else 0.0

    # Get holidays
    holiday_result = await db.execute(select(Holiday.date))
    holiday_dates = {r[0] for r in holiday_result.all()}

    # Get category info
    cat_result = await db.execute(select(Category).where(Category.id == category_id))
    category = cat_result.scalar_one_or_none()

    season_months = {"winter": [12, 1, 2], "summer": [6, 7, 8], "spring": [3, 4, 5], "fall": [9, 10, 11]}

    rows = []
    for d in forecast_dates:
        doy = d.timetuple().tm_yday
        dow = d.weekday()

        # Lag features from historical data
        qty_7 = hist_qtys.get(d - timedelta(days=7), 0)
        qty_14 = hist_qtys.get(d - timedelta(days=14), 0)
        qty_364 = hist_qtys.get(d - timedelta(days=364), 0)

        # Rolling averages
        recent_qtys = [hist_qtys.get(d - timedelta(days=i), 0) for i in range(1, 8)]
        rolling_7 = np.mean(recent_qtys) if recent_qtys else 0
        recent_28 = [hist_qtys.get(d - timedelta(days=i), 0) for i in range(1, 29)]
        rolling_28 = np.mean(recent_28) if recent_28 else 0

        # Holiday proximity
        days_to_next = 30
        days_from_prev = 30
        for hd in sorted(holiday_dates):
            diff = (hd - d).days
            if diff >= 0:
                days_to_next = min(diff, 30)
                break
        for hd in sorted(holiday_dates, reverse=True):
            diff = (d - hd).days
            if diff >= 0:
                days_from_prev = min(diff, 30)
                break

        # Christmas
        christmas = date(d.year, 12, 25)
        days_to_xmas = (christmas - d).days
        if days_to_xmas < 0:
            days_to_xmas = (date(d.year + 1, 12, 25) - d).days
        days_to_xmas = min(days_to_xmas, 60)

        row = {
            "store_id": store_id,
            "category_id": category_id,
            "date": d,
            "day_of_week": dow,
            "month": d.month,
            "week_of_year": d.isocalendar()[1],
            "is_weekend": int(dow in (5, 6)),
            "quarter": (d.month - 1) // 3 + 1,
            "temp_high_c": avg_temp + 3,
            "temp_low_c": avg_temp - 3,
            "temp_mean_c": avg_temp,
            "precipitation_mm": 0,
            "snowfall_cm": 0,
            "wind_speed_kmh": 15,
            "is_snow_day": 0,
            "is_rain_day": 0,
            "is_extreme_cold": int(avg_temp < -15),
            "is_hot_day": int(avg_temp > 30),
            "temp_deviation": 0,
            "is_holiday": int(d in holiday_dates),
            "days_to_next_holiday": days_to_next,
            "days_from_prev_holiday": days_from_prev,
            "days_to_christmas": days_to_xmas,
            "event_count_3day": 0,
            "event_attendance_3day": 0,
            "rolling_7d_qty": rolling_7,
            "rolling_28d_qty": rolling_28,
            "lag_7d_qty": qty_7,
            "lag_14d_qty": qty_14,
            "lag_364d_qty": qty_364,
            "is_seasonal": int(category.is_seasonal) if category else 0,
            "category_peak_match": int(
                d.month in season_months.get(category.peak_season or "", [])
            ) if category else 0,
        }
        rows.append(row)

    return pd.DataFrame(rows)


@router.get("/forecasts/{store_id}/{category_id}", response_model=ForecastResponse)
async def get_forecast(
    store_id: int,
    category_id: int,
    request: Request,
    days: int = Query(default=14, ge=1, le=90, description="Number of days to forecast"),
    db: AsyncSession = Depends(get_db),
):
    model = request.app.state.model
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded. Run training first.")

    # Build forecast dates
    today = date.today()
    forecast_dates = [today + timedelta(days=i) for i in range(1, days + 1)]

    # Build features
    df = await _build_forecast_features(store_id, category_id, forecast_dates, db)
    available_features = [c for c in FEATURE_COLUMNS if c in df.columns]
    X = df[available_features].values

    # Predict
    preds = model.predict(X)
    preds = np.maximum(preds, 0)

    # Estimate confidence interval (rough: +/- 1.5 * RMSE)
    meta = request.app.state.model_meta
    rmse = meta.get("metrics", {}).get("rmse", 1.5)

    forecasts = [
        ForecastPoint(
            date=forecast_dates[i],
            predicted_quantity=round(float(preds[i]), 2),
            lower_bound=round(max(0, float(preds[i]) - 1.5 * rmse), 2),
            upper_bound=round(float(preds[i]) + 1.5 * rmse, 2),
        )
        for i in range(len(preds))
    ]

    return ForecastResponse(
        store_id=store_id,
        category_id=category_id,
        forecasts=forecasts,
        model_type="xgboost",
        model_metrics=meta.get("metrics"),
        feature_importance=dict(list(meta.get("feature_importance", {}).items())[:10]),
    )


@router.get("/model/info", response_model=ModelInfoResponse)
async def get_model_info(request: Request):
    meta = request.app.state.model_meta
    if not meta:
        raise HTTPException(status_code=503, detail="No model metadata available.")
    return ModelInfoResponse(
        model_type=meta.get("model_type", "unknown"),
        metrics=meta.get("metrics", {}),
        feature_importance=meta.get("feature_importance", {}),
        train_date_range=meta.get("train_date_range", []),
        test_date_range=meta.get("test_date_range", []),
    )

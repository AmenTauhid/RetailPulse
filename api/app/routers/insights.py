"""Insights endpoints — top movers and weather impact analysis."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.core.database import get_db
from api.app.models.schemas import (
    TopMover,
    TopMoversResponse,
    WeatherImpactPoint,
    WeatherImpactResponse,
)
from data.scripts.db.models import Category, DailyAggregate, Store, WeatherDaily

router = APIRouter()


@router.get("/insights/top-movers", response_model=TopMoversResponse)
async def get_top_movers(
    days: int = Query(default=14, ge=7, le=90, description="Period to compare"),
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Find categories with the biggest demand changes vs the prior period."""
    today = date(2025, 12, 31)  # Use end of data range
    current_start = today - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)

    # Current period averages
    current_result = await db.execute(
        select(
            DailyAggregate.store_id,
            DailyAggregate.category_id,
            func.avg(DailyAggregate.total_quantity).label("avg_qty"),
        )
        .where(DailyAggregate.date >= current_start, DailyAggregate.date <= today)
        .group_by(DailyAggregate.store_id, DailyAggregate.category_id)
    )
    current = {(r[0], r[1]): float(r[2]) for r in current_result.all()}

    # Previous period averages
    prev_result = await db.execute(
        select(
            DailyAggregate.store_id,
            DailyAggregate.category_id,
            func.avg(DailyAggregate.total_quantity).label("avg_qty"),
        )
        .where(
            DailyAggregate.date >= previous_start,
            DailyAggregate.date < current_start,
        )
        .group_by(DailyAggregate.store_id, DailyAggregate.category_id)
    )
    previous = {(r[0], r[1]): float(r[2]) for r in prev_result.all()}

    # Load names
    store_result = await db.execute(select(Store))
    stores = {s.id: s.name for s in store_result.scalars().all()}
    cat_result = await db.execute(select(Category))
    categories = {c.id: c.name for c in cat_result.scalars().all()}

    # Compute changes
    movers = []
    for key, curr_avg in current.items():
        prev_avg = previous.get(key, 0)
        if prev_avg == 0:
            continue
        pct = ((curr_avg - prev_avg) / prev_avg) * 100
        movers.append(
            TopMover(
                category_id=key[1],
                category_name=categories.get(key[1], "Unknown"),
                store_id=key[0],
                store_name=stores.get(key[0], "Unknown"),
                current_avg_qty=round(curr_avg, 2),
                previous_avg_qty=round(prev_avg, 2),
                pct_change=round(pct, 2),
                direction="up" if pct > 0 else "down",
            )
        )

    movers.sort(key=lambda m: abs(m.pct_change), reverse=True)

    return TopMoversResponse(period_days=days, movers=movers[:limit])


@router.get("/insights/weather-impact", response_model=WeatherImpactResponse)
async def get_weather_impact(
    store_id: int = Query(default=1),
    db: AsyncSession = Depends(get_db),
):
    """Show how temperature ranges correlate with demand by category."""
    # Join aggregates with weather
    result = await db.execute(
        select(
            Category.name,
            WeatherDaily.temp_mean_c,
            DailyAggregate.total_quantity,
        )
        .join(
            WeatherDaily,
            (
                (DailyAggregate.store_id == WeatherDaily.store_id)
                & (DailyAggregate.date == WeatherDaily.date)
            ),
        )
        .join(Category, DailyAggregate.category_id == Category.id)
        .where(DailyAggregate.store_id == store_id)
    )
    rows = result.all()

    # Bucket by temperature range and category
    buckets: dict[tuple[str, str], list[int]] = {}
    for cat_name, temp, qty in rows:
        t = float(temp) if temp else 0
        if t < -10:
            temp_range = "< -10°C"
        elif t < 0:
            temp_range = "-10 to 0°C"
        elif t < 10:
            temp_range = "0 to 10°C"
        elif t < 20:
            temp_range = "10 to 20°C"
        else:
            temp_range = "> 20°C"

        key = (cat_name, temp_range)
        buckets.setdefault(key, []).append(qty)

    data = [
        WeatherImpactPoint(
            category_name=cat,
            temp_range=tr,
            avg_quantity=round(sum(qtys) / len(qtys), 2),
            sample_count=len(qtys),
        )
        for (cat, tr), qtys in sorted(buckets.items())
    ]

    return WeatherImpactResponse(data=data)

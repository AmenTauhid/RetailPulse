"""Historical demand data endpoints."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.core.database import get_db
from api.app.models.schemas import DailyDemandPoint, HistoricalResponse, WeatherResponse
from data.scripts.db.models import DailyAggregate, WeatherDaily

router = APIRouter()


@router.get("/historical/{store_id}/{category_id}", response_model=HistoricalResponse)
async def get_historical_demand(
    store_id: int,
    category_id: int,
    start_date: date = Query(default=None, description="Start date (default: 90 days ago)"),
    end_date: date = Query(default=None, description="End date (default: today)"),
    db: AsyncSession = Depends(get_db),
):
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=90)

    result = await db.execute(
        select(DailyAggregate)
        .where(
            DailyAggregate.store_id == store_id,
            DailyAggregate.category_id == category_id,
            DailyAggregate.date >= start_date,
            DailyAggregate.date <= end_date,
        )
        .order_by(DailyAggregate.date)
    )
    rows = result.scalars().all()

    data = [
        DailyDemandPoint(
            date=r.date,
            total_quantity=r.total_quantity,
            total_revenue=float(r.total_revenue),
            transaction_count=r.transaction_count,
        )
        for r in rows
    ]

    return HistoricalResponse(
        store_id=store_id,
        category_id=category_id,
        data=data,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/weather/{store_id}", response_model=list[WeatherResponse])
async def get_weather(
    store_id: int,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    limit: int = Query(default=30, le=365),
    db: AsyncSession = Depends(get_db),
):
    query = select(WeatherDaily).where(WeatherDaily.store_id == store_id)

    if start_date:
        query = query.where(WeatherDaily.date >= start_date)
    if end_date:
        query = query.where(WeatherDaily.date <= end_date)

    query = query.order_by(WeatherDaily.date.desc()).limit(limit)
    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        WeatherResponse(
            store_id=r.store_id,
            date=r.date,
            temp_high_c=float(r.temp_high_c) if r.temp_high_c else None,
            temp_low_c=float(r.temp_low_c) if r.temp_low_c else None,
            temp_mean_c=float(r.temp_mean_c) if r.temp_mean_c else None,
            precipitation_mm=float(r.precipitation_mm) if r.precipitation_mm else None,
            snowfall_cm=float(r.snowfall_cm) if r.snowfall_cm else None,
            weather_description=r.weather_description,
        )
        for r in rows
    ]

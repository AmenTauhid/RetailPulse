"""Anomaly detection endpoints."""

from datetime import date, timedelta

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.core.database import get_db
from api.app.models.schemas import AnomalyListResponse, AnomalyResponse
from data.scripts.db.models import Category, DailyAggregate, Store
from data.scripts.db.session import get_session_factory as get_sync_session_factory
from ml.features.feature_builder import FEATURE_COLUMNS, build_features

router = APIRouter()


@router.get("/anomalies", response_model=AnomalyListResponse)
async def get_anomalies(
    request: Request,
    store_id: int | None = Query(default=None),
    category_id: int | None = Query(default=None),
    severity: str | None = Query(default=None, description="Filter: low, medium, high"),
    days: int = Query(default=30, ge=1, le=365, description="Lookback days"),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    model = request.app.state.model
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")

    cutoff = date.today() - timedelta(days=days)

    # Query aggregates
    query = select(DailyAggregate).where(DailyAggregate.date >= cutoff)
    if store_id:
        query = query.where(DailyAggregate.store_id == store_id)
    if category_id:
        query = query.where(DailyAggregate.category_id == category_id)
    query = query.order_by(DailyAggregate.date.desc())

    result = await db.execute(query)
    rows = result.scalars().all()

    if not rows:
        return AnomalyListResponse(anomalies=[], total=0)

    # Build features using sync session (feature builder uses pandas read_sql)
    sync_factory = get_sync_session_factory()
    with sync_factory() as sync_session:
        df = build_features(sync_session)

    # Filter to matching rows
    df = df[df["date"] >= str(cutoff)]
    if store_id:
        df = df[df["store_id"] == store_id]
    if category_id:
        df = df[df["category_id"] == category_id]

    if df.empty:
        return AnomalyListResponse(anomalies=[], total=0)

    # Predict and compute residuals
    available_features = [c for c in FEATURE_COLUMNS if c in df.columns]
    y_actual = df["total_quantity"].values
    y_pred = model.predict(df[available_features].values)
    y_pred = np.maximum(y_pred, 0)

    residuals = y_actual - y_pred
    mean_r = np.mean(residuals)
    std_r = np.std(residuals)
    if std_r == 0:
        return AnomalyListResponse(anomalies=[], total=0)

    z_scores = (residuals - mean_r) / std_r

    # Load store/category names
    store_result = await db.execute(select(Store))
    stores = {s.id: s.name for s in store_result.scalars().all()}
    cat_result = await db.execute(select(Category))
    categories = {c.id: c.name for c in cat_result.scalars().all()}

    # Build anomaly list
    anomalies = []
    for i, z in enumerate(z_scores):
        abs_z = abs(z)
        if abs_z < 2.0:
            continue
        sev = "high" if abs_z >= 3.0 else "medium" if abs_z >= 2.5 else "low"
        if severity and sev != severity:
            continue

        row = df.iloc[i]
        anomalies.append(
            AnomalyResponse(
                store_id=int(row["store_id"]),
                category_id=int(row["category_id"]),
                date=row["date"].date() if hasattr(row["date"], "date") else row["date"],
                actual_quantity=int(y_actual[i]),
                predicted_quantity=round(float(y_pred[i]), 2),
                residual=round(float(residuals[i]), 2),
                severity=sev,
                z_score=round(float(z), 3),
                store_name=stores.get(int(row["store_id"])),
                category_name=categories.get(int(row["category_id"])),
            )
        )

    anomalies.sort(key=lambda a: abs(a.z_score), reverse=True)
    total = len(anomalies)
    anomalies = anomalies[:limit]

    return AnomalyListResponse(anomalies=anomalies, total=total)

"""Pydantic response and request schemas for the API."""

from datetime import date

from pydantic import BaseModel

# --- Generic ---


class ErrorResponse(BaseModel):
    detail: str
    status_code: int


# --- Stores ---


class StoreResponse(BaseModel):
    id: int
    store_code: str
    name: str
    city: str
    province: str
    latitude: float
    longitude: float
    store_type: str
    opened_date: date

    model_config = {"from_attributes": True}


# --- Categories ---


class CategoryResponse(BaseModel):
    id: int
    name: str
    department: str
    is_seasonal: bool
    peak_season: str | None

    model_config = {"from_attributes": True}


# --- Products ---


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    category_id: int
    unit_price: float
    unit_cost: float

    model_config = {"from_attributes": True}


# --- Historical ---


class DailyDemandPoint(BaseModel):
    date: date
    total_quantity: int
    total_revenue: float
    transaction_count: int


class HistoricalResponse(BaseModel):
    store_id: int
    category_id: int
    data: list[DailyDemandPoint]
    start_date: date
    end_date: date


# --- Forecasts ---


class ForecastPoint(BaseModel):
    date: date
    predicted_quantity: float
    lower_bound: float | None = None
    upper_bound: float | None = None


class ForecastResponse(BaseModel):
    store_id: int
    category_id: int
    forecasts: list[ForecastPoint]
    model_type: str = "xgboost"
    model_metrics: dict | None = None
    feature_importance: dict[str, float] | None = None


# --- Anomalies ---


class AnomalyResponse(BaseModel):
    store_id: int
    category_id: int
    date: date
    actual_quantity: int
    predicted_quantity: float
    residual: float
    severity: str
    z_score: float
    store_name: str | None = None
    category_name: str | None = None


class AnomalyListResponse(BaseModel):
    anomalies: list[AnomalyResponse]
    total: int


# --- Weather ---


class WeatherResponse(BaseModel):
    store_id: int
    date: date
    temp_high_c: float | None
    temp_low_c: float | None
    temp_mean_c: float | None
    precipitation_mm: float | None
    snowfall_cm: float | None
    weather_description: str | None

    model_config = {"from_attributes": True}


# --- Insights ---


class TopMover(BaseModel):
    category_id: int
    category_name: str
    store_id: int
    store_name: str
    current_avg_qty: float
    previous_avg_qty: float
    pct_change: float
    direction: str  # "up" or "down"


class TopMoversResponse(BaseModel):
    period_days: int
    movers: list[TopMover]


class WeatherImpactPoint(BaseModel):
    category_name: str
    temp_range: str
    avg_quantity: float
    sample_count: int


class WeatherImpactResponse(BaseModel):
    data: list[WeatherImpactPoint]


# --- Model Info ---


class ModelInfoResponse(BaseModel):
    model_type: str
    metrics: dict
    feature_importance: dict[str, float]
    train_date_range: list[str]
    test_date_range: list[str]

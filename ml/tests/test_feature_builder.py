"""Tests for the feature engineering pipeline."""

from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from ml.features.feature_builder import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    _add_holiday_features,
    _add_lag_features,
    _add_temporal_features,
    _add_weather_features,
)


@pytest.fixture
def sample_df():
    """Create a small DataFrame mimicking daily_aggregates."""
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    rows = []
    for d in dates:
        rows.append({
            "store_id": 1,
            "category_id": 1,
            "date": d,
            "total_quantity": np.random.randint(5, 50),
            "total_revenue": Decimal(str(np.random.uniform(100, 5000))),
            "transaction_count": np.random.randint(1, 20),
        })
    return pd.DataFrame(rows)


class TestTemporalFeatures:
    def test_adds_all_temporal_columns(self, sample_df):
        result = _add_temporal_features(sample_df)
        expected = ["day_of_week", "day_of_year", "month", "week_of_year", "is_weekend", "quarter"]
        for col in expected:
            assert col in result.columns

    def test_weekend_flag(self, sample_df):
        result = _add_temporal_features(sample_df)
        # Jan 6, 2024 is a Saturday
        sat_row = result[result["date"] == pd.Timestamp("2024-01-06")]
        if not sat_row.empty:
            assert sat_row.iloc[0]["is_weekend"] == 1

    def test_month_values(self, sample_df):
        result = _add_temporal_features(sample_df)
        assert (result["month"] == 1).all()  # All January


class TestWeatherFeatures:
    def test_merges_weather(self, sample_df):
        weather = pd.DataFrame([
            {"store_id": 1, "date": pd.Timestamp("2024-01-01"),
             "temp_high_c": -2, "temp_low_c": -10, "temp_mean_c": -5,
             "precipitation_mm": 0, "snowfall_cm": 5, "wind_speed_kmh": 20},
        ])
        result = _add_weather_features(sample_df, weather)
        assert "is_snow_day" in result.columns
        assert "temp_deviation" in result.columns

    def test_snow_day_flag(self):
        df = pd.DataFrame([{
            "store_id": 1, "category_id": 1, "date": pd.Timestamp("2024-01-01"),
            "total_quantity": 10, "month": 1,
        }])
        weather = pd.DataFrame([{
            "store_id": 1, "date": pd.Timestamp("2024-01-01"),
            "temp_high_c": -5, "temp_low_c": -12, "temp_mean_c": -8,
            "precipitation_mm": 0, "snowfall_cm": 10, "wind_speed_kmh": 15,
        }])
        result = _add_weather_features(df, weather)
        assert result.iloc[0]["is_snow_day"] == 1


class TestHolidayFeatures:
    def test_is_holiday_flag(self, sample_df):
        holidays = pd.DataFrame([
            {"date": pd.Timestamp("2024-01-01"), "name": "New Year's Day"},
        ])
        result = _add_holiday_features(sample_df, holidays)
        jan1 = result[result["date"] == pd.Timestamp("2024-01-01")]
        assert jan1.iloc[0]["is_holiday"] == 1

    def test_proximity_features(self, sample_df):
        holidays = pd.DataFrame([
            {"date": pd.Timestamp("2024-01-15"), "name": "Test Holiday"},
        ])
        result = _add_holiday_features(sample_df, holidays)
        assert "days_to_next_holiday" in result.columns
        assert "days_from_prev_holiday" in result.columns
        assert "days_to_christmas" in result.columns


class TestLagFeatures:
    def test_adds_lag_columns(self):
        dates = pd.date_range("2024-01-01", periods=60, freq="D")
        df = pd.DataFrame({
            "store_id": 1,
            "category_id": 1,
            "date": dates,
            "total_quantity": np.random.randint(5, 50, 60),
        })
        result = _add_lag_features(df)
        assert "rolling_7d_qty" in result.columns
        assert "rolling_28d_qty" in result.columns
        assert "lag_7d_qty" in result.columns
        assert "lag_14d_qty" in result.columns

    def test_no_nan_after_fillna(self):
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        df = pd.DataFrame({
            "store_id": 1,
            "category_id": 1,
            "date": dates,
            "total_quantity": np.random.randint(5, 50, 30),
        })
        result = _add_lag_features(df)
        assert not result["lag_7d_qty"].isna().any()

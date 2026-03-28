"""Tests for the XGBoost model module."""

import numpy as np
import pandas as pd
import pytest

from ml.models.xgboost_model import (
    chronological_split,
    compute_metrics,
)


@pytest.fixture
def sample_feature_df():
    """Create a synthetic feature DataFrame for testing."""
    n = 300
    rng = np.random.RandomState(42)
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="D"),
            "store_id": rng.randint(1, 3, n),
            "category_id": rng.randint(1, 5, n),
            "total_quantity": rng.randint(1, 100, n),
            "total_revenue": rng.uniform(50, 5000, n),
            "transaction_count": rng.randint(1, 30, n),
            "day_of_week": rng.randint(0, 7, n),
            "month": rng.randint(1, 13, n),
            "week_of_year": rng.randint(1, 53, n),
            "is_weekend": rng.randint(0, 2, n),
            "quarter": rng.randint(1, 5, n),
            "temp_high_c": rng.uniform(-20, 35, n),
            "temp_low_c": rng.uniform(-25, 20, n),
            "temp_mean_c": rng.uniform(-15, 25, n),
            "precipitation_mm": rng.uniform(0, 30, n),
            "snowfall_cm": rng.uniform(0, 20, n),
            "wind_speed_kmh": rng.uniform(0, 50, n),
            "is_snow_day": rng.randint(0, 2, n),
            "is_rain_day": rng.randint(0, 2, n),
            "is_extreme_cold": rng.randint(0, 2, n),
            "is_hot_day": rng.randint(0, 2, n),
            "temp_deviation": rng.uniform(-10, 10, n),
            "is_holiday": rng.randint(0, 2, n),
            "days_to_next_holiday": rng.randint(0, 31, n),
            "days_from_prev_holiday": rng.randint(0, 31, n),
            "days_to_christmas": rng.randint(0, 61, n),
            "event_count_3day": rng.randint(0, 5, n),
            "event_attendance_3day": rng.randint(0, 50000, n),
            "rolling_7d_qty": rng.uniform(5, 80, n),
            "rolling_28d_qty": rng.uniform(5, 80, n),
            "lag_7d_qty": rng.uniform(5, 80, n),
            "lag_14d_qty": rng.uniform(5, 80, n),
            "lag_364d_qty": rng.uniform(5, 80, n),
            "is_seasonal": rng.randint(0, 2, n),
            "category_peak_match": rng.randint(0, 2, n),
        }
    )
    return df


class TestChronologicalSplit:
    def test_split_sizes(self, sample_feature_df):
        train, val, test = chronological_split(sample_feature_df)
        total = len(train) + len(val) + len(test)
        assert total == len(sample_feature_df)

    def test_no_temporal_leakage(self, sample_feature_df):
        train, val, test = chronological_split(sample_feature_df)
        assert train["date"].max() <= val["date"].min()
        assert val["date"].max() <= test["date"].min()

    def test_default_ratios(self, sample_feature_df):
        train, val, _test = chronological_split(sample_feature_df)
        n = len(sample_feature_df)
        assert abs(len(train) / n - 0.7) < 0.05
        assert abs(len(val) / n - 0.15) < 0.05


class TestComputeMetrics:
    def test_perfect_predictions(self):
        y_true = np.array([10.0, 20.0, 30.0, 40.0])
        y_pred = np.array([10.0, 20.0, 30.0, 40.0])
        metrics = compute_metrics(y_true, y_pred)
        assert metrics.rmse == 0.0
        assert metrics.mae == 0.0
        assert metrics.r2 == 1.0

    def test_imperfect_predictions(self):
        y_true = np.array([10.0, 20.0, 30.0, 40.0])
        y_pred = np.array([12.0, 18.0, 33.0, 38.0])
        metrics = compute_metrics(y_true, y_pred)
        assert metrics.rmse > 0
        assert metrics.mae > 0
        assert 0 < metrics.r2 < 1
        assert metrics.mape > 0

    def test_handles_zero_actuals_in_mape(self):
        y_true = np.array([0.0, 10.0, 20.0])
        y_pred = np.array([1.0, 11.0, 19.0])
        metrics = compute_metrics(y_true, y_pred)
        # MAPE should be computed only on non-zero actuals
        assert metrics.mape > 0

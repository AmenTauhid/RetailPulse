"""Tests for the anomaly detector."""

import numpy as np
import pandas as pd
import pytest

from ml.models.anomaly_detector import detect_anomalies_statistical


@pytest.fixture
def sample_data():
    """Create sample prediction data with known anomalies."""
    n = 100
    rng = np.random.RandomState(42)

    df = pd.DataFrame(
        {
            "store_id": np.ones(n, dtype=int),
            "category_id": np.ones(n, dtype=int),
            "date": pd.date_range("2024-01-01", periods=n, freq="D"),
        }
    )

    y_actual = rng.normal(50, 5, n)
    y_predicted = y_actual + rng.normal(0, 2, n)  # Close predictions

    # Inject obvious anomalies
    y_actual[10] = 120  # Huge spike
    y_actual[50] = 5  # Huge drop

    return df, y_actual, y_predicted


class TestStatisticalAnomalies:
    def test_detects_spike(self, sample_data):
        df, y_actual, y_predicted = sample_data
        anomalies = detect_anomalies_statistical(df, y_actual, y_predicted)
        # Should detect the spike at index 10
        spike_dates = {a.date for a in anomalies}
        assert (
            str(df.iloc[10]["date"].date()) in spike_dates
            or str(df.iloc[10]["date"]) in spike_dates
        )

    def test_anomalies_have_severity(self, sample_data):
        df, y_actual, y_predicted = sample_data
        anomalies = detect_anomalies_statistical(df, y_actual, y_predicted)
        for a in anomalies:
            assert a.severity in ("low", "medium", "high")

    def test_sorted_by_z_score(self, sample_data):
        df, y_actual, y_predicted = sample_data
        anomalies = detect_anomalies_statistical(df, y_actual, y_predicted)
        z_scores = [abs(a.z_score) for a in anomalies]
        assert z_scores == sorted(z_scores, reverse=True)

    def test_no_anomalies_for_perfect_fit(self):
        df = pd.DataFrame(
            {
                "store_id": np.ones(50, dtype=int),
                "category_id": np.ones(50, dtype=int),
                "date": pd.date_range("2024-01-01", periods=50, freq="D"),
            }
        )
        y = np.full(50, 10.0)
        anomalies = detect_anomalies_statistical(df, y, y)
        assert len(anomalies) == 0

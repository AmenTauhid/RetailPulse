"""Anomaly detection for unexpected demand spikes and drops.

Uses prediction residuals from the XGBoost model to flag days where
actual demand deviates significantly from expected.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


@dataclass
class Anomaly:
    store_id: int
    category_id: int
    date: str
    actual_quantity: int
    predicted_quantity: float
    residual: float
    severity: str  # "low", "medium", "high"
    z_score: float


def detect_anomalies_statistical(
    df: pd.DataFrame,
    y_actual: np.ndarray,
    y_predicted: np.ndarray,
    z_threshold: float = 2.0,
) -> list[Anomaly]:
    """Detect anomalies using Z-score on prediction residuals.

    Args:
        df: DataFrame with store_id, category_id, date columns.
        y_actual: Actual demand values.
        y_predicted: Predicted demand values.
        z_threshold: Z-score threshold for anomaly flagging.

    Returns:
        List of Anomaly objects sorted by severity.
    """
    residuals = y_actual - y_predicted
    mean_res = np.mean(residuals)
    std_res = np.std(residuals)

    if std_res == 0:
        return []

    z_scores = (residuals - mean_res) / std_res

    anomalies: list[Anomaly] = []
    for i, z in enumerate(z_scores):
        abs_z = abs(z)
        if abs_z >= z_threshold:
            severity = "high" if abs_z >= 3.0 else "medium" if abs_z >= 2.5 else "low"
            anomalies.append(
                Anomaly(
                    store_id=int(df.iloc[i]["store_id"]),
                    category_id=int(df.iloc[i]["category_id"]),
                    date=str(df.iloc[i]["date"]),
                    actual_quantity=int(y_actual[i]),
                    predicted_quantity=round(float(y_predicted[i]), 2),
                    residual=round(float(residuals[i]), 2),
                    severity=severity,
                    z_score=round(float(z), 3),
                )
            )

    anomalies.sort(key=lambda a: abs(a.z_score), reverse=True)
    return anomalies


def train_isolation_forest(
    df: pd.DataFrame,
    y_actual: np.ndarray,
    y_predicted: np.ndarray,
    contamination: float = 0.05,
    output_dir: str = "ml/outputs",
) -> tuple[IsolationForest, list[Anomaly]]:
    """Train an Isolation Forest on prediction residuals and contextual features.

    Args:
        df: Feature DataFrame.
        y_actual: Actual demand values.
        y_predicted: Predicted demand values.
        contamination: Expected proportion of anomalies.
        output_dir: Directory to save the model.

    Returns:
        Tuple of (trained IsolationForest, list of detected anomalies).
    """
    residuals = y_actual - y_predicted
    pct_error = np.where(y_predicted > 0, residuals / y_predicted, 0)

    # Build anomaly feature matrix
    anomaly_features = pd.DataFrame({
        "residual": residuals,
        "pct_error": pct_error,
        "abs_residual": np.abs(residuals),
    })

    # Add contextual features if available
    for col in ["day_of_week", "month", "is_weekend", "is_holiday", "is_snow_day"]:
        if col in df.columns:
            anomaly_features[col] = df[col].values

    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=200,
        n_jobs=-1,
    )
    labels = model.fit_predict(anomaly_features)

    # Convert to anomaly objects
    anomaly_mask = labels == -1
    scores = model.decision_function(anomaly_features)

    anomalies: list[Anomaly] = []
    for i in np.where(anomaly_mask)[0]:
        score = float(scores[i])
        severity = "high" if score < -0.2 else "medium" if score < -0.1 else "low"
        anomalies.append(
            Anomaly(
                store_id=int(df.iloc[i]["store_id"]),
                category_id=int(df.iloc[i]["category_id"]),
                date=str(df.iloc[i]["date"]),
                actual_quantity=int(y_actual[i]),
                predicted_quantity=round(float(y_predicted[i]), 2),
                residual=round(float(residuals[i]), 2),
                severity=severity,
                z_score=round(score, 3),
            )
        )

    anomalies.sort(key=lambda a: a.z_score)

    # Save model
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_path / "anomaly_detector_latest.joblib")

    # Save anomaly summary
    summary = {
        "total_anomalies": len(anomalies),
        "high": sum(1 for a in anomalies if a.severity == "high"),
        "medium": sum(1 for a in anomalies if a.severity == "medium"),
        "low": sum(1 for a in anomalies if a.severity == "low"),
        "contamination": contamination,
        "timestamp": datetime.now().isoformat(),
    }
    with open(output_path / "anomaly_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(
        "Detected %d anomalies: %d high, %d medium, %d low",
        summary["total_anomalies"], summary["high"], summary["medium"], summary["low"],
    )

    return model, anomalies

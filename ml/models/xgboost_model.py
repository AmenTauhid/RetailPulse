"""XGBoost demand forecasting model with chronological train/val/test split."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ml.features.feature_builder import FEATURE_COLUMNS, TARGET_COLUMN

logger = logging.getLogger(__name__)


@dataclass
class ModelMetrics:
    rmse: float
    mae: float
    mape: float
    r2: float

    def to_dict(self) -> dict:
        return {
            "rmse": round(self.rmse, 4),
            "mae": round(self.mae, 4),
            "mape": round(self.mape, 4),
            "r2": round(self.r2, 4),
        }


def chronological_split(
    df: pd.DataFrame,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split data chronologically. Never leak future data into training."""
    df = df.sort_values("date").reset_index(drop=True)
    n = len(df)

    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train = df.iloc[:train_end]
    val = df.iloc[train_end:val_end]
    test = df.iloc[val_end:]

    logger.info(
        "Split: train=%d (to %s), val=%d (to %s), test=%d (to %s)",
        len(train), train["date"].max(),
        len(val), val["date"].max(),
        len(test), test["date"].max(),
    )

    return train, val, test


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> ModelMetrics:
    """Compute regression metrics."""
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))

    # MAPE: avoid division by zero
    mask = y_true != 0
    if mask.sum() > 0:
        mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)
    else:
        mape = 0.0

    r2 = float(r2_score(y_true, y_pred))

    return ModelMetrics(rmse=rmse, mae=mae, mape=mape, r2=r2)


def get_feature_importance(model: xgb.XGBRegressor, feature_names: list[str]) -> dict[str, float]:
    """Extract feature importance as a sorted dict."""
    importance = model.feature_importances_
    pairs = sorted(zip(feature_names, importance), key=lambda x: x[1], reverse=True)
    return {name: round(float(imp), 6) for name, imp in pairs}


def train_xgboost(
    df: pd.DataFrame,
    params: dict | None = None,
    output_dir: str = "ml/outputs",
) -> tuple[xgb.XGBRegressor, ModelMetrics, dict]:
    """Train XGBoost model on the feature matrix.

    Args:
        df: Feature matrix from build_features().
        params: XGBoost hyperparameters. Uses defaults if None.
        output_dir: Directory to save model artifacts.

    Returns:
        Tuple of (trained model, test metrics, feature importance dict).
    """
    # Ensure feature columns exist
    available_features = [c for c in FEATURE_COLUMNS if c in df.columns]
    missing = set(FEATURE_COLUMNS) - set(available_features)
    if missing:
        logger.warning("Missing features (will be skipped): %s", missing)

    train, val, test = chronological_split(df)

    X_train = train[available_features].values
    y_train = train[TARGET_COLUMN].values
    X_val = val[available_features].values
    y_val = val[TARGET_COLUMN].values
    X_test = test[available_features].values
    y_test = test[TARGET_COLUMN].values

    default_params = {
        "n_estimators": 500,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 5,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "random_state": 42,
        "n_jobs": -1,
    }
    if params:
        default_params.update(params)

    logger.info("Training XGBoost with params: %s", default_params)

    model = xgb.XGBRegressor(**default_params)
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )

    # Evaluate on test set
    y_pred = model.predict(X_test)
    y_pred = np.maximum(y_pred, 0)  # Demand cannot be negative

    metrics = compute_metrics(y_test, y_pred)
    importance = get_feature_importance(model, available_features)

    logger.info("Test metrics: %s", metrics.to_dict())
    logger.info("Top 10 features: %s", dict(list(importance.items())[:10]))

    # Save artifacts
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = output_path / f"xgboost_{timestamp}.joblib"
    metrics_path = output_path / f"xgboost_{timestamp}_metrics.json"

    joblib.dump(model, model_path)

    artifacts = {
        "model_type": "xgboost",
        "timestamp": timestamp,
        "params": default_params,
        "metrics": metrics.to_dict(),
        "feature_importance": importance,
        "feature_columns": available_features,
        "train_size": len(train),
        "val_size": len(val),
        "test_size": len(test),
        "train_date_range": [str(train["date"].min()), str(train["date"].max())],
        "test_date_range": [str(test["date"].min()), str(test["date"].max())],
    }
    with open(metrics_path, "w") as f:
        json.dump(artifacts, f, indent=2)

    # Also save as "latest" for easy access
    joblib.dump(model, output_path / "xgboost_latest.joblib")
    with open(output_path / "xgboost_latest_metrics.json", "w") as f:
        json.dump(artifacts, f, indent=2)

    logger.info("Model saved to %s", model_path)

    return model, metrics, importance


def load_model(model_path: str = "ml/outputs/xgboost_latest.joblib") -> xgb.XGBRegressor:
    """Load a saved XGBoost model."""
    return joblib.load(model_path)


def predict(
    model: xgb.XGBRegressor,
    df: pd.DataFrame,
) -> np.ndarray:
    """Generate predictions from a feature DataFrame."""
    available_features = [c for c in FEATURE_COLUMNS if c in df.columns]
    X = df[available_features].values
    preds = model.predict(X)
    return np.maximum(preds, 0)

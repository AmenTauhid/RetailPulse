"""ML model training CLI.

Usage:
    python -m ml.models.train
    python -m ml.models.train --config ml/configs/xgboost.yaml
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml

from data.scripts.db.session import get_session_factory
from ml.features.feature_builder import build_features, FEATURE_COLUMNS, TARGET_COLUMN
from ml.models.anomaly_detector import detect_anomalies_statistical, train_isolation_forest
from ml.models.xgboost_model import predict, train_xgboost

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def load_config(config_path: str | None) -> dict:
    """Load training config from YAML file."""
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {}


def main():
    parser = argparse.ArgumentParser(description="Train RetailPulse demand forecasting models")
    parser.add_argument("--config", type=str, default="ml/configs/xgboost.yaml",
                        help="Path to config YAML file")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory for model artifacts")
    args = parser.parse_args()

    config = load_config(args.config)
    output_dir = args.output_dir or config.get("output_dir", "ml/outputs")
    model_params = config.get("model", {})
    anomaly_config = config.get("anomaly", {})

    logger.info("=" * 60)
    logger.info("RetailPulse Model Training")
    logger.info("=" * 60)

    # Step 1: Build features
    logger.info("Step 1/3: Building feature matrix...")
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        df = build_features(session)

    logger.info("  Feature matrix: %d rows, %d columns", len(df), len(df.columns))
    logger.info("  Date range: %s to %s", df["date"].min(), df["date"].max())

    # Step 2: Train XGBoost
    logger.info("Step 2/3: Training XGBoost model...")
    model, metrics, importance = train_xgboost(df, params=model_params, output_dir=output_dir)

    logger.info("  RMSE: %.4f", metrics.rmse)
    logger.info("  MAE:  %.4f", metrics.mae)
    logger.info("  MAPE: %.2f%%", metrics.mape)
    logger.info("  R²:   %.4f", metrics.r2)
    logger.info("  Top 5 features:")
    for name, imp in list(importance.items())[:5]:
        logger.info("    %-25s %.4f", name, imp)

    # Step 3: Anomaly detection
    logger.info("Step 3/3: Running anomaly detection...")
    available_features = [c for c in FEATURE_COLUMNS if c in df.columns]
    y_actual = df[TARGET_COLUMN].values
    y_pred = predict(model, df)

    # Statistical anomalies
    stat_anomalies = detect_anomalies_statistical(df, y_actual, y_pred)
    logger.info("  Statistical anomalies (z>2.0): %d", len(stat_anomalies))

    # Isolation Forest
    contamination = anomaly_config.get("contamination", 0.05)
    iso_model, iso_anomalies = train_isolation_forest(
        df, y_actual, y_pred,
        contamination=contamination,
        output_dir=output_dir,
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("Training complete!")
    logger.info("  Artifacts saved to: %s", output_dir)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

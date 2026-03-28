"""Model evaluation CLI.

Usage:
    python -m ml.models.evaluate
    python -m ml.models.evaluate --model-path ml/outputs/xgboost_latest.joblib
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

from data.scripts.db.session import get_session_factory
from ml.features.feature_builder import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_features,
)
from ml.models.xgboost_model import (
    chronological_split,
    compute_metrics,
    load_model,
    predict,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained demand forecasting model")
    parser.add_argument("--model-path", type=str, default="ml/outputs/xgboost_latest.joblib",
                        help="Path to saved model")
    args = parser.parse_args()

    model_path = Path(args.model_path)
    if not model_path.exists():
        logger.error("Model not found at %s. Train a model first.", model_path)
        sys.exit(1)

    logger.info("Loading model from %s", model_path)
    model = load_model(str(model_path))

    # Build features
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        df = build_features(session)

    _, _, test = chronological_split(df)

    # Predict on test set
    y_test = test[TARGET_COLUMN].values
    y_pred = predict(model, test)

    metrics = compute_metrics(y_test, y_pred)

    logger.info("=" * 60)
    logger.info("Model Evaluation Results")
    logger.info("=" * 60)
    logger.info("  Test set size: %d", len(test))
    logger.info("  Date range: %s to %s", test["date"].min(), test["date"].max())
    logger.info("")
    logger.info("  RMSE:  %.4f", metrics.rmse)
    logger.info("  MAE:   %.4f", metrics.mae)
    logger.info("  MAPE:  %.2f%%", metrics.mape)
    logger.info("  R²:    %.4f", metrics.r2)
    logger.info("=" * 60)

    # Per-category breakdown
    logger.info("")
    logger.info("Per-category test metrics:")
    test_copy = test.copy()
    test_copy["predicted"] = y_pred

    for cat_id in sorted(test_copy["category_id"].unique()):
        mask = test_copy["category_id"] == cat_id
        y_t = test_copy.loc[mask, TARGET_COLUMN].values
        y_p = test_copy.loc[mask, "predicted"].values
        cat_metrics = compute_metrics(y_t, y_p)
        logger.info(
            "  Category %2d: RMSE=%.3f  MAE=%.3f  R²=%.3f",
            cat_id, cat_metrics.rmse, cat_metrics.mae, cat_metrics.r2,
        )


if __name__ == "__main__":
    main()

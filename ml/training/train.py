"""
ML Training Pipeline — Placeholder
=====================================
⚠️  PLACEHOLDER MODULE — No model training is implemented here.

This file defines the INTERFACE for the future ML correction model.
Training will NOT begin until:
  1. A validated dataset with ground-truth yield responses is available
  2. Target variable (correction residual vs STCR) is defined
  3. Feature engineering is agreed upon

See docs/science_status.md §3 for full requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TrainingConfig:
    """
    Configuration for the XGBoost correction model.
    All hyperparameters are defaults — tune via cross-validation on real data.
    """
    model_type: str = "xgboost"
    target: str = "npk_correction_residual"  # correction vs STCR baseline
    random_seed: int = 42
    n_estimators: int = 300
    max_depth: int = 5
    learning_rate: float = 0.05
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    early_stopping_rounds: int = 20

    # Features — must match MLCorrectionService._build_feature_vector()
    feature_columns: List[str] = field(default_factory=lambda: [
        "crop", "district", "season",
        "soil_N", "soil_P", "soil_K",
        "soil_pH", "soil_OC",
        "irrigation",
        "stcr_N", "stcr_P", "stcr_K",
        # weather variables TBD
    ])

    # Target — defined as actual_dose − stcr_dose for each nutrient
    target_columns: List[str] = field(default_factory=lambda: [
        "correction_N", "correction_P", "correction_K"
    ])


def train(config: TrainingConfig, data_path: str) -> None:
    """
    Entry point for model training.
    ⚠️  NOT IMPLEMENTED — dataset not yet available.
    """
    raise NotImplementedError(
        "ML training is not implemented. "
        "A validated dataset with yield response data is required. "
        "See docs/science_status.md §3."
    )


def evaluate(model_path: str, test_data_path: str) -> Dict[str, Any]:
    """
    Evaluates a trained model on held-out test data.
    ⚠️  NOT IMPLEMENTED — no model available.
    """
    raise NotImplementedError("No trained model available for evaluation.")


def explain(model_path: str, sample: Dict[str, Any]) -> Dict[str, float]:
    """
    Generates SHAP feature importance for a single prediction.
    ⚠️  NOT IMPLEMENTED — no model available.
    """
    raise NotImplementedError("SHAP explanation requires a trained model.")

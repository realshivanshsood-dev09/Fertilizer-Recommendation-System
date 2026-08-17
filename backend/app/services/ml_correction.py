"""
ML Correction Service
=====================
Applies an ML-learned correction (residual) on top of the STCR baseline.

Architecture note:
  - The ML layer DOES NOT replace the STCR baseline.
  - The model predicts a CORRECTION FACTOR (or residual), not an absolute dose.
  - final_N = STCR_N + ML_correction_N

Current status:  ML_ENABLED=False.
  No model has been trained.  A validated dataset with target definitions is
  required before training begins.  See docs/science_status.md §3 for details.

Feature interface (defined now, populated when model is ready):
  crop, district, season, soil_N, soil_P, soil_K, pH, organic_carbon,
  irrigation, STCR_N, STCR_P, STCR_K, [weather variables TBD]

Supports per-nutrient corrections: N, P, K independently.
"""

from __future__ import annotations

import structlog
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.constants import Crop, District, IrrigationType, Season
from app.schemas.response import MLAdjustment
from app.services.soil_resolution import SoilProfile
from app.schemas.response import STCRBaseline

log = structlog.get_logger(__name__)


class MLCorrectionService:
    """
    Interface for the ML correction layer.

    When ML_ENABLED=True and a model is loaded, this service:
      1. Builds the feature vector from context + STCR doses
      2. Calls the XGBoost model to predict N/P/K corrections
      3. Returns SHAP values for explainability

    When ML_ENABLED=False (current state), returns a zero-correction
    placeholder with model_enabled=False.
    """

    def __init__(self) -> None:
        self._model = None  # will hold loaded XGBoost model
        self._model_version: Optional[str] = None

        if settings.ML_ENABLED:
            self._load_model()

    def _load_model(self) -> None:
        """
        Load the trained XGBoost correction model from ML_MODEL_DIR.
        ⚠️  PLACEHOLDER — no model file exists yet.
        """
        log.warning(
            "ml_model_load_skipped",
            reason="No trained model available yet. Training requires validated dataset.",
            model_dir=settings.ML_MODEL_DIR,
        )
        self._model = None

    def _build_feature_vector(
        self,
        crop: Crop,
        district: District,
        season: Season,
        soil: SoilProfile,
        stcr: STCRBaseline,
        irrigation: Optional[IrrigationType],
    ) -> Dict[str, Any]:
        """
        Assembles the feature dictionary for the ML model.
        This interface is defined now so the model training pipeline
        knows exactly what features to expect.
        """
        return {
            "crop": crop.value,
            "district": district.value,
            "season": season.value,
            "soil_N": soil.nitrogen,
            "soil_P": soil.phosphorus,
            "soil_K": soil.potassium,
            "soil_pH": soil.ph,
            "soil_OC": soil.organic_carbon,
            "irrigation": irrigation.value if irrigation else None,
            "stcr_N": stcr.N_kg_per_ha,
            "stcr_P": stcr.P2O5_kg_per_ha,
            "stcr_K": stcr.K2O_kg_per_ha,
            # weather variables — TBD, see docs/science_status.md §3
        }

    def predict_correction(
        self,
        crop: Crop,
        district: District,
        season: Season,
        soil: SoilProfile,
        stcr: STCRBaseline,
        irrigation: Optional[IrrigationType] = None,
    ) -> MLAdjustment:
        if not settings.ML_ENABLED or self._model is None:
            log.info(
                "ml_correction_disabled",
                ml_enabled=settings.ML_ENABLED,
                model_loaded=self._model is not None,
            )
            return MLAdjustment(
                N_correction_kg_per_ha=None,
                P_correction_kg_per_ha=None,
                K_correction_kg_per_ha=None,
                model_version=None,
                model_enabled=False,
                shap_explanation=None,
            )

        # ── Active model path (future) ───────────────────────────────────────
        features = self._build_feature_vector(
            crop, district, season, soil, stcr, irrigation
        )
        # corrections = self._model.predict([features])  # XGBoost inference
        # shap_vals = shap_explainer(features)
        log.error("ml_model_inference_not_implemented")
        raise NotImplementedError(
            "ML model inference is not yet implemented. "
            "Set ML_ENABLED=False in config."
        )

"""
SQLAlchemy model registry.
All models must be imported here so Alembic can discover them.
"""
from app.models.location import Location
from app.models.farmer import Farmer
from app.models.crop import CropRecord
from app.models.soil_test import SoilTest
from app.models.study import Study
from app.models.field_trial import FieldTrialObservation
from app.models.stcr_config import STCRConfiguration
from app.models.model_version import ModelVersion
from app.models.recommendation import Recommendation
from app.models.recommendation_item import RecommendationItem
from app.models.fertilizer_product import FertilizerProductRecord
from app.models.fertilizer_price import FertilizerPrice
from app.models.biofertilizer import BiofertilizerRecord
from app.models.weather_observation import WeatherObservation

__all__ = [
    "Location",
    "Farmer",
    "CropRecord",
    "SoilTest",
    "Study",
    "FieldTrialObservation",
    "STCRConfiguration",
    "ModelVersion",
    "Recommendation",
    "RecommendationItem",
    "FertilizerProductRecord",
    "FertilizerPrice",
    "BiofertilizerRecord",
    "WeatherObservation",
]

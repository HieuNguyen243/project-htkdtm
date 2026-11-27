"""Data and recommendation provider adapters for TV4 frontend."""

from .base import DataProvider, ProviderError, RecommendationResponse, validate_preferences
from .mock_provider import MockDataProvider
from .real_provider import RealDataProvider

__all__ = [
    "DataProvider",
    "MockDataProvider",
    "ProviderError",
    "RealDataProvider",
    "RecommendationResponse",
    "validate_preferences",
]

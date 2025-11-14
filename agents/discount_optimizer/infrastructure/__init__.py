"""Infrastructure layer for external service integrations.

This module contains repository implementations for external APIs and services,
following the repository pattern for clean separation of concerns.
"""

from .salling_repository import SallingDiscountRepository
from .google_maps_repository import GoogleMapsRepository
from .cache_repository import (
    InMemoryCacheRepository,
    CacheMetrics,
    generate_cache_key,
    generate_cache_key_from_dict,
    serialize_for_cache,
    deserialize_from_cache,
    get_cache,
    close_global_cache,
)

__all__ = [
    "SallingDiscountRepository",
    "GoogleMapsRepository",
    "InMemoryCacheRepository",
    "CacheMetrics",
    "generate_cache_key",
    "generate_cache_key_from_dict",
    "serialize_for_cache",
    "deserialize_from_cache",
    "get_cache",
    "close_global_cache",
]

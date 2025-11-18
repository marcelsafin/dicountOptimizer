"""Infrastructure layer for external service integrations.

This module contains repository implementations for external APIs and services,
following the repository pattern for clean separation of concerns.
"""

from .cache_repository import (
    CacheMetrics,
    InMemoryCacheRepository,
    close_global_cache,
    deserialize_from_cache,
    generate_cache_key,
    generate_cache_key_from_dict,
    get_cache,
    serialize_for_cache,
)
from .google_maps_repository import GoogleMapsRepository
from .salling_repository import SallingDiscountRepository


__all__ = [
    "CacheMetrics",
    "GoogleMapsRepository",
    "InMemoryCacheRepository",
    "SallingDiscountRepository",
    "close_global_cache",
    "deserialize_from_cache",
    "generate_cache_key",
    "generate_cache_key_from_dict",
    "get_cache",
    "serialize_for_cache",
]

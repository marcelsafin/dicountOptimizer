"""Infrastructure layer for external service integrations.

This module contains repository implementations for external APIs and services,
following the repository pattern for clean separation of concerns.
"""

from .salling_repository import SallingDiscountRepository
from .google_maps_repository import GoogleMapsRepository

__all__ = [
    "SallingDiscountRepository",
    "GoogleMapsRepository",
]

"""Domain models and protocols for the Shopping Optimizer."""

from .exceptions import (
    AgentError,
    APIError,
    ShoppingOptimizerError,
    ValidationError,
)
from .models import (
    DiscountItem,
    Location,
    OptimizationPreferences,
    Purchase,
    ShoppingRecommendation,
    Timeframe,
)


__all__ = [
    "APIError",
    "AgentError",
    "DiscountItem",
    "Location",
    "OptimizationPreferences",
    "Purchase",
    "ShoppingOptimizerError",
    "ShoppingRecommendation",
    "Timeframe",
    "ValidationError",
]

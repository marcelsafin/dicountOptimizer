"""Domain models and protocols for the Shopping Optimizer."""

from .models import (
    Location,
    Timeframe,
    OptimizationPreferences,
    DiscountItem,
    Purchase,
    ShoppingRecommendation,
)
from .exceptions import (
    ShoppingOptimizerError,
    ValidationError,
    APIError,
    AgentError,
)

__all__ = [
    "Location",
    "Timeframe",
    "OptimizationPreferences",
    "DiscountItem",
    "Purchase",
    "ShoppingRecommendation",
    "ShoppingOptimizerError",
    "ValidationError",
    "APIError",
    "AgentError",
]

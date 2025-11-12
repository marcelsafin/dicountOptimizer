"""
Discount Optimizer Agent Package
"""

from .agent import root_agent, get_discounts_by_location, filter_products_by_preferences, optimize_shopping_plan
from .models import (
    Location, Timeframe, OptimizationPreferences, UserInput,
    DiscountItem, Purchase, ShoppingRecommendation,
    MOCK_DISCOUNTS, MEAL_INGREDIENTS
)
from .input_validator import InputValidator, ValidationError

__all__ = [
    'root_agent',
    'get_discounts_by_location',
    'filter_products_by_preferences',
    'optimize_shopping_plan',
    'Location',
    'Timeframe',
    'OptimizationPreferences',
    'UserInput',
    'DiscountItem',
    'Purchase',
    'ShoppingRecommendation',
    'MOCK_DISCOUNTS',
    'MEAL_INGREDIENTS',
    'InputValidator',
    'ValidationError',
]

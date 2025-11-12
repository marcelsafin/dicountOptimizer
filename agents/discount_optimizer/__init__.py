"""
Discount Optimizer Agent Package
"""

from .agent import root_agent, optimize_shopping
from .models import (
    Location, Timeframe, OptimizationPreferences, UserInput,
    DiscountItem, Purchase, ShoppingRecommendation,
    MOCK_DISCOUNTS, MEAL_INGREDIENTS
)
from .input_validator import InputValidator, ValidationError
from .discount_matcher import DiscountMatcher
from .ingredient_mapper import IngredientMapper
from .multi_criteria_optimizer import MultiCriteriaOptimizer
from .savings_calculator import SavingsCalculator
from .output_formatter import OutputFormatter
from .google_maps_service import GoogleMapsService

__all__ = [
    'root_agent',
    'optimize_shopping',
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
    'DiscountMatcher',
    'IngredientMapper',
    'MultiCriteriaOptimizer',
    'SavingsCalculator',
    'OutputFormatter',
    'GoogleMapsService',
]

"""
Google ADK agents for the Shopping Optimizer system.

This package contains all ADK-based agents that compose the shopping
optimization pipeline. Each agent has a single responsibility and uses
typed tool functions with Pydantic input/output models.
"""

from .ingredient_mapper_agent import (
    IngredientMapperAgent,
    IngredientMapping,
    IngredientMappingInput,
    IngredientMappingOutput,
    ProductMatch,
)
from .meal_suggester_agent import (
    MealSuggesterAgent,
    MealSuggestionInput,
    MealSuggestionOutput,
)
from .output_formatter_agent import (
    FormattingInput,
    FormattingOutput,
    OutputFormatterAgent,
)
from .shopping_optimizer_agent import (
    ShoppingOptimizerAgent,
    ShoppingOptimizerInput,
)


__all__ = [
    "FormattingInput",
    "FormattingOutput",
    "IngredientMapperAgent",
    "IngredientMapping",
    "IngredientMappingInput",
    "IngredientMappingOutput",
    "MealSuggesterAgent",
    "MealSuggestionInput",
    "MealSuggestionOutput",
    "OutputFormatterAgent",
    "ProductMatch",
    "ShoppingOptimizerAgent",
    "ShoppingOptimizerInput",
]

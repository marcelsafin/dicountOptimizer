"""
Google ADK agents for the Shopping Optimizer system.

This package contains all ADK-based agents that compose the shopping
optimization pipeline. Each agent has a single responsibility and uses
typed tool functions with Pydantic input/output models.
"""

from .meal_suggester_agent import (
    MealSuggesterAgent,
    MealSuggestionInput,
    MealSuggestionOutput,
)
from .ingredient_mapper_agent import (
    IngredientMapperAgent,
    IngredientMappingInput,
    IngredientMappingOutput,
    IngredientMapping,
    ProductMatch,
)
from .output_formatter_agent import (
    OutputFormatterAgent,
    FormattingInput,
    FormattingOutput,
)

__all__ = [
    'MealSuggesterAgent',
    'MealSuggestionInput',
    'MealSuggestionOutput',
    'IngredientMapperAgent',
    'IngredientMappingInput',
    'IngredientMappingOutput',
    'IngredientMapping',
    'ProductMatch',
    'OutputFormatterAgent',
    'FormattingInput',
    'FormattingOutput',
]

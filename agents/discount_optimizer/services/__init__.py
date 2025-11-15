"""
Business logic services for the Shopping Optimizer system.

This package contains deterministic business logic services that don't
require AI/LLM capabilities. These services handle filtering, sorting,
caching, and other computational tasks.
"""

from .discount_matcher_service import (
    DiscountMatcherService,
    DiscountMatchingInput,
    DiscountMatchingOutput,
)

__all__ = [
    'DiscountMatcherService',
    'DiscountMatchingInput',
    'DiscountMatchingOutput',
]

"""
DiscountMatcher Service - Deterministic discount filtering and matching.

This module implements the DiscountMatcher as a business logic service with:
- Typed functions using Pydantic models
- Dependency injection of DiscountRepository
- Location and timeframe filtering
- Caching for discount data to reduce API calls
- Structured logging

This is NOT an AI agent - it performs deterministic filtering, sorting, and
caching operations. No LLM calls are needed for this functionality.

Requirements: 2.1, 2.3, 3.1, 3.2, 8.1
"""

from datetime import date

from pydantic import BaseModel, Field, field_validator

from ..config import settings
from ..domain.models import Location, Timeframe, DiscountItem
from ..domain.protocols import DiscountRepository, CacheRepository
from ..domain.exceptions import APIError
from ..logging import get_logger, set_agent_context
from ..infrastructure.cache_repository import (
    generate_cache_key,
    serialize_for_cache,
    deserialize_from_cache,
)

# Get logger for this module
logger = get_logger(__name__)


class DiscountMatchingInput(BaseModel):
    """
    Input model for discount matching.
    
    Attributes:
        location: Geographic location to search around
        radius_km: Search radius in kilometers
        timeframe: Shopping timeframe for filtering discounts
        min_discount_percent: Minimum discount percentage to consider
        prefer_organic: Whether to prioritize organic products
        max_results: Maximum number of discount items to return
    """
    location: Location = Field(description="Geographic location to search around")
    radius_km: float = Field(default=5.0, gt=0.0, le=100.0, description="Search radius in kilometers")
    timeframe: Timeframe = Field(description="Shopping timeframe for filtering discounts")
    min_discount_percent: float = Field(default=10.0, ge=0.0, le=100.0, description="Minimum discount percentage to consider")
    prefer_organic: bool = Field(default=False, description="Whether to prioritize organic products")
    max_results: int = Field(default=100, gt=0, le=500, description="Maximum number of discount items to return")
    
    @field_validator('radius_km')
    @classmethod
    def validate_radius(cls, v: float) -> float:
        """Ensure radius is within reasonable bounds."""
        if v > 100.0:
            logger.warning("radius_capped", requested=v, capped_to=100.0)
            return 100.0
        return v


class DiscountMatchingOutput(BaseModel):
    """
    Output model from discount matching.
    
    Attributes:
        discounts: List of matched discount items
        total_found: Total number of discounts found before filtering
        total_matched: Number of discounts after filtering
        filters_applied: Description of filters that were applied
        cache_hit: Whether the result was retrieved from cache
        organic_count: Number of organic products in results
        average_discount_percent: Average discount percentage across all results
    """
    discounts: list[DiscountItem] = Field(description="List of matched discount items")
    total_found: int = Field(ge=0, description="Total number of discounts found before filtering")
    total_matched: int = Field(ge=0, description="Number of discounts after filtering")
    filters_applied: str = Field(description="Description of filters that were applied")
    cache_hit: bool = Field(default=False, description="Whether the result was retrieved from cache")
    organic_count: int = Field(ge=0, description="Number of organic products in results")
    average_discount_percent: float = Field(ge=0.0, le=100.0, description="Average discount percentage across all results")


class DiscountMatcherService:
    """
    Service for deterministic discount filtering and matching with caching.
    
    This service fetches and filters discount data from external sources
    (e.g., Salling Group API) based on location, timeframe, and user
    preferences. It implements caching to reduce API calls and improve
    performance.
    
    Key features:
    - Location-based filtering within specified radius
    - Timeframe filtering (only discounts valid during shopping period)
    - Minimum discount percentage filtering
    - Organic product prioritization
    - Intelligent caching with TTL
    - Comprehensive error handling with fallbacks
    
    This is a deterministic service - no AI/LLM calls are made.
    
    Requirements: 2.1, 2.3, 3.1, 3.2, 8.1
    """
    
    def __init__(
        self,
        discount_repository: DiscountRepository,
        cache_repository: CacheRepository | None = None,
    ):
        """
        Initialize DiscountMatcher service with dependency injection.
        
        Args:
            discount_repository: Repository for fetching discount data
            cache_repository: Optional cache repository for performance optimization
        
        Requirements: 3.2, 3.7, 5.5
        """
        set_agent_context('discount_matcher')
        
        self.discount_repository = discount_repository
        self.cache_repository = cache_repository
        
        logger.info(
            "discount_matcher_service_initialized",
            has_cache=cache_repository is not None,
            caching_enabled=settings.enable_caching,
        )
    
    async def match_discounts(self, input_data: DiscountMatchingInput) -> DiscountMatchingOutput:
        """
        Match discounts based on location, timeframe, and preferences.
        
        This method:
        1. Checks cache for existing results
        2. Fetches discounts from repository if cache miss
        3. Applies location filtering (within radius)
        4. Applies timeframe filtering (valid during shopping period)
        5. Applies discount percentage filtering
        6. Prioritizes organic products if requested
        7. Caches results for future requests
        
        Args:
            input_data: Validated input data for discount matching
        
        Returns:
            Structured output with matched discounts
        
        Requirements: 2.1, 2.3, 3.1, 3.2, 8.1
        """
        logger.info(
            "discount_matching_started",
            location=(input_data.location.latitude, input_data.location.longitude),
            radius_km=input_data.radius_km,
            timeframe=(input_data.timeframe.start_date, input_data.timeframe.end_date),
            min_discount_percent=input_data.min_discount_percent,
            prefer_organic=input_data.prefer_organic,
        )
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(input_data)
            
            # Try to get from cache first
            cached_result = await self._get_from_cache(cache_key)
            if cached_result is not None:
                logger.info("discount_cache_hit", cache_key=cache_key)
                cached_result.cache_hit = True
                return cached_result
            
            logger.debug("discount_cache_miss", cache_key=cache_key)
            
            # Fetch discounts from repository
            all_discounts = await self.discount_repository.fetch_discounts(
                location=input_data.location,
                radius_km=input_data.radius_km,
            )
            
            logger.debug("discounts_fetched_from_repository", count=len(all_discounts))
            
            # Apply filters
            filtered_discounts = self._apply_filters(all_discounts, input_data)
            
            # Sort and limit results
            sorted_discounts = self._sort_discounts(filtered_discounts, input_data)
            limited_discounts = sorted_discounts[:input_data.max_results]
            
            # Calculate statistics
            organic_count = sum(1 for d in limited_discounts if d.is_organic)
            average_discount = (
                sum(d.discount_percent for d in limited_discounts) / len(limited_discounts)
                if limited_discounts
                else 0.0
            )
            
            # Build filters description
            filters_applied = self._build_filters_description(input_data)
            
            # Create output
            output = DiscountMatchingOutput(
                discounts=limited_discounts,
                total_found=len(all_discounts),
                total_matched=len(limited_discounts),
                filters_applied=filters_applied,
                cache_hit=False,
                organic_count=organic_count,
                average_discount_percent=round(average_discount, 2),
            )
            
            # Cache the result
            await self._save_to_cache(cache_key, output)
            
            logger.info(
                "discount_matching_completed",
                total_found=output.total_found,
                total_matched=output.total_matched,
                cache_hit=output.cache_hit,
                organic_count=output.organic_count,
                average_discount=output.average_discount_percent,
            )
            
            return output
            
        except APIError as e:
            logger.error("discount_fetch_failed", error=str(e))
            raise
        except Exception as e:
            logger.error("discount_matching_failed", error=str(e), error_type=type(e).__name__)
            return self._fallback_results(input_data)
    
    def _apply_filters(
        self,
        discounts: list[DiscountItem],
        input_data: DiscountMatchingInput
    ) -> list[DiscountItem]:
        """Apply timeframe and discount percentage filters."""
        filtered = discounts
        
        # Filter by timeframe
        filtered = [d for d in filtered if d.expiration_date >= input_data.timeframe.start_date]
        logger.debug("timeframe_filter_applied", before=len(discounts), after=len(filtered))
        
        # Filter by minimum discount percentage
        filtered = [d for d in filtered if d.discount_percent >= input_data.min_discount_percent]
        logger.debug("discount_percent_filter_applied", min_percent=input_data.min_discount_percent, before=len(discounts), after=len(filtered))
        
        return filtered
    
    def _sort_discounts(
        self,
        discounts: list[DiscountItem],
        input_data: DiscountMatchingInput
    ) -> list[DiscountItem]:
        """Sort discounts by organic preference, discount percentage, and expiration date."""
        def sort_key(discount: DiscountItem) -> tuple[int, float, date]:
            organic_priority = 1 if (input_data.prefer_organic and discount.is_organic) else 0
            discount_priority = -discount.discount_percent
            expiration_priority = discount.expiration_date
            return (-organic_priority, discount_priority, expiration_priority)
        
        sorted_discounts = sorted(discounts, key=sort_key)
        logger.debug("discounts_sorted", count=len(sorted_discounts), prefer_organic=input_data.prefer_organic)
        return sorted_discounts
    
    def _build_filters_description(self, input_data: DiscountMatchingInput) -> str:
        """Build human-readable description of applied filters."""
        filters = [
            f"location within {input_data.radius_km}km",
            f"timeframe {input_data.timeframe.start_date} to {input_data.timeframe.end_date}",
            f"min discount {input_data.min_discount_percent}%"
        ]
        if input_data.prefer_organic:
            filters.append("prioritize organic")
        return ", ".join(filters)
    
    def _generate_cache_key(self, input_data: DiscountMatchingInput) -> str:
        """Generate cache key for discount matching request."""
        return generate_cache_key(
            input_data.location.latitude,
            input_data.location.longitude,
            input_data.radius_km,
            input_data.timeframe.start_date.isoformat(),
            input_data.timeframe.end_date.isoformat(),
            input_data.min_discount_percent,
            input_data.prefer_organic,
            prefix="discount_match:",
        )
    
    async def _get_from_cache(self, cache_key: str) -> DiscountMatchingOutput | None:
        """Get discount matching result from cache."""
        if not settings.enable_caching or self.cache_repository is None:
            return None
        
        try:
            cached_data = await self.cache_repository.get(cache_key)
            if cached_data is None:
                return None
            
            cached_result = deserialize_from_cache(cached_data)
            if isinstance(cached_result, DiscountMatchingOutput):
                return cached_result
            
            logger.warning("invalid_cache_data_type", expected="DiscountMatchingOutput", actual=type(cached_result).__name__)
            return None
        except Exception as e:
            logger.warning("cache_retrieval_failed", error=str(e), error_type=type(e).__name__)
            return None
    
    async def _save_to_cache(self, cache_key: str, output: DiscountMatchingOutput) -> None:
        """Save discount matching result to cache."""
        if not settings.enable_caching or self.cache_repository is None:
            return
        
        try:
            cached_data = serialize_for_cache(output)
            await self.cache_repository.set(cache_key, cached_data, ttl_seconds=settings.cache_ttl_seconds)
            logger.debug("discount_result_cached", cache_key=cache_key, ttl_seconds=settings.cache_ttl_seconds)
        except Exception as e:
            logger.warning("cache_save_failed", error=str(e), error_type=type(e).__name__)
    
    def _fallback_results(self, input_data: DiscountMatchingInput) -> DiscountMatchingOutput:
        """Provide fallback empty results if discount fetching fails."""
        logger.info("generating_fallback_empty_results")
        return DiscountMatchingOutput(
            discounts=[],
            total_found=0,
            total_matched=0,
            filters_applied=self._build_filters_description(input_data),
            cache_hit=False,
            organic_count=0,
            average_discount_percent=0.0,
        )

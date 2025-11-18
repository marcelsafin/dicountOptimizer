"""
ShoppingOptimizer Root Agent - Orchestrates the complete shopping optimization pipeline.

This module implements the root ShoppingOptimizer agent that composes all sub-agents
and services to provide end-to-end shopping optimization with:
- Dependency injection of all sub-agents and services
- Typed tool functions using Pydantic models
- Comprehensive error handling with typed exceptions
- Correlation IDs for distributed tracing
- Structured logging throughout the pipeline
- Graceful fallbacks when components fail

The agent orchestrates the following pipeline:
1. Input validation (location, timeframe, preferences)
2. Discount matching (fetch and filter discounts)
3. Meal suggestion (AI-powered meal ideas) OR use provided meal plan
4. Ingredient mapping (map meals to products)
5. Multi-criteria optimization (select best purchases)
6. Output formatting (tips and motivation)

Requirements: 2.2, 3.2, 3.3, 3.4, 10.1, 10.5
"""

from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel, Field, field_validator

from agents.discount_optimizer.config import settings
from agents.discount_optimizer.domain.exceptions import (
    AgentError,
    APIError,
    ShoppingOptimizerError,
    ValidationError,
)
from agents.discount_optimizer.domain.models import (
    Location,
    OptimizationPreferences,
    ShoppingRecommendation,
    Timeframe,
)
from agents.discount_optimizer.logging import (
    LogContext,
    get_correlation_id,
    get_logger,
    set_correlation_id,
)
from agents.discount_optimizer.services.discount_matcher_service import (
    DiscountMatcherService,
    DiscountMatchingInput,
)

# Import services
from agents.discount_optimizer.services.input_validation_service import (
    InputValidationService,
    ValidationInput,
)
from agents.discount_optimizer.services.multi_criteria_optimizer_service import (
    MultiCriteriaOptimizerService,
    OptimizationInput,
)

from .ingredient_mapper_agent import IngredientMapperAgent, IngredientMappingInput

# Import sub-agents
from .meal_suggester_agent import MealSuggesterAgent, MealSuggestionInput
from .output_formatter_agent import FormattingInput, OutputFormatterAgent


# Get logger for this module
logger = get_logger(__name__)


class ShoppingOptimizerInput(BaseModel):
    """
    Input model for shopping optimization.

    This is the main entry point for the shopping optimizer. Users can provide
    either an address or coordinates, along with their meal preferences and
    optimization goals.

    Attributes:
        address: User's address or location description
        latitude: Optional latitude if coordinates are provided directly
        longitude: Optional longitude if coordinates are provided directly
        meal_plan: List of meal names (empty for AI suggestions)
        timeframe: Shopping timeframe description (e.g., "this week", "next 3 days")
        maximize_savings: Whether to prioritize maximum cost savings
        minimize_stores: Whether to prioritize shopping at fewer stores
        prefer_organic: Whether to prioritize organic products
        search_radius_km: Optional search radius in kilometers
        num_meals: Optional number of meals to suggest (if meal_plan is empty)
        correlation_id: Optional correlation ID for distributed tracing

    Example:
        >>> input_data = ShoppingOptimizerInput(
        ...     address="Nørrebrogade 20, Copenhagen",
        ...     meal_plan=[],  # Empty for AI suggestions
        ...     timeframe="this week",
        ...     maximize_savings=True,
        ...     num_meals=5,
        ... )
    """

    address: str | None = Field(
        default=None, description="User's address or location description", max_length=500
    )
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="Latitude in degrees (if coordinates provided directly)",
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Longitude in degrees (if coordinates provided directly)",
    )
    meal_plan: list[str] = Field(
        default_factory=list,
        description="List of meal names (empty for AI suggestions)",
        max_length=20,
    )
    timeframe: str = Field(
        default="this week", description="Shopping timeframe description", max_length=100
    )
    maximize_savings: bool = Field(default=True, description="Prioritize maximum cost savings")
    minimize_stores: bool = Field(default=False, description="Prioritize shopping at fewer stores")
    prefer_organic: bool = Field(default=False, description="Prioritize organic products")
    search_radius_km: float | None = Field(
        default=None, gt=0, le=50, description="Search radius in kilometers"
    )
    num_meals: int | None = Field(
        default=None, ge=1, le=10, description="Number of meals to suggest (if meal_plan is empty)"
    )
    correlation_id: str | None = Field(
        default=None, description="Optional correlation ID for distributed tracing"
    )

    @field_validator("meal_plan")
    @classmethod
    def validate_meal_plan_items(cls, v: list[str]) -> list[str]:
        """Ensure meal plan items are non-empty strings."""
        if v:
            # Filter out empty strings
            return [meal.strip() for meal in v if meal and meal.strip()]
        return v


class ShoppingOptimizerAgent:
    """
    Root agent that orchestrates the complete shopping optimization pipeline.

    This agent composes specialized sub-agents and services to provide end-to-end
    shopping optimization. It follows enterprise-grade patterns:
    - Dependency injection for all components
    - Comprehensive error handling with typed exceptions
    - Correlation IDs for distributed tracing
    - Structured logging throughout the pipeline
    - Graceful fallbacks when components fail
    - Type-safe data flow using Pydantic models

    The agent orchestrates the following pipeline:
    1. Input validation (location, timeframe, preferences)
    2. Discount matching (fetch and filter discounts)
    3. Meal suggestion (AI-powered) OR use provided meal plan
    4. Ingredient mapping (map meals to products)
    5. Multi-criteria optimization (select best purchases)
    6. Output formatting (tips and motivation)

    Each step is logged with correlation IDs for debugging and monitoring.
    If any step fails, the agent attempts graceful fallbacks to provide
    partial results rather than complete failure.

    Example:
        >>> from agents.discount_optimizer.infrastructure.google_maps_repository import (
        ...     GoogleMapsRepository,
        ... )
        >>> from agents.discount_optimizer.infrastructure.salling_repository import (
        ...     SallingDiscountRepository,
        ... )
        >>> from agents.discount_optimizer.infrastructure.cache_repository import (
        ...     InMemoryCacheRepository,
        ... )
        >>> # Create dependencies
        >>> geocoding_service = GoogleMapsRepository()
        >>> discount_repository = SallingDiscountRepository()
        >>> cache_repository = InMemoryCacheRepository()
        >>> # Create agent with dependency injection
        >>> agent = ShoppingOptimizerAgent(
        ...     meal_suggester=MealSuggesterAgent(),
        ...     ingredient_mapper=IngredientMapperAgent(),
        ...     output_formatter=OutputFormatterAgent(),
        ...     input_validator=InputValidationService(geocoding_service),
        ...     discount_matcher=DiscountMatcherService(discount_repository, cache_repository),
        ...     optimizer=MultiCriteriaOptimizerService(),
        ... )
        >>> # Run optimization
        >>> input_data = ShoppingOptimizerInput(
        ...     address="Nørrebrogade 20, Copenhagen",
        ...     meal_plan=[],
        ...     timeframe="this week",
        ...     maximize_savings=True,
        ... )
        >>> recommendation = await agent.run(input_data)
        >>> print(f"Total savings: {recommendation.total_savings} kr")

    Requirements: 2.2, 3.2, 3.3, 3.4, 10.1, 10.5
    """

    def __init__(
        self,
        meal_suggester: MealSuggesterAgent,
        ingredient_mapper: IngredientMapperAgent,
        output_formatter: OutputFormatterAgent,
        input_validator: InputValidationService,
        discount_matcher: DiscountMatcherService,
        optimizer: MultiCriteriaOptimizerService,
    ):
        """
        Initialize ShoppingOptimizer agent with dependency injection.

        All dependencies are injected via constructor to enable:
        - Testability (can inject mocks)
        - Flexibility (can swap implementations)
        - Clear dependency graph
        - Type safety (Protocol validation)

        Args:
            meal_suggester: Agent for AI-powered meal suggestions
            ingredient_mapper: Agent for mapping meals to products
            output_formatter: Agent for formatting output with tips
            input_validator: Service for input validation
            discount_matcher: Service for discount fetching and filtering
            optimizer: Service for multi-criteria optimization

        Requirements: 3.2, 3.7, 5.5
        """
        self.meal_suggester = meal_suggester
        self.ingredient_mapper = ingredient_mapper
        self.output_formatter = output_formatter
        self.input_validator = input_validator
        self.discount_matcher = discount_matcher
        self.optimizer = optimizer

        logger.info(
            "shopping_optimizer_agent_initialized",
            meal_suggester=type(meal_suggester).__name__,
            ingredient_mapper=type(ingredient_mapper).__name__,
            output_formatter=type(output_formatter).__name__,
            input_validator=type(input_validator).__name__,
            discount_matcher=type(discount_matcher).__name__,
            optimizer=type(optimizer).__name__,
        )

    async def run(self, input_data: ShoppingOptimizerInput) -> ShoppingRecommendation:
        """
        Run the complete shopping optimization pipeline.

        This is the main entry point for the agent. It orchestrates all sub-agents
        and services in the correct order, handles errors gracefully, and returns
        a complete shopping recommendation.

        Pipeline:
        1. Set up correlation ID for distributed tracing
        2. Validate input (location, timeframe, preferences)
        3. Fetch and filter discounts
        4. Generate meal suggestions (AI) or use provided meal plan
        5. Map meals to available products
        6. Optimize purchases using multi-criteria scoring
        7. Format output with tips and motivation

        Args:
            input_data: Validated input data for shopping optimization

        Returns:
            Complete shopping recommendation with purchases, tips, and motivation

        Raises:
            ValidationError: If input validation fails
            ShoppingOptimizerError: If optimization pipeline fails

        Requirements: 2.2, 3.2, 3.3, 3.4, 10.1, 10.5
        """
        # Set up correlation ID for distributed tracing
        correlation_id = input_data.correlation_id or set_correlation_id()

        with LogContext(correlation_id=correlation_id, agent="shopping_optimizer"):
            logger.info(
                "shopping_optimization_started",
                has_address=bool(input_data.address),
                has_coordinates=bool(input_data.latitude and input_data.longitude),
                has_meal_plan=bool(input_data.meal_plan),
                timeframe=input_data.timeframe,
                maximize_savings=input_data.maximize_savings,
                minimize_stores=input_data.minimize_stores,
                prefer_organic=input_data.prefer_organic,
                correlation_id=correlation_id,
            )

            try:
                # Step 1: Validate input
                validation_result = await self._validate_input(input_data)

                if not validation_result.is_valid:
                    error_msg = "; ".join(validation_result.validation_errors)
                    logger.error(
                        "input_validation_failed",
                        errors=validation_result.validation_errors,
                        correlation_id=correlation_id,
                    )
                    raise ValidationError(f"Input validation failed: {error_msg}")

                # Extract validated data
                location = validation_result.location
                timeframe = validation_result.timeframe
                preferences = validation_result.preferences
                search_radius_km = validation_result.search_radius_km
                meal_plan = validation_result.meal_plan
                num_meals = validation_result.num_meals

                if not location or not timeframe or not preferences:
                    raise ValidationError("Missing required validated data")

                logger.info(
                    "input_validated",
                    location=(location.latitude, location.longitude),
                    timeframe=(timeframe.start_date, timeframe.end_date),
                    search_radius_km=search_radius_km,
                    num_meals=num_meals,
                    has_meal_plan=bool(meal_plan),
                    correlation_id=correlation_id,
                )

                # Step 2: Fetch and filter discounts
                discount_result = await self._fetch_discounts(
                    location, timeframe, preferences, search_radius_km
                )

                logger.info(
                    "discounts_fetched",
                    total_found=discount_result.total_found,
                    total_matched=discount_result.total_matched,
                    unique_stores=len({d.store_name for d in discount_result.discounts}),
                    correlation_id=correlation_id,
                )

                # Step 3: Generate or use meal plan
                if meal_plan:
                    # Use provided meal plan
                    final_meal_plan = meal_plan
                    logger.info(
                        "using_provided_meal_plan",
                        num_meals=len(meal_plan),
                        meals=meal_plan,
                        correlation_id=correlation_id,
                    )
                else:
                    # Generate AI meal suggestions
                    meal_suggestions = await self._suggest_meals(
                        discount_result.discounts, num_meals
                    )
                    final_meal_plan = meal_suggestions.suggested_meals
                    logger.info(
                        "ai_meals_suggested",
                        num_meals=len(final_meal_plan),
                        meals=final_meal_plan,
                        correlation_id=correlation_id,
                    )

                # Step 4: Map meals to products
                ingredient_mappings = await self._map_ingredients(
                    final_meal_plan, discount_result.discounts
                )

                logger.info(
                    "ingredients_mapped",
                    total_ingredients=ingredient_mappings.total_ingredients,
                    ingredients_with_matches=ingredient_mappings.ingredients_with_matches,
                    coverage_percent=ingredient_mappings.coverage_percent,
                    correlation_id=correlation_id,
                )

                # Step 5: Optimize purchases
                optimization_result = await self._optimize_purchases(
                    ingredient_mappings, preferences, location, timeframe
                )

                logger.info(
                    "purchases_optimized",
                    total_items=optimization_result.total_items,
                    unique_stores=optimization_result.unique_stores,
                    total_savings=float(optimization_result.total_savings),
                    correlation_id=correlation_id,
                )

                # Step 6: Format output
                recommendation = await self._format_output(optimization_result, location)

                logger.info(
                    "shopping_optimization_completed",
                    total_purchases=len(recommendation.purchases),
                    total_savings=float(recommendation.total_savings),
                    time_savings=recommendation.time_savings,
                    num_stores=len(recommendation.stores),
                    correlation_id=correlation_id,
                )

                return recommendation

            except ValidationError:
                # Re-raise validation errors
                raise
            except Exception as e:
                logger.exception(
                    "shopping_optimization_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    correlation_id=correlation_id,
                )
                raise ShoppingOptimizerError(f"Shopping optimization failed: {e!s}") from e

    async def _validate_input(self, input_data: ShoppingOptimizerInput) -> Any:
        """
        Validate user input using InputValidationService.

        Args:
            input_data: User input data

        Returns:
            ValidationOutput with validated data

        Requirements: 1.4, 4.4, 10.1
        """
        logger.debug("validating_input", correlation_id=get_correlation_id())

        validation_input = ValidationInput(
            address=input_data.address,
            latitude=input_data.latitude,
            longitude=input_data.longitude,
            meal_plan=input_data.meal_plan,
            timeframe=input_data.timeframe,
            maximize_savings=input_data.maximize_savings,
            minimize_stores=input_data.minimize_stores,
            prefer_organic=input_data.prefer_organic,
            search_radius_km=input_data.search_radius_km,
            num_meals=input_data.num_meals,
        )

        return await self.input_validator.run(validation_input)

    async def _fetch_discounts(
        self,
        location: Location,
        timeframe: Timeframe,
        preferences: OptimizationPreferences,
        search_radius_km: float,
    ) -> Any:
        """
        Fetch and filter discounts using DiscountMatcherService.

        Args:
            location: User's location
            timeframe: Shopping timeframe
            preferences: Optimization preferences
            search_radius_km: Search radius in kilometers

        Returns:
            DiscountMatchingOutput with filtered discounts

        Requirements: 2.1, 3.2, 8.1, 10.1
        """
        logger.debug(
            "fetching_discounts",
            location=(location.latitude, location.longitude),
            radius_km=search_radius_km,
            correlation_id=get_correlation_id(),
        )

        discount_input = DiscountMatchingInput(
            location=location,
            radius_km=search_radius_km,
            timeframe=timeframe,
            min_discount_percent=settings.min_discount_percent,
            prefer_organic=preferences.prefer_organic,
            max_results=100,
        )

        try:
            return await self.discount_matcher.match_discounts(discount_input)
        except APIError as e:
            logger.warning(
                "discount_fetch_failed_using_fallback",
                error=str(e),
                correlation_id=get_correlation_id(),
            )
            # Return empty result as fallback
            from agents.discount_optimizer.services.discount_matcher_service import DiscountMatchingOutput

            return DiscountMatchingOutput(
                discounts=[],
                total_found=0,
                total_matched=0,
                filters_applied="fallback due to API error",
                cache_hit=False,
                organic_count=0,
                average_discount_percent=0.0,
            )

    async def _suggest_meals(self, discounts: list[Any], num_meals: int) -> Any:
        """
        Generate AI-powered meal suggestions using MealSuggesterAgent.

        Args:
            discounts: List of available discount items
            num_meals: Number of meals to suggest

        Returns:
            MealSuggestionOutput with suggested meals

        Requirements: 2.1, 2.3, 3.1, 3.3, 10.1
        """
        logger.debug(
            "suggesting_meals",
            num_discounts=len(discounts),
            num_meals=num_meals,
            correlation_id=get_correlation_id(),
        )

        # Handle empty discount list - use fallback
        if not discounts:
            logger.warning(
                "no_discounts_available_using_fallback_meals", correlation_id=get_correlation_id()
            )
            from .meal_suggester_agent import MealSuggestionOutput

            return MealSuggestionOutput(
                suggested_meals=["Salat", "Wrap", "Suppe", "Omelet", "Grillret"][:num_meals],
                reasoning="Fallback suggestions due to no discounts available",
                urgency_notes="",
            )

        # Extract product names and details
        available_products = [d.product_name for d in discounts]
        product_details = [
            {
                "name": d.product_name,
                "expiration_date": d.expiration_date,
                "discount_percent": d.discount_percent,
            }
            for d in discounts
        ]

        meal_input = MealSuggestionInput(
            available_products=available_products[:20],  # Limit to avoid token overflow
            num_meals=num_meals,
            product_details=product_details[:20],
        )

        try:
            return await self.meal_suggester.run(meal_input)
        except (AgentError, Exception) as e:
            logger.warning(
                "meal_suggestion_failed_using_fallback",
                error=str(e),
                correlation_id=get_correlation_id(),
            )
            # Return fallback suggestions
            from .meal_suggester_agent import MealSuggestionOutput

            return MealSuggestionOutput(
                suggested_meals=["Salat", "Wrap", "Suppe", "Omelet", "Grillret"][:num_meals],
                reasoning="Fallback suggestions due to AI service unavailable",
                urgency_notes="",
            )

    async def _map_ingredients(self, meal_plan: list[str], discounts: list[Any]) -> Any:
        """
        Map meals to available products using IngredientMapperAgent.

        Args:
            meal_plan: List of meal names
            discounts: List of available discount items

        Returns:
            IngredientMappingOutput with ingredient-to-product mappings

        Requirements: 2.1, 2.3, 3.1, 3.3, 10.1
        """
        logger.debug(
            "mapping_ingredients",
            num_meals=len(meal_plan),
            num_discounts=len(discounts),
            correlation_id=get_correlation_id(),
        )

        # Convert discounts to dict format for ingredient mapper
        available_products = [
            {
                "name": d.product_name,
                "product_name": d.product_name,
                "store_name": d.store_name,
                "store": d.store_name,
                "discount_percent": d.discount_percent,
                "price": float(d.discount_price),
                "discount_price": float(d.discount_price),
            }
            for d in discounts
        ]

        # Map each meal to ingredients
        all_mappings = []

        for meal in meal_plan:
            mapping_input = IngredientMappingInput(
                meal_name=meal,
                ingredients=[meal],  # Use meal name as ingredient for simplicity
                available_products=available_products,
                match_threshold=0.6,
                max_matches_per_ingredient=5,
            )

            try:
                mapping_result = await self.ingredient_mapper.run(mapping_input)
                all_mappings.append(mapping_result)
            except AgentError as e:
                logger.warning(
                    "ingredient_mapping_failed_for_meal",
                    meal=meal,
                    error=str(e),
                    correlation_id=get_correlation_id(),
                )
                # Continue with other meals
                continue

        # Combine all mappings
        if all_mappings:
            # Use the first mapping as base and combine others
            combined = all_mappings[0]
            for mapping in all_mappings[1:]:
                combined.mappings.extend(mapping.mappings)
                combined.total_ingredients += mapping.total_ingredients
                combined.ingredients_with_matches += mapping.ingredients_with_matches
                combined.unmapped_ingredients.extend(mapping.unmapped_ingredients)

            # Recalculate coverage
            if combined.total_ingredients > 0:
                combined.coverage_percent = (
                    combined.ingredients_with_matches / combined.total_ingredients * 100.0
                )

            return combined
        # Return empty mapping as fallback
        from .ingredient_mapper_agent import IngredientMappingOutput

        return IngredientMappingOutput(
            meal_name="fallback",
            mappings=[],
            total_ingredients=len(meal_plan),
            ingredients_with_matches=0,
            coverage_percent=0.0,
            unmapped_ingredients=meal_plan,
        )

    async def _optimize_purchases(
        self,
        ingredient_mappings: Any,
        preferences: OptimizationPreferences,
        location: Location,
        timeframe: Timeframe,
    ) -> Any:
        """
        Optimize purchases using MultiCriteriaOptimizerService.

        Args:
            ingredient_mappings: Ingredient-to-product mappings
            preferences: Optimization preferences
            location: User's location
            timeframe: Shopping timeframe

        Returns:
            OptimizationOutput with optimized purchases

        Requirements: 2.1, 3.1, 3.3, 10.1
        """
        logger.debug(
            "optimizing_purchases",
            num_mappings=len(ingredient_mappings.mappings),
            correlation_id=get_correlation_id(),
        )

        # Convert mappings to ingredient_matches format
        ingredient_matches: dict[str, list[dict[str, Any]]] = {}

        for mapping in ingredient_mappings.mappings:
            if mapping.has_matches:
                ingredient_matches[mapping.ingredient] = [
                    {
                        "product_name": match.product_name,
                        "store_name": match.store_name,
                        "store_location": {"latitude": 0.0, "longitude": 0.0},  # Placeholder
                        "original_price": match.price / (1 - match.discount_percent / 100),
                        "discount_price": match.price,
                        "discount_percent": match.discount_percent,
                        "expiration_date": date.today() + timedelta(days=7),  # Placeholder
                        "is_organic": False,  # Placeholder
                        "store_address": "",
                        "travel_distance_km": 0.0,
                        "travel_time_minutes": 0.0,
                    }
                    for match in mapping.matched_products
                ]

        optimization_input = OptimizationInput(
            ingredient_matches=ingredient_matches,
            preferences=preferences,
            user_location=location,
            timeframe_start=timeframe.start_date,
            timeframe_end=timeframe.end_date,
        )

        return self.optimizer.optimize(optimization_input)

    async def _format_output(
        self, optimization_result: Any, location: Location
    ) -> ShoppingRecommendation:
        """
        Format output with tips and motivation using OutputFormatterAgent.

        Args:
            optimization_result: Optimization result with purchases
            location: User's location

        Returns:
            Complete ShoppingRecommendation

        Requirements: 2.1, 2.3, 3.1, 3.3, 10.1
        """
        logger.debug(
            "formatting_output",
            num_purchases=len(optimization_result.purchases),
            total_savings=float(optimization_result.total_savings),
            correlation_id=get_correlation_id(),
        )

        # Build store summary
        stores = [
            {
                "name": store_name,
                "items": item_count,
                "address": "",  # Placeholder
                "distance_km": 0.0,  # Placeholder
            }
            for store_name, item_count in optimization_result.store_summary.items()
        ]

        # Estimate time savings (5 minutes per store avoided)
        baseline_stores = 5  # Assume baseline of 5 stores without optimization
        stores_saved = max(0, baseline_stores - optimization_result.unique_stores)
        time_savings = stores_saved * 5.0  # 5 minutes per store

        formatting_input = FormattingInput(
            purchases=optimization_result.purchases,
            total_savings=optimization_result.total_savings,
            time_savings=time_savings,
            stores=stores,
            num_tips=5,
        )

        try:
            formatting_result = await self.output_formatter.run(formatting_input)
            return formatting_result.formatted_recommendation
        except AgentError as e:
            logger.warning(
                "output_formatting_failed_using_fallback",
                error=str(e),
                correlation_id=get_correlation_id(),
            )
            # Return basic recommendation without AI-generated tips
            return ShoppingRecommendation(
                purchases=optimization_result.purchases,
                total_savings=optimization_result.total_savings,
                time_savings=time_savings,
                tips=[
                    "Shop early in the morning for best selection",
                    "Bring reusable bags to reduce waste",
                    "Check expiration dates carefully",
                ],
                motivation_message=f"Great planning! You're saving {optimization_result.total_savings} kr.",
                stores=stores,
            )

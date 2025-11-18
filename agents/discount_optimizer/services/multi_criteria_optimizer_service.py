"""
MultiCriteriaOptimizer Service - Deterministic purchase optimization.

This module implements multi-criteria optimization as a pure Python service with:
- Typed input/output using Pydantic models
- Multi-criteria scoring algorithm (savings, distance, organic preference)
- Store consolidation logic to minimize shopping trips
- Structured logging with optimization decisions
- Type-safe calculations using Decimal for financial precision

This is a SERVICE (not an Agent) - it uses deterministic business logic,
not AI. No Gemini API calls are made.

Requirements: 2.1, 2.3, 3.1, 3.3
"""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from agents.discount_optimizer.domain.models import (
    DiscountItem,
    Location,
    OptimizationPreferences,
    Purchase,
)
from agents.discount_optimizer.logging import get_logger, set_agent_context


# Get logger for this module
logger = get_logger(__name__)


class ProductOption(BaseModel):
    """
    A product option with scoring details.

    Attributes:
        product_name: Name of the product
        store_name: Name of the store
        discount_price: Discounted price
        original_price: Original price before discount
        savings: Amount saved
        discount_percent: Discount percentage
        expiration_date: Date when discount expires
        is_organic: Whether product is organic
        store_location: Geographic location of store
        distance_km: Distance to store in kilometers
        score: Calculated optimization score
    """

    product_name: str
    store_name: str
    discount_price: Decimal
    original_price: Decimal
    savings: Decimal
    discount_percent: float
    expiration_date: date
    is_organic: bool
    store_location: Location
    distance_km: float = 0.0
    score: float = 0.0


class OptimizationInput(BaseModel):
    """
    Input model for multi-criteria optimization.

    Attributes:
        ingredient_matches: Dictionary mapping ingredients to lists of discount items
        preferences: User's optimization preferences
        user_location: User's geographic location
        timeframe_start: Start date of shopping timeframe
        timeframe_end: End date of shopping timeframe

    Example:
        >>> from datetime import date
        >>> input_data = OptimizationInput(
        ...     ingredient_matches={"ground beef": [...]},
        ...     preferences=OptimizationPreferences(maximize_savings=True),
        ...     user_location=Location(latitude=55.6761, longitude=12.5683),
        ...     timeframe_start=date(2025, 11, 15),
        ...     timeframe_end=date(2025, 11, 22),
        ... )
    """

    ingredient_matches: dict[str, list[dict[str, Any]]] = Field(
        description="Dictionary mapping ingredients to lists of discount items"
    )
    preferences: OptimizationPreferences = Field(description="User's optimization preferences")
    user_location: Location = Field(
        description="User's geographic location for distance calculations"
    )
    timeframe_start: date = Field(description="Start date of shopping timeframe")
    timeframe_end: date = Field(description="End date of shopping timeframe")

    @field_validator("timeframe_end")
    @classmethod
    def validate_timeframe(cls, v: date, info: Any) -> date:
        """Ensure end date is after start date."""
        if "timeframe_start" in info.data and v < info.data["timeframe_start"]:
            raise ValueError("timeframe_end must be after timeframe_start")
        return v


class OptimizationOutput(BaseModel):
    """
    Output model from multi-criteria optimization.

    Attributes:
        purchases: List of optimized purchase recommendations
        total_savings: Total amount saved across all purchases
        total_items: Total number of items to purchase
        unique_stores: Number of unique stores to visit
        store_summary: Summary of items per store
        optimization_notes: Notes about optimization decisions

    Example:
        >>> output = OptimizationOutput(
        ...     purchases=[...],
        ...     total_savings=Decimal("45.50"),
        ...     total_items=8,
        ...     unique_stores=2,
        ...     store_summary={"Føtex": 5, "Netto": 3},
        ...     optimization_notes="Consolidated shopping to 2 stores for convenience",
        ... )
    """

    purchases: list[Purchase] = Field(description="List of optimized purchase recommendations")
    total_savings: Decimal = Field(ge=0, description="Total amount saved across all purchases")
    total_items: int = Field(ge=0, description="Total number of items to purchase")
    unique_stores: int = Field(ge=0, description="Number of unique stores to visit")
    store_summary: dict[str, int] = Field(description="Summary of items per store")
    optimization_notes: str = Field(default="", description="Notes about optimization decisions")


class MultiCriteriaOptimizerService:
    """
    Service for multi-criteria purchase optimization.

    This service optimizes product-store combinations based on multiple criteria:
    - Maximize savings: Prioritize products with highest discounts
    - Minimize stores: Consolidate purchases to fewer stores
    - Prefer organic: Prioritize organic products when available

    The service uses a weighted scoring algorithm that balances these criteria
    based on user preferences. It also implements store consolidation logic
    to minimize shopping trips while maintaining good value.

    This is a SERVICE (not an Agent):
    - Uses deterministic business logic (math, filtering, sorting)
    - No AI/Gemini API calls
    - Validates inputs/outputs with Pydantic
    - Includes structured logging
    - Uses Decimal for financial calculations

    Example:
        >>> service = MultiCriteriaOptimizerService()
        >>> input_data = OptimizationInput(
        ...     ingredient_matches={"ground beef": [...]},
        ...     preferences=OptimizationPreferences(maximize_savings=True),
        ...     user_location=Location(latitude=55.6761, longitude=12.5683),
        ...     timeframe_start=date(2025, 11, 15),
        ...     timeframe_end=date(2025, 11, 22),
        ... )
        >>> output = service.optimize(input_data)
        >>> print(f"Total savings: ${output.total_savings}")

    Requirements: 2.1, 2.3, 3.1, 3.3
    """

    def __init__(self) -> None:
        """Initialize MultiCriteriaOptimizer service."""
        # Set context for logging
        set_agent_context("multi_criteria_optimizer")

        logger.info("multi_criteria_optimizer_service_initialized")

    def optimize(self, input_data: OptimizationInput) -> OptimizationOutput:
        """
        Optimize product-store combinations using multi-criteria scoring.

        This is the main entry point for the service. It validates input,
        performs optimization using the scoring algorithm, and returns
        structured output with purchase recommendations.

        Args:
            input_data: Validated input data for optimization

        Returns:
            Structured output with optimized purchase recommendations

        Raises:
            ValueError: If input validation fails

        Requirements: 2.1, 2.3, 3.1, 3.3
        """
        logger.info(
            "optimization_started",
            num_ingredients=len(input_data.ingredient_matches),
            preferences=input_data.preferences.model_dump(),
            timeframe_days=(input_data.timeframe_end - input_data.timeframe_start).days,
        )

        try:
            # Optimize purchases using scoring algorithm
            output = self._optimize_purchases(input_data)

            logger.info(
                "optimization_completed",
                total_items=output.total_items,
                unique_stores=output.unique_stores,
                total_savings=float(output.total_savings),
                store_summary=output.store_summary,
            )

            return output

        except Exception as e:
            logger.exception("optimization_failed", error=str(e), error_type=type(e).__name__)
            raise

    def _optimize_purchases(self, input_data: OptimizationInput) -> OptimizationOutput:
        """
        Optimize product-store combinations using multi-criteria scoring.

        This method implements a two-pass optimization algorithm:
        1. First pass: Select best option for each ingredient based on initial scores
        2. Second pass: Re-evaluate with store consolidation bonuses

        The scoring algorithm considers:
        - Savings percentage (discount amount)
        - Distance to store (travel convenience)
        - Organic preference (product quality)
        - Store consolidation (minimize shopping trips)

        Args:
            input_data: Validated input data for optimization

        Returns:
            Structured output with optimized purchases

        Requirements: 2.1, 2.3, 3.1, 3.3
        """
        purchases: list[Purchase] = []
        store_item_counts: dict[str, int] = {}

        logger.debug(
            "starting_optimization_algorithm", num_ingredients=len(input_data.ingredient_matches)
        )

        # First pass: Select best option for each ingredient
        ingredient_selections: dict[str, DiscountItem] = {}

        for ingredient, discount_options_data in input_data.ingredient_matches.items():
            if not discount_options_data:
                logger.debug("no_matches_for_ingredient", ingredient=ingredient)
                continue

            # Convert dict data to DiscountItem objects
            discount_options = self._parse_discount_items(discount_options_data)

            # Score all options for this ingredient
            best_option = None
            best_score = -1.0

            for option in discount_options:
                # Calculate distance
                distance_km = self._calculate_distance(
                    input_data.user_location, option.store_location
                )

                # Calculate score
                score = self._calculate_score(
                    option, input_data.preferences, distance_km, store_item_counts
                )

                logger.debug(
                    "scored_option",
                    ingredient=ingredient,
                    product=option.product_name,
                    store=option.store_name,
                    score=score,
                    distance_km=distance_km,
                )

                if score > best_score:
                    best_score = score
                    best_option = option

            if best_option:
                ingredient_selections[ingredient] = best_option
                # Update store item counts for consolidation bonus
                store_item_counts[best_option.store_name] = (
                    store_item_counts.get(best_option.store_name, 0) + 1
                )

                logger.debug(
                    "selected_best_option",
                    ingredient=ingredient,
                    product=best_option.product_name,
                    store=best_option.store_name,
                    score=best_score,
                )

        # Second pass: Re-evaluate with consolidation bonuses
        # This ensures store consolidation is properly considered
        logger.debug("starting_second_pass_with_consolidation_bonuses")

        store_item_counts = {}
        final_selections: dict[str, DiscountItem] = {}

        for ingredient, discount_options_data in input_data.ingredient_matches.items():
            if not discount_options_data:
                continue

            discount_options = self._parse_discount_items(discount_options_data)

            best_option = None
            best_score = -1.0

            for option in discount_options:
                distance_km = self._calculate_distance(
                    input_data.user_location, option.store_location
                )

                score = self._calculate_score(
                    option, input_data.preferences, distance_km, store_item_counts
                )

                if score > best_score:
                    best_score = score
                    best_option = option

            if best_option:
                final_selections[ingredient] = best_option
                store_item_counts[best_option.store_name] = (
                    store_item_counts.get(best_option.store_name, 0) + 1
                )

        # Create Purchase objects with optimal purchase days
        total_savings = Decimal("0.00")

        for ingredient, discount_item in final_selections.items():
            # Assign optimal purchase day based on discount expiration
            purchase_day = self._calculate_optimal_purchase_day(
                discount_item.expiration_date, input_data.timeframe_start
            )

            # Calculate savings for this purchase
            savings = discount_item.original_price - discount_item.discount_price
            total_savings += savings

            purchase = Purchase(
                product_name=discount_item.product_name,
                store_name=discount_item.store_name,
                purchase_day=purchase_day,
                price=discount_item.discount_price,
                savings=savings,
                meal_association=ingredient,
            )

            purchases.append(purchase)

            logger.debug(
                "created_purchase",
                product=purchase.product_name,
                store=purchase.store_name,
                price=float(purchase.price),
                savings=float(purchase.savings),
                purchase_day=purchase.purchase_day.isoformat(),
            )

        # Generate optimization notes
        optimization_notes = self._generate_optimization_notes(
            input_data.preferences, store_item_counts, total_savings
        )

        return OptimizationOutput(
            purchases=purchases,
            total_savings=total_savings,
            total_items=len(purchases),
            unique_stores=len(store_item_counts),
            store_summary=store_item_counts,
            optimization_notes=optimization_notes,
        )

    def _parse_discount_items(
        self, discount_options_data: Sequence[dict[str, Any] | DiscountItem]
    ) -> list[DiscountItem]:
        """
        Parse discount item dictionaries into DiscountItem objects.

        Args:
            discount_options_data: List of discount item dictionaries or DiscountItem objects

        Returns:
            List of validated DiscountItem objects
        """
        discount_items: list[DiscountItem] = []

        for data in discount_options_data:
            try:
                # Handle different data formats
                if isinstance(data, DiscountItem):
                    discount_items.append(data)
                else:
                    # Parse from dictionary
                    discount_item = DiscountItem(
                        product_name=data.get("product_name", ""),
                        store_name=data.get("store_name", ""),
                        store_location=Location(
                            latitude=data.get("store_location", {}).get("latitude", 0.0),
                            longitude=data.get("store_location", {}).get("longitude", 0.0),
                        ),
                        original_price=Decimal(str(data.get("original_price", 0))),
                        discount_price=Decimal(str(data.get("discount_price", 0))),
                        discount_percent=float(data.get("discount_percent", 0)),
                        expiration_date=data.get("expiration_date", date.today()),
                        is_organic=bool(data.get("is_organic", False)),
                        store_address=data.get("store_address", ""),
                        travel_distance_km=float(data.get("travel_distance_km", 0)),
                        travel_time_minutes=float(data.get("travel_time_minutes", 0)),
                    )
                    discount_items.append(discount_item)
            except (ValueError, KeyError, TypeError) as e:
                logger.warning("failed_to_parse_discount_item", error=str(e), data=data)
                continue

        return discount_items

    def _calculate_distance(self, origin: Location, destination: Location) -> float:
        """
        Calculate distance between two locations using Haversine formula.

        Args:
            origin: Origin location
            destination: Destination location

        Returns:
            Distance in kilometers
        """
        import math

        # Earth's radius in kilometers
        R = 6371.0

        # Convert to radians
        lat1 = math.radians(origin.latitude)
        lon1 = math.radians(origin.longitude)
        lat2 = math.radians(destination.latitude)
        lon2 = math.radians(destination.longitude)

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _calculate_score(
        self,
        purchase_option: DiscountItem,
        preferences: OptimizationPreferences,
        distance_km: float,
        store_item_counts: dict[str, int],
    ) -> float:
        """
        Calculate weighted score for a purchase option based on user preferences.

        The scoring algorithm uses weighted criteria:
        - Savings score: (original_price - discount_price) / original_price
        - Distance score: 1 / (1 + distance_km)
        - Organic score: 1.0 if organic, 0.5 otherwise
        - Consolidation bonus: +0.2 per item already selected from same store

        Args:
            purchase_option: The discount item to score
            preferences: User's optimization preferences
            distance_km: Distance to store in kilometers
            store_item_counts: Dictionary tracking number of items per store

        Returns:
            Weighted score (can exceed 1.0 with bonuses)

        Requirements: 3.1, 3.3
        """
        score = 0.0

        # Count active preferences to determine weights
        active_preferences = sum(
            [preferences.maximize_savings, preferences.minimize_stores, preferences.prefer_organic]
        )

        # Default weights when multiple preferences are selected
        savings_weight = 0.5
        distance_weight = 0.3
        organic_weight = 0.2

        # Adjust weights based on active preferences
        if active_preferences == 1:
            if preferences.maximize_savings:
                savings_weight, distance_weight, organic_weight = 1.0, 0.0, 0.0
            elif preferences.minimize_stores:
                savings_weight, distance_weight, organic_weight = 0.0, 1.0, 0.0
            elif preferences.prefer_organic:
                savings_weight, distance_weight, organic_weight = 0.0, 0.0, 1.0
        elif active_preferences == 2:
            if preferences.maximize_savings and preferences.minimize_stores:
                savings_weight, distance_weight, organic_weight = 0.6, 0.4, 0.0
            elif preferences.maximize_savings and preferences.prefer_organic:
                savings_weight, distance_weight, organic_weight = 0.6, 0.0, 0.4
            elif preferences.minimize_stores and preferences.prefer_organic:
                savings_weight, distance_weight, organic_weight = 0.0, 0.6, 0.4

        # Calculate savings score
        if preferences.maximize_savings:
            savings_ratio = (
                purchase_option.original_price - purchase_option.discount_price
            ) / purchase_option.original_price
            savings_score = float(savings_ratio)
            score += savings_score * savings_weight

            logger.debug(
                "calculated_savings_score",
                product=purchase_option.product_name,
                savings_score=savings_score,
                weight=savings_weight,
                contribution=savings_score * savings_weight,
            )

        # Calculate distance score
        if preferences.minimize_stores:
            distance_score = 1.0 / (1.0 + distance_km)
            score += distance_score * distance_weight

            logger.debug(
                "calculated_distance_score",
                product=purchase_option.product_name,
                distance_km=distance_km,
                distance_score=distance_score,
                weight=distance_weight,
                contribution=distance_score * distance_weight,
            )

        # Calculate organic score
        if preferences.prefer_organic:
            organic_score = 1.0 if purchase_option.is_organic else 0.5
            score += organic_score * organic_weight

            logger.debug(
                "calculated_organic_score",
                product=purchase_option.product_name,
                is_organic=purchase_option.is_organic,
                organic_score=organic_score,
                weight=organic_weight,
                contribution=organic_score * organic_weight,
            )

        # Store consolidation bonus: +0.2 for each additional item from same store
        if purchase_option.store_name in store_item_counts:
            consolidation_bonus = 0.2 * store_item_counts[purchase_option.store_name]
            score += consolidation_bonus

            logger.debug(
                "applied_consolidation_bonus",
                product=purchase_option.product_name,
                store=purchase_option.store_name,
                items_in_store=store_item_counts[purchase_option.store_name],
                bonus=consolidation_bonus,
            )

        return score

    def _calculate_optimal_purchase_day(self, expiration_date: date, timeframe_start: date) -> date:
        """
        Calculate optimal purchase day based on discount expiration.

        Strategy:
        - If expiring within 3 days: Buy immediately (start date)
        - If expiring within 7 days: Buy within first few days (start date)
        - Otherwise: Can buy anytime in timeframe (start date)

        Args:
            expiration_date: Date when discount expires
            timeframe_start: Start date of shopping timeframe

        Returns:
            Optimal purchase date
        """
        days_until_expiration = (expiration_date - timeframe_start).days

        if days_until_expiration <= 3:
            # Expiring soon - buy immediately
            purchase_day = timeframe_start
            logger.debug(
                "urgent_purchase_scheduled",
                expiration_date=expiration_date.isoformat(),
                days_until_expiration=days_until_expiration,
                purchase_day=purchase_day.isoformat(),
            )
        elif days_until_expiration <= 7:
            # Expiring within a week - buy within first few days
            purchase_day = timeframe_start
            logger.debug(
                "soon_expiring_purchase_scheduled",
                expiration_date=expiration_date.isoformat(),
                days_until_expiration=days_until_expiration,
                purchase_day=purchase_day.isoformat(),
            )
        else:
            # Longer-lasting - can buy anytime
            purchase_day = timeframe_start
            logger.debug(
                "flexible_purchase_scheduled",
                expiration_date=expiration_date.isoformat(),
                days_until_expiration=days_until_expiration,
                purchase_day=purchase_day.isoformat(),
            )

        return purchase_day

    def _generate_optimization_notes(
        self,
        preferences: OptimizationPreferences,
        store_summary: dict[str, int],
        total_savings: Decimal,
    ) -> str:
        """
        Generate human-readable notes about optimization decisions.

        Args:
            preferences: User's optimization preferences
            store_summary: Summary of items per store
            total_savings: Total amount saved

        Returns:
            Optimization notes string
        """
        notes_parts = []

        # Describe active preferences
        active_prefs = []
        if preferences.maximize_savings:
            active_prefs.append("maximizing savings")
        if preferences.minimize_stores:
            active_prefs.append("minimizing stores")
        if preferences.prefer_organic:
            active_prefs.append("preferring organic products")

        if active_prefs:
            notes_parts.append(f"Optimized for: {', '.join(active_prefs)}")

        # Describe store consolidation
        num_stores = len(store_summary)
        if num_stores == 1:
            notes_parts.append("All items consolidated to a single store for maximum convenience")
        elif num_stores <= 3:
            notes_parts.append(
                f"Shopping consolidated to {num_stores} stores for good balance of savings and convenience"
            )
        else:
            notes_parts.append(f"Shopping across {num_stores} stores to maximize savings")

        # Describe savings
        if total_savings > 0:
            notes_parts.append(f"Total savings: ${total_savings:.2f}")

        return ". ".join(notes_parts) + "."

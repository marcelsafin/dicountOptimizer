"""
MultiCriteriaOptimizer component for optimizing product-store combinations.
"""

from datetime import date

from .discount_matcher import DiscountMatcher
from .models import DiscountItem, Location, OptimizationPreferences, Purchase


class MultiCriteriaOptimizer:
    """
    Responsible for optimizing product-store combinations based on user preferences.
    Uses a weighted scoring algorithm to balance multiple optimization criteria.
    """

    def __init__(self):
        self.discount_matcher = DiscountMatcher()

    def calculate_score(
        self,
        purchase_option: DiscountItem,
        preferences: OptimizationPreferences,
        user_location: Location,
        store_item_counts: dict[str, int] | None = None,
    ) -> float:
        """
        Calculate weighted score for a purchase option based on user preferences.

        Args:
            purchase_option: The discount item to score
            preferences: User's optimization preferences
            user_location: User's location for distance calculation
            store_item_counts: Dictionary tracking number of items per store (for consolidation bonus)

        Returns:
            Weighted score between 0.0 and 1.0+ (can exceed 1.0 with bonuses)
        """
        score = 0.0
        active_preferences = 0

        # Count active preferences to determine weights
        if preferences.maximize_savings:
            active_preferences += 1
        if preferences.minimize_stores:
            active_preferences += 1
        if preferences.prefer_organic:
            active_preferences += 1

        # Default weights when multiple preferences are selected
        savings_weight = 0.5
        distance_weight = 0.3
        organic_weight = 0.2

        # Adjust weights based on active preferences
        if active_preferences == 1:
            if preferences.maximize_savings:
                savings_weight = 1.0
                distance_weight = 0.0
                organic_weight = 0.0
            elif preferences.minimize_stores:
                savings_weight = 0.0
                distance_weight = 1.0
                organic_weight = 0.0
            elif preferences.prefer_organic:
                savings_weight = 0.0
                distance_weight = 0.0
                organic_weight = 1.0
        elif active_preferences == 2:
            if preferences.maximize_savings and preferences.minimize_stores:
                savings_weight = 0.6
                distance_weight = 0.4
                organic_weight = 0.0
            elif preferences.maximize_savings and preferences.prefer_organic:
                savings_weight = 0.6
                distance_weight = 0.0
                organic_weight = 0.4
            elif preferences.minimize_stores and preferences.prefer_organic:
                savings_weight = 0.0
                distance_weight = 0.6
                organic_weight = 0.4

        # Calculate savings score: (original_price - discount_price) / original_price
        if preferences.maximize_savings:
            savings_score = (
                purchase_option.original_price - purchase_option.discount_price
            ) / purchase_option.original_price
            score += savings_score * savings_weight

        # Calculate distance score: 1 / (1 + distance_km)
        if preferences.minimize_stores:
            distance_km = self.discount_matcher.calculate_distance(
                user_location, purchase_option.store_location
            )
            distance_score = 1.0 / (1.0 + distance_km)
            score += distance_score * distance_weight

        # Calculate organic score
        if preferences.prefer_organic:
            organic_score = 1.0 if purchase_option.is_organic else 0.5
            score += organic_score * organic_weight

        # Store consolidation bonus: +0.2 for each additional item from same store
        if store_item_counts and purchase_option.store_name in store_item_counts:
            consolidation_bonus = 0.2 * store_item_counts[purchase_option.store_name]
            score += consolidation_bonus

        return score

    def optimize(
        self,
        matches: dict[str, list[DiscountItem]],
        preferences: OptimizationPreferences,
        user_location: Location,
        timeframe_start: date,
    ) -> list[Purchase]:
        """
        Optimize product-store combinations for all ingredients based on user preferences.

        Selects the best product-store combination for each ingredient and assigns
        optimal purchase days based on discount expiration and meal timing.

        Args:
            matches: Dictionary mapping ingredients to lists of matching discount items
            preferences: User's optimization preferences
            user_location: User's location for distance calculation
            timeframe_start: Start date of shopping timeframe for purchase day assignment

        Returns:
            List of optimized Purchase recommendations
        """
        purchases: list[Purchase] = []
        store_item_counts: dict[str, int] = {}

        # First pass: Select best option for each ingredient
        ingredient_selections: dict[str, DiscountItem] = {}

        for ingredient, discount_options in matches.items():
            if not discount_options:
                # No matching products found for this ingredient
                continue

            # Score all options for this ingredient
            best_option = None
            best_score = -1.0

            for option in discount_options:
                score = self.calculate_score(option, preferences, user_location, store_item_counts)

                if score > best_score:
                    best_score = score
                    best_option = option

            if best_option:
                ingredient_selections[ingredient] = best_option
                # Update store item counts for consolidation bonus
                store_item_counts[best_option.store_name] = (
                    store_item_counts.get(best_option.store_name, 0) + 1
                )

        # Second pass: Re-evaluate with consolidation bonuses
        # This ensures store consolidation is properly considered
        store_item_counts = {}
        final_selections: dict[str, DiscountItem] = {}

        for ingredient, discount_options in matches.items():
            if not discount_options:
                continue

            best_option = None
            best_score = -1.0

            for option in discount_options:
                score = self.calculate_score(option, preferences, user_location, store_item_counts)

                if score > best_score:
                    best_score = score
                    best_option = option

            if best_option:
                final_selections[ingredient] = best_option
                store_item_counts[best_option.store_name] = (
                    store_item_counts.get(best_option.store_name, 0) + 1
                )

        # Create Purchase objects with optimal purchase days
        for ingredient, discount_item in final_selections.items():
            # Assign optimal purchase day based on discount expiration
            # Buy closer to expiration if it's soon, otherwise buy at start of timeframe
            days_until_expiration = (discount_item.expiration_date - timeframe_start).days

            if days_until_expiration <= 3:
                # If expiring soon, buy on the start date
                purchase_day = timeframe_start
            elif days_until_expiration <= 7:
                # If expiring within a week, buy within first few days
                purchase_day = timeframe_start
            else:
                # For longer-lasting items, can buy anytime in the timeframe
                purchase_day = timeframe_start

            # Calculate savings for this purchase
            savings = discount_item.original_price - discount_item.discount_price

            purchase = Purchase(
                product_name=discount_item.product_name,
                store_name=discount_item.store_name,
                purchase_day=purchase_day,
                price=discount_item.discount_price,
                savings=savings,
                meal_association=ingredient,
            )

            purchases.append(purchase)

        return purchases

"""
SavingsCalculator component for calculating monetary and time savings.
"""

from .discount_matcher import DiscountMatcher
from .models import Location, Purchase


class SavingsCalculator:
    """
    Responsible for calculating monetary and time savings from optimized shopping plan.
    """

    def __init__(self):
        self.discount_matcher = DiscountMatcher()

    def calculate_monetary_savings(self, purchases: list[Purchase]) -> float:
        """
        Calculate total monetary savings by summing all discount savings.

        Args:
            purchases: List of recommended purchases with savings information

        Returns:
            Total monetary savings in currency units
        """
        total_savings = 0.0

        for purchase in purchases:
            total_savings += purchase.savings

        return total_savings

    def calculate_time_savings(self, purchases: list[Purchase], user_location: Location) -> float:
        """
        Calculate time savings using heuristic: 30 min/store + 5 min/km travel.

        Compares baseline time (shopping at closest store) vs optimized plan time.

        Args:
            purchases: List of recommended purchases
            user_location: User's location for distance calculation

        Returns:
            Time savings in hours (can be negative if optimized plan takes longer)
        """
        if not purchases:
            return 0.0

        # Get unique stores from purchases
        stores_in_plan = {}
        for purchase in purchases:
            if purchase.store_name not in stores_in_plan:
                # Find the store location from the first purchase at this store
                stores_in_plan[purchase.store_name] = None

        # Calculate distances for stores in the optimized plan
        # We need to get store locations from the discount data
        from .models import MOCK_DISCOUNTS

        store_locations = {}
        for discount in MOCK_DISCOUNTS:
            if discount.store_name not in store_locations:
                store_locations[discount.store_name] = discount.store_location

        # Calculate baseline time: shopping at closest store
        closest_distance = float("inf")
        for store_name, store_location in store_locations.items():
            distance = self.discount_matcher.calculate_distance(user_location, store_location)
            closest_distance = min(closest_distance, distance)

        # Baseline: 1 store + travel to closest store
        # Time = 30 min for shopping + (5 min/km * distance * 2 for round trip)
        baseline_time_minutes = 30 + (5 * closest_distance * 2)

        # Calculate optimized plan time
        num_stores = len(stores_in_plan)

        # Calculate total travel distance for optimized plan
        total_distance = 0.0
        for store_name in stores_in_plan:
            if store_name in store_locations:
                distance = self.discount_matcher.calculate_distance(
                    user_location, store_locations[store_name]
                )
                # Round trip distance
                total_distance += distance * 2

        # Optimized time = (30 min * number of stores) + (5 min/km * total distance)
        optimized_time_minutes = (30 * num_stores) + (5 * total_distance)

        # Calculate time savings (baseline - optimized)
        # Positive value means time saved, negative means extra time spent
        time_savings_minutes = baseline_time_minutes - optimized_time_minutes

        # Convert to hours
        return time_savings_minutes / 60.0

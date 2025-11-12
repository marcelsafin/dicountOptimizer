"""
DiscountMatcher component for filtering and matching discount data.
"""

import math
from typing import List
from datetime import date

from .models import DiscountItem, Location, Timeframe, MOCK_DISCOUNTS


class DiscountMatcher:
    """
    Responsible for loading and filtering discount data based on location and timeframe.
    """
    
    def load_discounts(self) -> List[DiscountItem]:
        """
        Load mock discount data.
        
        Returns:
            List of all available discount items
        """
        return MOCK_DISCOUNTS.copy()
    
    def calculate_distance(self, loc1: Location, loc2: Location) -> float:
        """
        Calculate distance between two coordinates using Haversine formula.
        
        Args:
            loc1: First location with latitude and longitude
            loc2: Second location with latitude and longitude
            
        Returns:
            Distance in kilometers
        """
        # Earth's radius in kilometers
        R = 6371.0
        
        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(loc1.latitude)
        lon1_rad = math.radians(loc1.longitude)
        lat2_rad = math.radians(loc2.latitude)
        lon2_rad = math.radians(loc2.longitude)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        
        return distance
    
    def filter_by_location(
        self, 
        discounts: List[DiscountItem], 
        user_location: Location, 
        max_distance_km: float = 20.0
    ) -> List[DiscountItem]:
        """
        Filter discounts within max_distance_km radius from user location.
        
        Args:
            discounts: List of discount items to filter
            user_location: User's location coordinates
            max_distance_km: Maximum distance in kilometers (default: 20.0)
            
        Returns:
            List of discounts within the specified radius
        """
        filtered = []
        
        for discount in discounts:
            distance = self.calculate_distance(user_location, discount.store_location)
            if distance <= max_distance_km:
                filtered.append(discount)
        
        return filtered
    
    def filter_by_timeframe(
        self, 
        discounts: List[DiscountItem], 
        timeframe: Timeframe
    ) -> List[DiscountItem]:
        """
        Filter out discounts with expiration dates outside the user's shopping timeframe.
        
        Args:
            discounts: List of discount items to filter
            timeframe: User's shopping timeframe
            
        Returns:
            List of discounts that are valid within the timeframe
        """
        filtered = []
        
        for discount in discounts:
            # Include discount if expiration date is >= timeframe start date
            if discount.expiration_date >= timeframe.start_date:
                filtered.append(discount)
        
        return filtered

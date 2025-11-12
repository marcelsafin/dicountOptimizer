"""
DiscountMatcher component for filtering and matching discount data.
"""

import math
import os
from typing import List, Optional
from datetime import date

from .models import DiscountItem, Location, Timeframe, MOCK_DISCOUNTS
from .salling_api_client import SallingAPIClient


class DiscountMatcher:
    """
    Responsible for loading and filtering discount data based on location and timeframe.
    """
    
    def __init__(self, use_real_api: bool = True):
        """
        Initialize the DiscountMatcher.
        
        Args:
            use_real_api: If True, use Salling API; if False, use mock data (default: True)
        """
        self.use_real_api = use_real_api
        self.api_client: Optional[SallingAPIClient] = None
        
        # Initialize API client if using real API
        if self.use_real_api:
            api_key = os.getenv("SALLING_GROUP_API_KEY")
            if api_key:
                try:
                    self.api_client = SallingAPIClient(api_key)
                except Exception as e:
                    print(f"Warning: Failed to initialize Salling API client: {e}")
                    print("Falling back to mock data")
                    self.use_real_api = False
            else:
                print("Warning: SALLING_GROUP_API_KEY not found. Using mock data.")
                self.use_real_api = False
    
    def load_discounts(self, location: Optional[Location] = None, radius_km: float = 20.0) -> List[DiscountItem]:
        """
        Load discount data from Salling API or mock data.
        
        Args:
            location: User's location (required for real API)
            radius_km: Search radius in kilometers (default: 20.0)
        
        Returns:
            List of all available discount items
        """
        # Use real API if enabled and location is provided
        if self.use_real_api and self.api_client and location:
            try:
                # Fetch campaigns from Salling API
                discounts = self.api_client.fetch_campaigns(location, radius_km)
                
                # If API returns no results, fall back to cached data or mock data
                if not discounts:
                    print("Warning: No discounts found from API. Checking cache...")
                    cached = self.api_client.get_cached_campaigns()
                    if cached:
                        return cached
                    else:
                        print("No cached data available. Using mock data.")
                        return MOCK_DISCOUNTS.copy()
                
                return discounts
                
            except Exception as e:
                print(f"Error fetching from Salling API: {e}")
                print("Falling back to cached data or mock data")
                
                # Try to use cached data
                if self.api_client:
                    cached = self.api_client.get_cached_campaigns()
                    if cached:
                        return cached
                
                # Fall back to mock data
                return MOCK_DISCOUNTS.copy()
        
        # Use mock data as fallback
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

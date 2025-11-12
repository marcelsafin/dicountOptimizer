"""
Salling Group API client for fetching real discount data from Danish stores.

The Salling Group operates major Danish grocery chains including:
- Netto
- Føtex
- Bilka
- BR

API Documentation: https://developer.sallinggroup.com/
"""

import os
import json
import requests
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from dataclasses import asdict

from .models import DiscountItem, Location


class SallingAPIClient:
    """
    Client for interacting with the Salling Group API to fetch discount campaigns.
    """
    
    BASE_URL = "https://api.sallinggroup.com/v1"
    CACHE_TTL_HOURS = 24
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Salling API client.
        
        Args:
            api_key: Salling Group API key (defaults to SALLING_GROUP_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("SALLING_GROUP_API_KEY")
        if not self.api_key:
            raise ValueError("Salling Group API key is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Simple in-memory cache
        self._cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None
    
    def fetch_campaigns(
        self, 
        location: Location, 
        radius_km: float = 2.0
    ) -> List[DiscountItem]:
        """
        Fetch discount campaigns from Salling Group API.
        
        Args:
            location: User's location coordinates
            radius_km: Search radius in kilometers (default: 20.0)
            
        Returns:
            List of DiscountItem objects
            
        Raises:
            requests.RequestException: If API request fails
        """
        # Check cache first
        cached_data = self.get_cached_campaigns()
        if cached_data is not None:
            return cached_data
        
        try:
            # Salling API uses kilometers for radius (max 100km, default 2km)
            radius_km_capped = min(radius_km, 100.0)
            
            # API endpoint for food waste offers
            url = f"{self.BASE_URL}/food-waste/"
            
            # Salling API expects geo parameter in format "latitude,longitude"
            params = {
                "geo": f"{location.latitude},{location.longitude}",
                "radius": radius_km_capped
            }
            
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                raise requests.RequestException("API rate limit exceeded. Please try again later.")
            
            # Debug: print response for bad requests
            if response.status_code >= 400:
                print(f"API Error Response: {response.text}")
            
            response.raise_for_status()
            
            # Parse the response
            json_data = response.json()
            campaigns = self.parse_campaign_response(json_data)
            
            # Cache the results
            self.cache_campaigns(campaigns)
            
            return campaigns
            
        except requests.Timeout:
            raise requests.RequestException("API request timed out")
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch campaigns: {str(e)}")
    
    def parse_campaign_response(self, json_data: List[Dict]) -> List[DiscountItem]:
        """
        Parse Salling Group API response and convert to DiscountItem objects.
        
        The Salling API returns food waste offers with the following structure:
        {
            "store": {
                "name": "Netto",
                "address": {
                    "street": "Street name",
                    "city": "Copenhagen",
                    "zip": "2100"
                },
                "coordinates": [12.5683, 55.6761],
                "brand": "netto"
            },
            "clearances": [
                {
                    "product": {
                        "description": "Product name",
                        "ean": "product code"
                    },
                    "offer": {
                        "originalPrice": 100.0,
                        "newPrice": 50.0,
                        "percentDiscount": 50,
                        "stock": 5,
                        "stockUnit": "kg",
                        "endTime": "2025-11-15T20:00:00Z"
                    }
                }
            ]
        }
        
        Args:
            json_data: Raw JSON response from API
            
        Returns:
            List of DiscountItem objects
        """
        discount_items = []
        
        for store_data in json_data:
            try:
                # Extract store information
                store = store_data.get("store", {})
                store_name = store.get("name", "Unknown Store")
                store_address = store.get("address", {})
                store_city = store_address.get("city", "")
                store_street = store_address.get("street", "")
                
                # Get store coordinates
                coordinates = store.get("coordinates", [])
                if len(coordinates) >= 2:
                    # Salling API returns [longitude, latitude]
                    store_location = Location(
                        latitude=coordinates[1],
                        longitude=coordinates[0]
                    )
                else:
                    # Skip stores without valid coordinates
                    continue
                
                # Process each clearance item at this store
                clearances = store_data.get("clearances", [])
                
                for clearance in clearances:
                    try:
                        # Extract product information
                        product = clearance.get("product", {})
                        product_name = product.get("description", "Unknown Product")
                        
                        # Extract offer information
                        offer = clearance.get("offer", {})
                        original_price = offer.get("originalPrice", 0.0)
                        discount_price = offer.get("newPrice", 0.0)
                        discount_percent = offer.get("percentDiscount", 0)
                        
                        # Extract expiration information
                        end_time_str = offer.get("endTime")
                        
                        if end_time_str:
                            # Parse ISO format datetime
                            end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                            expiration_date = end_time.date()
                        else:
                            # Default to 3 days from now if no expiration
                            expiration_date = date.today() + timedelta(days=3)
                        
                        # Determine if product is organic
                        # Check for Danish organic keywords in product name
                        is_organic = any(
                            keyword in product_name.lower() 
                            for keyword in ["økologisk", "organic", "øko", "bio"]
                        )
                        
                        # Create full store address
                        full_address = f"{store_street}, {store_city}".strip(", ")
                        
                        # Create DiscountItem
                        discount_item = DiscountItem(
                            product_name=product_name,
                            store_name=f"{store_name} {store_city}".strip(),
                            store_location=store_location,
                            original_price=original_price,
                            discount_price=discount_price,
                            discount_percent=discount_percent,
                            expiration_date=expiration_date,
                            is_organic=is_organic,
                            store_address=full_address,
                            travel_distance_km=0.0,  # Will be calculated later by Google Maps
                            travel_time_minutes=0.0  # Will be calculated later by Google Maps
                        )
                        
                        discount_items.append(discount_item)
                        
                    except (KeyError, ValueError, TypeError) as e:
                        # Skip malformed clearance items but continue processing
                        print(f"Warning: Failed to parse clearance item: {e}")
                        continue
                
            except (KeyError, ValueError, TypeError) as e:
                # Skip malformed store data but continue processing
                print(f"Warning: Failed to parse store data: {e}")
                continue
        
        return discount_items
    
    def get_cached_campaigns(self) -> Optional[List[DiscountItem]]:
        """
        Retrieve cached campaign data if still valid.
        
        Returns:
            List of DiscountItem objects if cache is valid, None otherwise
        """
        if not self._cache or not self._cache_timestamp:
            return None
        
        # Check if cache has expired
        cache_age = datetime.now() - self._cache_timestamp
        if cache_age > timedelta(hours=self.CACHE_TTL_HOURS):
            # Cache expired
            self._cache = {}
            self._cache_timestamp = None
            return None
        
        return self._cache.get("campaigns")
    
    def cache_campaigns(self, campaigns: List[DiscountItem], ttl_hours: int = 24):
        """
        Cache campaign data with specified TTL.
        
        Args:
            campaigns: List of DiscountItem objects to cache
            ttl_hours: Time-to-live in hours (default: 24)
        """
        self._cache = {"campaigns": campaigns}
        self._cache_timestamp = datetime.now()
        self.CACHE_TTL_HOURS = ttl_hours
    
    def clear_cache(self):
        """Clear the campaign cache."""
        self._cache = {}
        self._cache_timestamp = None

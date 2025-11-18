"""
GoogleMapsService component for geocoding, finding nearby stores, and calculating distances.
Uses hardcoded mock data for testing without requiring Google Maps API keys.
"""

import math
import os
from datetime import UTC, datetime, timedelta

from .models import Location


class GoogleMapsService:
    """Service for interacting with Google Maps APIs (mock implementation)."""

    def __init__(self, api_key: str | None = None, use_mock: bool = True):
        """
        Initialize the Google Maps service.

        Args:
            api_key: Google Maps API key (not used in mock mode)
            use_mock: If True, uses hardcoded mock data instead of real API calls
        """
        self.use_mock = use_mock
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")

        # Simple in-memory cache for geocoding results (24h TTL)
        self._geocoding_cache: dict[str, tuple[Location, datetime]] = {}
        self._cache_ttl_hours = 24

        # Mock stores near Copenhagen/Malmö area
        self._mock_stores = [
            {
                "name": "Netto Nørrebro",
                "location": Location(55.6872, 12.5537),
                "address": "Nørrebrogade 45, 2200 København N",
            },
            {
                "name": "Føtex Vesterbro",
                "location": Location(55.6692, 12.5515),
                "address": "Vesterbrogade 89, 1620 København V",
            },
            {
                "name": "Rema 1000 Østerbro",
                "location": Location(55.7008, 12.5731),
                "address": "Østerbrogade 112, 2100 København Ø",
            },
            {
                "name": "Netto Amager",
                "location": Location(55.6531, 12.5989),
                "address": "Amagerbrogade 156, 2300 København S",
            },
            {
                "name": "Føtex City",
                "location": Location(55.6761, 12.5683),
                "address": "Frederiksborggade 21, 1360 København K",
            },
            {
                "name": "Bilka Malmö",
                "location": Location(55.6050, 13.0038),
                "address": "Jörgen Kocksgatan 5, 211 20 Malmö",
            },
            {
                "name": "ICA Maxi Malmö",
                "location": Location(55.5950, 13.0150),
                "address": "Dalaplan 5, 211 20 Malmö",
            },
            {
                "name": "Willys Malmö",
                "location": Location(55.6100, 13.0000),
                "address": "Södra Förstadsgatan 50, 211 43 Malmö",
            },
        ]

    def geocode_address(self, address: str) -> Location:
        """
        Convert an address to geographic coordinates.
        In mock mode, returns predefined locations for known addresses.

        Args:
            address: Street address, city, or postal code

        Returns:
            Location object with latitude and longitude

        Raises:
            ValueError: If address cannot be geocoded
        """
        # Check cache first
        if address in self._geocoding_cache:
            cached_location, cached_time = self._geocoding_cache[address]
            if datetime.now(UTC) - cached_time < timedelta(hours=self._cache_ttl_hours):
                return cached_location

        if self.use_mock:
            # Mock geocoding for common addresses
            address_lower = address.lower()

            # Predefined locations
            mock_geocoding = {
                "malmö": Location(55.6050, 13.0038),
                "malmo": Location(55.6050, 13.0038),
                "copenhagen": Location(55.6761, 12.5683),
                "københavn": Location(55.6761, 12.5683),
                "nørrebro": Location(55.6872, 12.5537),
                "vesterbro": Location(55.6692, 12.5515),
                "østerbro": Location(55.7008, 12.5731),
                "amager": Location(55.6531, 12.5989),
            }

            # Try to find a match
            for key, location in mock_geocoding.items():
                if key in address_lower:
                    self._geocoding_cache[address] = (location, datetime.now(UTC))
                    return location

            # Default to user's hardcoded position if no match
            default_location = Location(55.680535554805324, 12.570640208986235)
            self._geocoding_cache[address] = (default_location, datetime.now(UTC))
            return default_location

        # Real API implementation would go here
        raise NotImplementedError("Real Google Maps API not implemented. Use mock mode.")

    def find_nearby_stores(self, location: Location, radius_km: float = 20.0) -> list[dict]:
        """
        Find nearby grocery stores.
        In mock mode, returns predefined stores within the specified radius.

        Args:
            location: User's location
            radius_km: Search radius in kilometers (default 20km)

        Returns:
            List of store dictionaries with name, location, and address
        """
        if self.use_mock:
            # Filter mock stores by distance
            nearby_stores = []
            for store in self._mock_stores:
                distance = self._calculate_haversine_distance(location, store["location"])
                if distance <= radius_km:
                    nearby_stores.append(
                        {
                            "name": store["name"],
                            "location": store["location"],
                            "address": store["address"],
                            "place_id": f"mock_{store['name'].lower().replace(' ', '_')}",
                        }
                    )

            return nearby_stores

        # Real API implementation would go here
        raise NotImplementedError("Real Google Maps API not implemented. Use mock mode.")

    def calculate_distance_matrix(
        self, origin: Location, destinations: list[Location]
    ) -> dict[str, dict[str, float]]:
        """
        Calculate travel distance and time from origin to multiple destinations.
        In mock mode, uses Haversine distance and estimates travel time.

        Args:
            origin: Starting location
            destinations: List of destination locations

        Returns:
            Dictionary mapping destination coordinates to distance (km) and duration (minutes)
            Format: {
                "lat,lng": {
                    "distance_km": float,
                    "duration_minutes": float
                }
            }
        """
        if not destinations:
            return {}

        if self.use_mock:
            results = {}
            for dest in destinations:
                dest_key = f"{dest.latitude},{dest.longitude}"

                # Calculate Haversine distance
                distance_km = self._calculate_haversine_distance(origin, dest)

                # Estimate travel time (assume average speed of 40 km/h in city)
                duration_minutes = (distance_km / 40.0) * 60.0

                results[dest_key] = {
                    "distance_km": distance_km,
                    "duration_minutes": duration_minutes,
                }

            return results

        # Real API implementation would go here
        raise NotImplementedError("Real Google Maps API not implemented. Use mock mode.")

    def _calculate_haversine_distance(self, loc1: Location, loc2: Location) -> float:
        """
        Calculate the great circle distance between two points on Earth.

        Args:
            loc1: First location
            loc2: Second location

        Returns:
            Distance in kilometers
        """
        # Earth's radius in kilometers
        R = 6371.0

        # Convert degrees to radians
        lat1_rad = math.radians(loc1.latitude)
        lon1_rad = math.radians(loc1.longitude)
        lat2_rad = math.radians(loc2.latitude)
        lon2_rad = math.radians(loc2.longitude)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        return R * c

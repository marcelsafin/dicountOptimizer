"""Protocol interfaces for dependency injection.

This module defines Protocol classes that establish contracts for external
dependencies. Using Protocols enables structural subtyping (duck typing with
type safety) and makes the system testable through dependency injection.

All protocols are marked as @runtime_checkable to enable isinstance() checks.
"""

from typing import Protocol, runtime_checkable
from .models import Location, DiscountItem, Timeframe


@runtime_checkable
class DiscountRepository(Protocol):
    """Protocol for discount data sources.
    
    Implementations of this protocol fetch discount information from external
    sources (e.g., Salling Group API, other retail APIs) and return validated
    DiscountItem objects.
    
    Example:
        >>> class SallingDiscountRepository:
        ...     async def fetch_discounts(
        ...         self, location: Location, radius_km: float
        ...     ) -> list[DiscountItem]:
        ...         # Implementation here
        ...         pass
        ...     
        ...     async def health_check(self) -> bool:
        ...         # Implementation here
        ...         return True
        >>> 
        >>> repo: DiscountRepository = SallingDiscountRepository()
    """
    
    async def fetch_discounts(
        self, 
        location: Location, 
        radius_km: float
    ) -> list[DiscountItem]:
        """Fetch discounts near a given location.
        
        Args:
            location: Geographic location to search around
            radius_km: Search radius in kilometers
            
        Returns:
            List of discount items found within the specified radius
            
        Raises:
            APIError: If the external API call fails after retries
            ValidationError: If the API response cannot be validated
        """
        ...
    
    async def health_check(self) -> bool:
        """Check if the discount repository is healthy and accessible.
        
        Returns:
            True if the repository is healthy, False otherwise
        """
        ...


@runtime_checkable
class GeocodingService(Protocol):
    """Protocol for geocoding and distance calculation services.
    
    Implementations of this protocol provide geographic services such as
    converting addresses to coordinates and calculating distances between
    locations.
    
    Example:
        >>> class GoogleMapsService:
        ...     async def geocode_address(self, address: str) -> Location:
        ...         # Implementation here
        ...         pass
        ...     
        ...     async def calculate_distance(
        ...         self, origin: Location, destination: Location
        ...     ) -> float:
        ...         # Implementation here
        ...         return 5.2
        >>> 
        >>> service: GeocodingService = GoogleMapsService()
    """
    
    async def geocode_address(self, address: str) -> Location:
        """Convert a text address to geographic coordinates.
        
        Args:
            address: Text address to geocode (e.g., "Nørrebrogade 20, Copenhagen")
            
        Returns:
            Location object with latitude and longitude coordinates
            
        Raises:
            APIError: If the geocoding API call fails after retries
            ValidationError: If the address cannot be geocoded
        """
        ...
    
    async def calculate_distance(
        self, 
        origin: Location, 
        destination: Location
    ) -> float:
        """Calculate distance between two locations.
        
        Args:
            origin: Starting location
            destination: Ending location
            
        Returns:
            Distance in kilometers
            
        Note:
            Implementations may use different calculation methods:
            - Haversine formula for great-circle distance
            - Road distance via routing APIs
            - Manhattan distance for grid-based calculations
        """
        ...
    
    async def health_check(self) -> bool:
        """Check if the geocoding service is healthy and accessible.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        ...


@runtime_checkable
class CacheRepository(Protocol):
    """Protocol for caching layer.
    
    Implementations of this protocol provide key-value caching with TTL
    (time-to-live) support. This enables performance optimization by
    reducing redundant API calls.
    
    Example:
        >>> class RedisCacheRepository:
        ...     async def get(self, key: str) -> bytes | None:
        ...         # Implementation here
        ...         pass
        ...     
        ...     async def set(
        ...         self, key: str, value: bytes, ttl_seconds: int
        ...     ) -> None:
        ...         # Implementation here
        ...         pass
        >>> 
        >>> cache: CacheRepository = RedisCacheRepository()
    """
    
    async def get(self, key: str) -> bytes | None:
        """Get cached value by key.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Cached value as bytes if found, None if not found or expired
            
        Note:
            Implementations should handle serialization/deserialization
            of complex objects. Consider using pickle, json, or msgpack.
        """
        ...
    
    async def set(self, key: str, value: bytes, ttl_seconds: int) -> None:
        """Set cached value with TTL.
        
        Args:
            key: Cache key to set
            value: Value to cache as bytes
            ttl_seconds: Time-to-live in seconds (cache expiration time)
            
        Note:
            If a key already exists, implementations should overwrite it
            with the new value and reset the TTL.
        """
        ...
    
    async def health_check(self) -> bool:
        """Check if the cache is healthy and operational.
        
        Returns:
            True if the cache is operational, False otherwise
        """
        ...

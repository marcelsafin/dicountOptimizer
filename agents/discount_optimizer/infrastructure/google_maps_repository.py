"""Async repository for Google Maps API with connection pooling and retry logic.

This module implements the GeocodingService protocol for the Google Maps API,
providing type-safe, async access to geocoding and distance calculation services
with automatic retries, connection pooling, and comprehensive error handling.
"""

import httpx
from typing import Any
from math import radians, sin, cos, sqrt, atan2
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import structlog

from ..domain.models import Location
from ..domain.protocols import GeocodingService
from ..domain.exceptions import APIError, ValidationError
from ..config import settings
from ..metrics import get_metrics_collector

logger = structlog.get_logger(__name__)
metrics_collector = get_metrics_collector()


class GoogleMapsRepository:
    """Repository for Google Maps API with connection pooling and retry logic.
    
    This repository implements the GeocodingService protocol and provides
    async access to Google Maps services. It includes:
    - Automatic retry with exponential backoff
    - HTTP connection pooling for performance
    - Comprehensive error handling
    - Haversine distance calculation
    - Context manager support for resource cleanup
    
    API Documentation: https://developers.google.com/maps/documentation
    
    Example:
        >>> async with GoogleMapsRepository(api_key="your-key") as repo:
        ...     location = await repo.geocode_address("Nørrebrogade 20, Copenhagen")
        ...     print(f"Location: {location.latitude}, {location.longitude}")
    """
    
    GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    
    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        """Initialize the Google Maps API repository.
        
        Args:
            api_key: Google Maps API key (defaults to settings.get_google_maps_key())
            client: Optional pre-configured httpx.AsyncClient for testing
        
        Raises:
            ValueError: If no API key is provided and none is configured
        """
        # Get API key from parameter or settings
        if api_key:
            self.api_key = api_key
        else:
            try:
                self.api_key = settings.get_google_maps_key()
            except Exception as e:
                raise ValueError(
                    "Google Maps API key is required. "
                    "Set GOOGLE_MAPS_API_KEY or GOOGLE_API_KEY environment variable."
                ) from e
        
        # Use provided client or create new one with connection pooling
        self._client = client or self._create_client()
        self._owns_client = client is None  # Track if we created the client
        
        logger.info(
            "google_maps_repository_initialized",
            timeout=settings.api_timeout_seconds,
            max_connections=settings.max_concurrent_requests,
        )
    
    def _create_client(self) -> httpx.AsyncClient:
        """Create a new httpx.AsyncClient with connection pooling.
        
        Returns:
            Configured AsyncClient instance
        """
        return httpx.AsyncClient(
            timeout=settings.api_timeout_seconds,
            limits=httpx.Limits(
                max_connections=settings.max_concurrent_requests,
                max_keepalive_connections=5,
                keepalive_expiry=30.0,
            ),
            headers={
                "User-Agent": "ShoppingOptimizer/1.0",
            },
            follow_redirects=True,
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(
            multiplier=1,
            min=settings.retry_min_wait_seconds,
            max=settings.retry_max_wait_seconds,
        ),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def geocode_address(self, address: str) -> Location:
        """Convert a text address to geographic coordinates with automatic retry.
        
        This method uses the Google Maps Geocoding API to convert a text address
        into latitude and longitude coordinates. It automatically retries failed
        requests with exponential backoff.
        
        Args:
            address: Text address to geocode (e.g., "Nørrebrogade 20, Copenhagen")
        
        Returns:
            Location object with validated latitude and longitude
        
        Raises:
            APIError: If the API call fails after all retries
            ValidationError: If the address cannot be geocoded or response is invalid
        
        Example:
            >>> location = await repo.geocode_address("Rådhuspladsen 1, Copenhagen")
            >>> print(f"{location.latitude}, {location.longitude}")
            55.6761, 12.5683
        """
        logger.info(
            "geocoding_address",
            address=address,
        )
        
        try:
            # Track API call timing and success
            with metrics_collector.time_api_call("google_maps", "/geocode"):
                # Build request parameters
                params: dict[str, str] = {
                    "address": address,
                    "key": self.api_key,
                }
                
                # Make API request
                response = await self._client.get(
                    self.GEOCODING_URL,
                    params=params,
                )
            
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    logger.warning(
                        "api_rate_limited",
                        retry_after=retry_after,
                        status_code=response.status_code,
                    )
                    raise APIError(
                        f"API rate limit exceeded. Retry after {retry_after} seconds.",
                        status_code=429,
                        response_body=response.text,
                    )
                
                # Handle other HTTP errors
                if response.status_code >= 400:
                    logger.error(
                        "api_request_failed",
                        status_code=response.status_code,
                        response_body=response.text[:500],  # Truncate for logging
                    )
                    raise APIError(
                        f"API request failed with status {response.status_code}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )
                
                response.raise_for_status()
                
                # Parse JSON response
                json_data = response.json()
                
                # Check API status
                status = json_data.get("status")
                
                if status == "ZERO_RESULTS":
                    logger.warning(
                        "geocoding_no_results",
                        address=address,
                    )
                    raise ValidationError(f"Address not found: {address}")
                
                if status == "INVALID_REQUEST":
                    logger.error(
                        "geocoding_invalid_request",
                        address=address,
                    )
                    raise ValidationError(f"Invalid geocoding request for address: {address}")
                
                if status != "OK":
                    logger.error(
                        "geocoding_api_error",
                        status=status,
                        address=address,
                    )
                    raise APIError(f"Geocoding API returned status: {status}")
                
                # Parse location from response
                location = self._parse_geocoding_response(json_data, address)
                
                # Record successful API call
                metrics_collector.record_api_success("google_maps", "/geocode")
                
                logger.info(
                    "address_geocoded",
                    address=address,
                    latitude=location.latitude,
                    longitude=location.longitude,
                )
                
                return location
            
        except httpx.TimeoutException as e:
            metrics_collector.record_api_failure("google_maps", "/geocode", error_type="timeout")
            logger.error("api_timeout", error=str(e), address=address)
            raise APIError(
                f"Geocoding request timed out after {settings.api_timeout_seconds}s"
            ) from e
        
        except httpx.HTTPError as e:
            status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            metrics_collector.record_api_failure("google_maps", "/geocode", status_code=status_code, error_type="http_error")
            logger.error(
                "http_error",
                error=str(e),
                error_type=type(e).__name__,
                address=address,
            )
            raise APIError(f"HTTP error occurred: {str(e)}") from e
        
        except (ValidationError, APIError) as e:
            metrics_collector.record_api_failure("google_maps", "/geocode", error_type=type(e).__name__)
            # Re-raise our custom errors without wrapping
            raise
        
        except Exception as e:
            metrics_collector.record_api_failure("google_maps", "/geocode", error_type=type(e).__name__)
            logger.error(
                "unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                address=address,
            )
            raise APIError(f"Unexpected error geocoding address: {str(e)}") from e
    
    async def calculate_distance(
        self,
        origin: Location,
        destination: Location,
    ) -> float:
        """Calculate distance between two locations using Haversine formula.
        
        This method calculates the great-circle distance between two points
        on Earth using the Haversine formula. This gives the shortest distance
        over the Earth's surface (as the crow flies), not road distance.
        
        Args:
            origin: Starting location
            destination: Ending location
        
        Returns:
            Distance in kilometers
        
        Note:
            This uses the Haversine formula for great-circle distance, which
            assumes a spherical Earth. For most purposes, this is accurate
            enough (error < 0.5%). For road distance, use a routing API instead.
        
        Example:
            >>> origin = Location(latitude=55.6761, longitude=12.5683)
            >>> destination = Location(latitude=55.6867, longitude=12.5700)
            >>> distance = await repo.calculate_distance(origin, destination)
            >>> print(f"{distance:.2f} km")
            1.18 km
        """
        logger.debug(
            "calculating_distance",
            origin=(origin.latitude, origin.longitude),
            destination=(destination.latitude, destination.longitude),
        )
        
        # Earth's radius in kilometers
        EARTH_RADIUS_KM = 6371.0
        
        # Convert coordinates to radians
        lat1 = radians(origin.latitude)
        lon1 = radians(origin.longitude)
        lat2 = radians(destination.latitude)
        lon2 = radians(destination.longitude)
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance_km = EARTH_RADIUS_KM * c
        
        logger.debug(
            "distance_calculated",
            distance_km=round(distance_km, 2),
        )
        
        return distance_km
    
    async def health_check(self) -> bool:
        """Check if the Google Maps API is healthy and accessible.
        
        This method performs a lightweight health check by attempting to
        geocode a well-known address.
        
        Returns:
            True if the API is healthy and accessible, False otherwise
        
        Example:
            >>> is_healthy = await repo.health_check()
            >>> if not is_healthy:
            ...     print("Google Maps API is down!")
        """
        try:
            # Use a well-known address for health check
            test_address = "Copenhagen, Denmark"
            
            response = await self._client.get(
                self.GEOCODING_URL,
                params={
                    "address": test_address,
                    "key": self.api_key,
                },
                timeout=5.0,  # Short timeout for health check
            )
            
            # Check both HTTP status and API status
            if response.status_code != 200:
                logger.warning(
                    "health_check_http_error",
                    status_code=response.status_code,
                )
                return False
            
            json_data = response.json()
            api_status: str = json_data.get("status", "")
            
            is_healthy: bool = api_status == "OK"
            
            logger.info(
                "health_check_completed",
                is_healthy=is_healthy,
                api_status=api_status,
            )
            
            return is_healthy
            
        except Exception as e:
            logger.warning(
                "health_check_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
    
    def _parse_geocoding_response(
        self,
        json_data: dict[str, Any],
        address: str,
    ) -> Location:
        """Parse Google Maps Geocoding API response.
        
        The Google Maps Geocoding API returns responses with the following structure:
        {
            "status": "OK",
            "results": [
                {
                    "geometry": {
                        "location": {
                            "lat": 55.6761,
                            "lng": 12.5683
                        }
                    },
                    "formatted_address": "Full address string"
                }
            ]
        }
        
        Args:
            json_data: Raw JSON response from API
            address: Original address that was geocoded (for error messages)
        
        Returns:
            Validated Location object
        
        Raises:
            ValidationError: If the response structure is invalid
        """
        try:
            results = json_data.get("results", [])
            
            if not results:
                raise ValidationError(f"No results found for address: {address}")
            
            # Get first result (most relevant)
            first_result = results[0]
            
            # Extract geometry
            geometry = first_result.get("geometry", {})
            location_data = geometry.get("location", {})
            
            # Extract coordinates
            latitude = location_data.get("lat")
            longitude = location_data.get("lng")
            
            if latitude is None or longitude is None:
                raise ValidationError(
                    f"Missing coordinates in geocoding response for address: {address}"
                )
            
            # Create and validate Location using Pydantic
            location = Location(
                latitude=float(latitude),
                longitude=float(longitude),
            )
            
            return location
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(
                "geocoding_parse_failed",
                error=str(e),
                address=address,
            )
            raise ValidationError(
                f"Failed to parse geocoding response for address: {address}"
            ) from e
    
    async def __aenter__(self) -> "GoogleMapsRepository":
        """Enter async context manager.
        
        Returns:
            Self for use in async with statement
        """
        return self
    
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager and cleanup resources.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        # Only close the client if we created it
        if self._owns_client and self._client:
            await self._client.aclose()
            logger.info("google_maps_repository_closed")

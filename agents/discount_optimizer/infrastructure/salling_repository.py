"""Async repository for Salling Group API with connection pooling and retry logic.

This module implements the DiscountRepository protocol for the Salling Group API,
providing type-safe, async access to discount data with automatic retries,
connection pooling, and comprehensive error handling.
"""

import httpx
from typing import Any
from datetime import date, datetime, timedelta
from decimal import Decimal
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import structlog
import logging

from ..domain.models import Location, DiscountItem
from ..domain.protocols import DiscountRepository
from ..domain.exceptions import APIError, ValidationError
from ..config import settings

logger = structlog.get_logger(__name__)


class SallingDiscountRepository:
    """Repository for Salling Group API with connection pooling and retry logic.
    
    This repository implements the DiscountRepository protocol and provides
    async access to discount data from the Salling Group API. It includes:
    - Automatic retry with exponential backoff
    - HTTP connection pooling for performance
    - Comprehensive error handling
    - Pydantic validation of API responses
    - Context manager support for resource cleanup
    
    The Salling Group operates major Danish grocery chains including:
    - Netto
    - Føtex
    - Bilka
    - BR
    
    API Documentation: https://developer.sallinggroup.com/
    
    Example:
        >>> async with SallingDiscountRepository(api_key="your-key") as repo:
        ...     location = Location(latitude=55.6761, longitude=12.5683)
        ...     discounts = await repo.fetch_discounts(location, radius_km=5.0)
        ...     print(f"Found {len(discounts)} discounts")
    """
    
    BASE_URL = "https://api.sallinggroup.com/v1"
    
    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        """Initialize the Salling API repository.
        
        Args:
            api_key: Salling Group API key (defaults to settings.salling_group_api_key)
            client: Optional pre-configured httpx.AsyncClient for testing
        
        Raises:
            ValueError: If no API key is provided and none is configured
        """
        # Get API key from parameter or settings
        if api_key:
            self.api_key = api_key
        elif settings.salling_group_api_key:
            self.api_key = settings.salling_group_api_key.get_secret_value()
        else:
            raise ValueError(
                "Salling Group API key is required. "
                "Set SALLING_GROUP_API_KEY environment variable or pass api_key parameter."
            )
        
        # Use provided client or create new one with connection pooling
        self._client = client or self._create_client()
        self._owns_client = client is None  # Track if we created the client
        
        logger.info(
            "salling_repository_initialized",
            base_url=self.BASE_URL,
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
                "Authorization": f"Bearer {self.api_key}",
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
    async def fetch_discounts(
        self,
        location: Location,
        radius_km: float,
    ) -> list[DiscountItem]:
        """Fetch discounts from Salling API with automatic retry logic.
        
        This method fetches food waste offers from the Salling Group API within
        the specified radius of the given location. It automatically retries
        failed requests with exponential backoff.
        
        Args:
            location: Geographic location to search around
            radius_km: Search radius in kilometers (capped at 100km by API)
        
        Returns:
            List of validated DiscountItem objects
        
        Raises:
            APIError: If the API call fails after all retries
            ValidationError: If the API response cannot be validated
        
        Example:
            >>> location = Location(latitude=55.6761, longitude=12.5683)
            >>> discounts = await repo.fetch_discounts(location, radius_km=5.0)
        """
        logger.info(
            "fetching_discounts",
            latitude=location.latitude,
            longitude=location.longitude,
            radius_km=radius_km,
        )
        
        try:
            # Cap radius at API maximum
            radius_km_capped = min(radius_km, 100.0)
            
            # Build request parameters
            # Salling API expects geo parameter in format "latitude,longitude"
            params: dict[str, str | float] = {
                "geo": f"{location.latitude},{location.longitude}",
                "radius": radius_km_capped,
            }
            
            # Make API request
            response = await self._client.get(
                f"{self.BASE_URL}/food-waste/",
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
            
            # Parse and validate discount items
            discounts = self._parse_response(json_data)
            
            logger.info(
                "discounts_fetched",
                count=len(discounts),
                location=(location.latitude, location.longitude),
                radius_km=radius_km_capped,
            )
            
            return discounts
            
        except httpx.TimeoutException as e:
            logger.error("api_timeout", error=str(e))
            raise APIError(f"API request timed out after {settings.api_timeout_seconds}s") from e
        
        except httpx.HTTPError as e:
            logger.error("http_error", error=str(e), error_type=type(e).__name__)
            raise APIError(f"HTTP error occurred: {str(e)}") from e
        
        except ValidationError:
            # Re-raise validation errors without wrapping
            raise
        
        except Exception as e:
            logger.error("unexpected_error", error=str(e), error_type=type(e).__name__)
            raise APIError(f"Unexpected error fetching discounts: {str(e)}") from e
    
    async def health_check(self) -> bool:
        """Check if the Salling API is healthy and accessible.
        
        This method performs a lightweight health check by attempting to
        fetch a small amount of data from the API.
        
        Returns:
            True if the API is healthy and accessible, False otherwise
        
        Example:
            >>> is_healthy = await repo.health_check()
            >>> if not is_healthy:
            ...     print("API is down!")
        """
        try:
            # Use a small radius for quick health check
            test_location = Location(latitude=55.6761, longitude=12.5683)  # Copenhagen
            
            response = await self._client.get(
                f"{self.BASE_URL}/food-waste/",
                params={
                    "geo": f"{test_location.latitude},{test_location.longitude}",
                    "radius": 1.0,  # Minimal radius
                },
                timeout=5.0,  # Short timeout for health check
            )
            
            is_healthy = response.status_code == 200
            
            logger.info(
                "health_check_completed",
                is_healthy=is_healthy,
                status_code=response.status_code,
            )
            
            return is_healthy
            
        except Exception as e:
            logger.warning(
                "health_check_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
    
    def _parse_response(self, json_data: list[dict[str, Any]]) -> list[DiscountItem]:
        """Parse Salling Group API response and convert to DiscountItem objects.
        
        The Salling API returns food waste offers with the following structure:
        {
            "store": {
                "name": "Netto",
                "address": {
                    "street": "Street name",
                    "city": "Copenhagen",
                    "zip": "2100"
                },
                "coordinates": [12.5683, 55.6761],  # [longitude, latitude]
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
            List of validated DiscountItem objects
        
        Raises:
            ValidationError: If the response structure is invalid
        """
        discount_items: list[DiscountItem] = []
        
        if not isinstance(json_data, list):
            raise ValidationError(f"Expected list response, got {type(json_data).__name__}")
        
        for store_data in json_data:
            try:
                # Extract store information
                store = store_data.get("store", {})
                store_name = store.get("name", "Unknown Store")
                store_address_data = store.get("address", {})
                store_city = store_address_data.get("city", "")
                store_street = store_address_data.get("street", "")
                
                # Get store coordinates
                # Salling API returns [longitude, latitude]
                coordinates = store.get("coordinates", [])
                if len(coordinates) < 2:
                    logger.warning(
                        "store_missing_coordinates",
                        store_name=store_name,
                    )
                    continue
                
                store_location = Location(
                    latitude=coordinates[1],
                    longitude=coordinates[0],
                )
                
                # Process each clearance item at this store
                clearances = store_data.get("clearances", [])
                
                for clearance in clearances:
                    try:
                        discount_item = self._parse_discount(
                            clearance=clearance,
                            store_name=store_name,
                            store_location=store_location,
                            store_street=store_street,
                            store_city=store_city,
                        )
                        discount_items.append(discount_item)
                        
                    except (KeyError, ValueError, TypeError) as e:
                        logger.warning(
                            "clearance_parse_failed",
                            error=str(e),
                            store_name=store_name,
                        )
                        continue
                
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(
                    "store_parse_failed",
                    error=str(e),
                )
                continue
        
        return discount_items
    
    def _parse_discount(
        self,
        clearance: dict[str, Any],
        store_name: str,
        store_location: Location,
        store_street: str,
        store_city: str,
    ) -> DiscountItem:
        """Parse a single clearance item into a DiscountItem with Pydantic validation.
        
        Args:
            clearance: Clearance data from API
            store_name: Name of the store
            store_location: Location of the store
            store_street: Street address of the store
            store_city: City of the store
        
        Returns:
            Validated DiscountItem object
        
        Raises:
            ValueError: If required fields are missing or invalid
            ValidationError: If Pydantic validation fails
        """
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
        
        # Create and validate DiscountItem using Pydantic
        try:
            discount_item = DiscountItem(
                product_name=product_name,
                store_name=f"{store_name} {store_city}".strip(),
                store_location=store_location,
                original_price=Decimal(str(original_price)),
                discount_price=Decimal(str(discount_price)),
                discount_percent=float(discount_percent),
                expiration_date=expiration_date,
                is_organic=is_organic,
                store_address=full_address,
                travel_distance_km=0.0,  # Will be calculated later by Google Maps
                travel_time_minutes=0.0,  # Will be calculated later by Google Maps
            )
            
            return discount_item
            
        except Exception as e:
            logger.error(
                "discount_validation_failed",
                error=str(e),
                product_name=product_name,
                store_name=store_name,
            )
            raise ValidationError(f"Failed to validate discount item: {str(e)}") from e
    
    async def __aenter__(self) -> "SallingDiscountRepository":
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
            logger.info("salling_repository_closed")

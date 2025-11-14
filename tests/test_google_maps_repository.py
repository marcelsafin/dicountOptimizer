"""
Tests for GoogleMapsRepository.

This module tests the async Google Maps repository implementation with
focus on I/O operations: geocoding API calls, error handling, and health checks.
Uses pytest-httpx to mock HTTP responses.
"""

import pytest
import httpx
from pytest_httpx import HTTPXMock
from agents.discount_optimizer.infrastructure.google_maps_repository import GoogleMapsRepository
from agents.discount_optimizer.domain.models import Location
from agents.discount_optimizer.domain.exceptions import APIError, ValidationError


class TestGoogleMapsRepository:
    """Test suite for GoogleMapsRepository."""
    
    @pytest.mark.asyncio
    async def test_geocode_address_success(self, httpx_mock: HTTPXMock):
        """Test successful geocoding with mocked 200 response."""
        # Arrange
        mock_response = {
            "status": "OK",
            "results": [
                {
                    "geometry": {
                        "location": {
                            "lat": 55.6761,
                            "lng": 12.5683
                        }
                    },
                    "formatted_address": "Copenhagen, Denmark"
                }
            ]
        }
        
        httpx_mock.add_response(
            url="https://maps.googleapis.com/maps/api/geocode/json?address=Copenhagen%2C+Denmark&key=test-key",
            json=mock_response,
            status_code=200
        )
        
        async with httpx.AsyncClient() as client:
            repo = GoogleMapsRepository(api_key="test-key", client=client)
            
            # Act
            location = await repo.geocode_address("Copenhagen, Denmark")
            
            # Assert
            assert isinstance(location, Location)
            assert location.latitude == 55.6761
            assert location.longitude == 12.5683
    
    @pytest.mark.asyncio
    async def test_geocode_address_api_error(self, httpx_mock: HTTPXMock):
        """Test geocoding with mocked 500 error response."""
        # Arrange
        httpx_mock.add_response(
            url="https://maps.googleapis.com/maps/api/geocode/json?address=Invalid+Address&key=test-key",
            text="Internal Server Error",
            status_code=500
        )
        
        async with httpx.AsyncClient() as client:
            repo = GoogleMapsRepository(api_key="test-key", client=client)
            
            # Act & Assert
            with pytest.raises(APIError) as exc_info:
                await repo.geocode_address("Invalid Address")
            
            assert "500" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_geocode_address_rate_limit(self, httpx_mock: HTTPXMock):
        """Test geocoding with mocked 429 rate limit response."""
        # Arrange
        httpx_mock.add_response(
            url="https://maps.googleapis.com/maps/api/geocode/json?address=Test+Address&key=test-key",
            text="Rate limit exceeded",
            status_code=429,
            headers={"Retry-After": "60"}
        )
        
        async with httpx.AsyncClient() as client:
            repo = GoogleMapsRepository(api_key="test-key", client=client)
            
            # Act & Assert
            with pytest.raises(APIError) as exc_info:
                await repo.geocode_address("Test Address")
            
            assert "rate limit" in str(exc_info.value).lower()
            assert exc_info.value.status_code == 429
    
    @pytest.mark.asyncio
    async def test_geocode_address_zero_results(self, httpx_mock: HTTPXMock):
        """Test geocoding with ZERO_RESULTS status."""
        # Arrange
        mock_response = {
            "status": "ZERO_RESULTS",
            "results": []
        }
        
        httpx_mock.add_response(
            url="https://maps.googleapis.com/maps/api/geocode/json?address=Nonexistent+Place&key=test-key",
            json=mock_response,
            status_code=200
        )
        
        async with httpx.AsyncClient() as client:
            repo = GoogleMapsRepository(api_key="test-key", client=client)
            
            # Act & Assert
            with pytest.raises(ValidationError) as exc_info:
                await repo.geocode_address("Nonexistent Place")
            
            assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_geocode_address_invalid_request(self, httpx_mock: HTTPXMock):
        """Test geocoding with INVALID_REQUEST status."""
        # Arrange
        mock_response = {
            "status": "INVALID_REQUEST",
            "results": []
        }
        
        httpx_mock.add_response(
            url="https://maps.googleapis.com/maps/api/geocode/json?address=&key=test-key",
            json=mock_response,
            status_code=200
        )
        
        async with httpx.AsyncClient() as client:
            repo = GoogleMapsRepository(api_key="test-key", client=client)
            
            # Act & Assert
            with pytest.raises(ValidationError) as exc_info:
                await repo.geocode_address("")
            
            assert "invalid" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, httpx_mock: HTTPXMock):
        """Test health check with mocked 200 response."""
        # Arrange
        mock_response = {
            "status": "OK",
            "results": [
                {
                    "geometry": {
                        "location": {
                            "lat": 55.6761,
                            "lng": 12.5683
                        }
                    }
                }
            ]
        }
        
        httpx_mock.add_response(
            url="https://maps.googleapis.com/maps/api/geocode/json?address=Copenhagen%2C+Denmark&key=test-key",
            json=mock_response,
            status_code=200
        )
        
        async with httpx.AsyncClient() as client:
            repo = GoogleMapsRepository(api_key="test-key", client=client)
            
            # Act
            is_healthy = await repo.health_check()
            
            # Assert
            assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, httpx_mock: HTTPXMock):
        """Test health check with mocked 503 error response."""
        # Arrange
        httpx_mock.add_response(
            url="https://maps.googleapis.com/maps/api/geocode/json?address=Copenhagen%2C+Denmark&key=test-key",
            text="Service Unavailable",
            status_code=503
        )
        
        async with httpx.AsyncClient() as client:
            repo = GoogleMapsRepository(api_key="test-key", client=client)
            
            # Act
            is_healthy = await repo.health_check()
            
            # Assert
            assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_calculate_distance_haversine(self):
        """Test Haversine distance calculation (no API call)."""
        # Arrange
        repo = GoogleMapsRepository(api_key="test-key")
        copenhagen = Location(latitude=55.6761, longitude=12.5683)
        malmo = Location(latitude=55.6050, longitude=13.0038)
        
        # Act
        distance = await repo.calculate_distance(copenhagen, malmo)
        
        # Assert
        # Expected distance is approximately 28-29 km
        assert 27.0 <= distance <= 30.0, f"Distance should be ~28km, got {distance}"
        
        # Cleanup
        await repo._client.aclose()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

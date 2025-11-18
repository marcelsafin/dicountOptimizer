"""Unit tests for SallingDiscountRepository with mocked HTTP responses.

This test suite verifies the repository implementation without making real
network calls. All HTTP responses are mocked using pytest-httpx.
"""

from datetime import date
from decimal import Decimal
from typing import Any

import httpx
import pytest

from agents.discount_optimizer.domain.exceptions import APIError, ValidationError
from agents.discount_optimizer.domain.models import Location
from agents.discount_optimizer.domain.protocols import DiscountRepository
from agents.discount_optimizer.infrastructure.salling_repository import SallingDiscountRepository


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_api_response() -> list[dict[str, Any]]:
    """Fixture providing a realistic Salling API response."""
    return [
        {
            "store": {
                "name": "Netto",
                "address": {"street": "Nørrebrogade 20", "city": "København K", "zip": "2200"},
                "coordinates": [12.5683, 55.6761],  # [longitude, latitude]
                "brand": "netto",
            },
            "clearances": [
                {
                    "product": {"description": "Økologisk Mælk 1L", "ean": "5701234567890"},
                    "offer": {
                        "originalPrice": 25.00,
                        "newPrice": 18.75,
                        "percentDiscount": 25,
                        "stock": 10,
                        "stockUnit": "stk",
                        "endTime": "2025-11-20T20:00:00Z",
                    },
                },
                {
                    "product": {"description": "Bananer", "ean": "5701234567891"},
                    "offer": {
                        "originalPrice": 15.00,
                        "newPrice": 10.00,
                        "percentDiscount": 33,
                        "stock": 5,
                        "stockUnit": "kg",
                        "endTime": "2025-11-18T20:00:00Z",
                    },
                },
            ],
        },
        {
            "store": {
                "name": "Føtex",
                "address": {"street": "Vesterbrogade 1", "city": "København V", "zip": "1620"},
                "coordinates": [12.5584, 55.6738],
                "brand": "foetex",
            },
            "clearances": [
                {
                    "product": {"description": "Bio Yoghurt", "ean": "5701234567892"},
                    "offer": {
                        "originalPrice": 20.00,
                        "newPrice": 15.00,
                        "percentDiscount": 25,
                        "stock": 8,
                        "stockUnit": "stk",
                        "endTime": "2025-11-19T20:00:00Z",
                    },
                }
            ],
        },
    ]


@pytest.fixture
def test_location() -> Location:
    """Fixture providing a test location (Copenhagen center)."""
    return Location(latitude=55.6761, longitude=12.5683)


# ============================================================================
# Test: Repository Initialization
# ============================================================================


def test_repository_initialization_with_api_key():
    """Test that repository initializes correctly with explicit API key."""
    repo = SallingDiscountRepository(api_key="test_api_key_123")

    assert repo.api_key == "test_api_key_123"
    assert repo.BASE_URL == "https://api.sallinggroup.com/v1"
    assert repo._client is not None
    assert repo._owns_client is True


def test_repository_initialization_without_api_key_raises_error(monkeypatch):
    """Test that repository raises ValueError when no API key is provided."""
    # Remove API key from environment and patch settings
    monkeypatch.delenv("SALLING_GROUP_API_KEY", raising=False)

    # Also patch the settings object to return None
    from agents.discount_optimizer import config

    monkeypatch.setattr(config.settings, "salling_group_api_key", None)

    with pytest.raises(ValueError, match="Salling Group API key is required"):
        SallingDiscountRepository()


def test_repository_implements_protocol():
    """Test that repository correctly implements DiscountRepository protocol."""
    repo = SallingDiscountRepository(api_key="test_key")

    # Runtime check using @runtime_checkable protocol
    assert isinstance(repo, DiscountRepository)


# ============================================================================
# Test: Fetch Discounts (Success Cases)
# ============================================================================


@pytest.mark.asyncio
async def test_fetch_discounts_success(
    httpx_mock, mock_api_response: list[dict[str, Any]], test_location: Location
):
    """Test successful discount fetching with mocked HTTP response."""
    # Mock the HTTP response
    httpx_mock.add_response(
        url="https://api.sallinggroup.com/v1/food-waste/?geo=55.6761%2C12.5683&radius=5.0",
        json=mock_api_response,
        status_code=200,
    )

    async with SallingDiscountRepository(api_key="test_key") as repo:
        discounts = await repo.fetch_discounts(test_location, radius_km=5.0)

    # Verify we got the expected number of discounts
    assert len(discounts) == 3  # 2 from Netto + 1 from Føtex

    # Verify first discount (Økologisk Mælk)
    first = discounts[0]
    assert first.product_name == "Økologisk Mælk 1L"
    assert first.store_name == "Netto København K"
    assert first.original_price == Decimal("25.00")
    assert first.discount_price == Decimal("18.75")
    assert first.discount_percent == 25.0
    assert first.is_organic is True  # Should detect "Økologisk"
    assert first.expiration_date == date(2025, 11, 20)

    # Verify location parsing
    assert first.store_location.latitude == 55.6761
    assert first.store_location.longitude == 12.5683


@pytest.mark.asyncio
async def test_fetch_discounts_caps_radius(
    httpx_mock, mock_api_response: list[dict[str, Any]], test_location: Location
):
    """Test that radius is capped at 100km per API limits."""
    # Mock expects radius=100.0 (capped)
    httpx_mock.add_response(
        url="https://api.sallinggroup.com/v1/food-waste/?geo=55.6761%2C12.5683&radius=100.0",
        json=mock_api_response,
        status_code=200,
    )

    async with SallingDiscountRepository(api_key="test_key") as repo:
        # Request 150km but should be capped at 100km
        discounts = await repo.fetch_discounts(test_location, radius_km=150.0)

    assert len(discounts) == 3


@pytest.mark.asyncio
async def test_fetch_discounts_empty_response(httpx_mock, test_location: Location):
    """Test handling of empty API response (no discounts available)."""
    httpx_mock.add_response(
        url="https://api.sallinggroup.com/v1/food-waste/?geo=55.6761%2C12.5683&radius=5.0",
        json=[],
        status_code=200,
    )

    async with SallingDiscountRepository(api_key="test_key") as repo:
        discounts = await repo.fetch_discounts(test_location, radius_km=5.0)

    assert discounts == []


# ============================================================================
# Test: Fetch Discounts (Error Cases)
# ============================================================================


@pytest.mark.asyncio
async def test_fetch_discounts_rate_limited(httpx_mock, test_location: Location):
    """Test handling of API rate limiting (429 status)."""
    httpx_mock.add_response(
        url="https://api.sallinggroup.com/v1/food-waste/?geo=55.6761%2C12.5683&radius=5.0",
        status_code=429,
        headers={"Retry-After": "60"},
        text="Rate limit exceeded",
    )

    async with SallingDiscountRepository(api_key="test_key") as repo:
        with pytest.raises(APIError, match="API rate limit exceeded"):
            await repo.fetch_discounts(test_location, radius_km=5.0)


@pytest.mark.asyncio
async def test_fetch_discounts_http_error(httpx_mock, test_location: Location):
    """Test handling of HTTP errors (4xx, 5xx)."""
    httpx_mock.add_response(
        url="https://api.sallinggroup.com/v1/food-waste/?geo=55.6761%2C12.5683&radius=5.0",
        status_code=500,
        text="Internal Server Error",
    )

    async with SallingDiscountRepository(api_key="test_key") as repo:
        with pytest.raises(APIError, match="API request failed with status 500"):
            await repo.fetch_discounts(test_location, radius_km=5.0)


@pytest.mark.asyncio
async def test_fetch_discounts_timeout(httpx_mock, test_location: Location):
    """Test handling of request timeout."""
    httpx_mock.add_exception(httpx.TimeoutException("Request timed out"))

    async with SallingDiscountRepository(api_key="test_key") as repo:
        with pytest.raises(APIError, match="API request timed out"):
            await repo.fetch_discounts(test_location, radius_km=5.0)


@pytest.mark.asyncio
async def test_fetch_discounts_invalid_json_response(httpx_mock, test_location: Location):
    """Test handling of invalid JSON response structure."""
    # Return a dict instead of expected list
    httpx_mock.add_response(
        url="https://api.sallinggroup.com/v1/food-waste/?geo=55.6761%2C12.5683&radius=5.0",
        json={"error": "Invalid response"},
        status_code=200,
    )

    async with SallingDiscountRepository(api_key="test_key") as repo:
        with pytest.raises(ValidationError, match="Expected list response"):
            await repo.fetch_discounts(test_location, radius_km=5.0)


# ============================================================================
# Test: Health Check
# ============================================================================


@pytest.mark.asyncio
async def test_health_check_success(httpx_mock):
    """Test successful health check."""
    httpx_mock.add_response(
        url="https://api.sallinggroup.com/v1/food-waste/?geo=55.6761%2C12.5683&radius=1.0",
        json=[],
        status_code=200,
    )

    async with SallingDiscountRepository(api_key="test_key") as repo:
        is_healthy = await repo.health_check()

    assert is_healthy is True


@pytest.mark.asyncio
async def test_health_check_failure(httpx_mock):
    """Test health check when API is down."""
    httpx_mock.add_response(
        url="https://api.sallinggroup.com/v1/food-waste/?geo=55.6761%2C12.5683&radius=1.0",
        status_code=503,
    )

    async with SallingDiscountRepository(api_key="test_key") as repo:
        is_healthy = await repo.health_check()

    assert is_healthy is False


@pytest.mark.asyncio
async def test_health_check_exception(httpx_mock):
    """Test health check when network error occurs."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

    async with SallingDiscountRepository(api_key="test_key") as repo:
        is_healthy = await repo.health_check()

    assert is_healthy is False


# ============================================================================
# Test: Context Manager
# ============================================================================


@pytest.mark.asyncio
async def test_context_manager_cleanup():
    """Test that context manager properly cleans up resources."""
    repo = SallingDiscountRepository(api_key="test_key")

    async with repo:
        # Client should be open
        assert repo._client is not None

    # After exiting context, client should be closed
    # Note: We can't easily test if httpx client is closed, but we verify no errors


# ============================================================================
# Test: Discount Parsing Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_parse_discount_missing_coordinates(httpx_mock, test_location: Location):
    """Test that stores without coordinates are skipped."""
    response = [
        {
            "store": {
                "name": "Test Store",
                "address": {"street": "Test St", "city": "Test City", "zip": "1234"},
                "coordinates": [],  # Missing coordinates
                "brand": "test",
            },
            "clearances": [
                {
                    "product": {"description": "Test Product", "ean": "123"},
                    "offer": {
                        "originalPrice": 10.0,
                        "newPrice": 5.0,
                        "percentDiscount": 50,
                        "endTime": "2025-11-20T20:00:00Z",
                    },
                }
            ],
        }
    ]

    httpx_mock.add_response(
        url="https://api.sallinggroup.com/v1/food-waste/?geo=55.6761%2C12.5683&radius=5.0",
        json=response,
        status_code=200,
    )

    async with SallingDiscountRepository(api_key="test_key") as repo:
        discounts = await repo.fetch_discounts(test_location, radius_km=5.0)

    # Store should be skipped due to missing coordinates
    assert len(discounts) == 0


@pytest.mark.asyncio
async def test_parse_discount_missing_end_time(httpx_mock, test_location: Location):
    """Test that missing endTime defaults to 3 days from now."""
    response = [
        {
            "store": {
                "name": "Test Store",
                "address": {"street": "Test St", "city": "Test City", "zip": "1234"},
                "coordinates": [12.5683, 55.6761],
                "brand": "test",
            },
            "clearances": [
                {
                    "product": {"description": "Test Product", "ean": "123"},
                    "offer": {
                        "originalPrice": 10.0,
                        "newPrice": 5.0,
                        "percentDiscount": 50,
                        # No endTime field
                    },
                }
            ],
        }
    ]

    httpx_mock.add_response(
        url="https://api.sallinggroup.com/v1/food-waste/?geo=55.6761%2C12.5683&radius=5.0",
        json=response,
        status_code=200,
    )

    async with SallingDiscountRepository(api_key="test_key") as repo:
        discounts = await repo.fetch_discounts(test_location, radius_km=5.0)

    assert len(discounts) == 1
    # Should default to today + 3 days
    from datetime import timedelta

    expected_date = date.today() + timedelta(days=3)
    assert discounts[0].expiration_date == expected_date

"""
Unit tests for DiscountMatcherService with mocked repositories.

This test suite verifies the service implementation without making real
API calls. All repository responses are mocked using pytest-mock.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date, timedelta
from decimal import Decimal

from agents.discount_optimizer.services.discount_matcher_service import (
    DiscountMatcherService,
    DiscountMatchingInput,
    DiscountMatchingOutput,
)
from agents.discount_optimizer.domain.models import Location, Timeframe, DiscountItem
from agents.discount_optimizer.domain.exceptions import APIError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_location() -> Location:
    """Fixture providing a test location (Copenhagen)."""
    return Location(latitude=55.6761, longitude=12.5683)


@pytest.fixture
def test_timeframe() -> Timeframe:
    """Fixture providing a test timeframe (next 7 days)."""
    today = date.today()
    return Timeframe(
        start_date=today,
        end_date=today + timedelta(days=7)
    )


@pytest.fixture
def basic_input(test_location: Location, test_timeframe: Timeframe) -> DiscountMatchingInput:
    """Fixture providing basic input data."""
    return DiscountMatchingInput(
        location=test_location,
        radius_km=5.0,
        timeframe=test_timeframe,
        min_discount_percent=10.0,
        prefer_organic=False,
        max_results=100
    )


@pytest.fixture
def sample_discounts(test_location: Location) -> list[DiscountItem]:
    """Fixture providing sample discount items."""
    today = date.today()
    
    return [
        DiscountItem(
            product_name="Organic Milk",
            store_name="Føtex Copenhagen",
            store_location=test_location,
            original_price=Decimal("25.00"),
            discount_price=Decimal("18.75"),
            discount_percent=25.0,
            expiration_date=today + timedelta(days=2),
            is_organic=True,
            store_address="Nørrebrogade 20, Copenhagen",
        ),
        DiscountItem(
            product_name="Hakket oksekød",
            store_name="Netto Copenhagen",
            store_location=test_location,
            original_price=Decimal("50.00"),
            discount_price=Decimal("35.00"),
            discount_percent=30.0,
            expiration_date=today + timedelta(days=1),
            is_organic=False,
            store_address="Vesterbrogade 10, Copenhagen",
        ),
        DiscountItem(
            product_name="Tortillas",
            store_name="Bilka Copenhagen",
            store_location=test_location,
            original_price=Decimal("20.00"),
            discount_price=Decimal("18.00"),
            discount_percent=10.0,
            expiration_date=today + timedelta(days=3),
            is_organic=False,
            store_address="Amager Centervej 100, Copenhagen",
        ),
        DiscountItem(
            product_name="Expired Product",
            store_name="Føtex Copenhagen",
            store_location=test_location,
            original_price=Decimal("30.00"),
            discount_price=Decimal("27.00"),
            discount_percent=10.0,
            expiration_date=today - timedelta(days=1),  # Already expired
            is_organic=False,
            store_address="Nørrebrogade 20, Copenhagen",
        ),
        DiscountItem(
            product_name="Low Discount Product",
            store_name="Netto Copenhagen",
            store_location=test_location,
            original_price=Decimal("100.00"),
            discount_price=Decimal("95.00"),
            discount_percent=5.0,  # Below 10% threshold
            expiration_date=today + timedelta(days=5),
            is_organic=False,
            store_address="Vesterbrogade 10, Copenhagen",
        ),
    ]


@pytest.fixture
def mock_discount_repository(sample_discounts: list[DiscountItem]) -> AsyncMock:
    """Fixture providing a mocked DiscountRepository."""
    mock_repo = AsyncMock()
    mock_repo.fetch_discounts = AsyncMock(return_value=sample_discounts)
    mock_repo.health_check = AsyncMock(return_value=True)
    return mock_repo


@pytest.fixture
def mock_cache_repository() -> AsyncMock:
    """Fixture providing a mocked CacheRepository."""
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)  # Cache miss by default
    mock_cache.set = AsyncMock()
    return mock_cache


# ============================================================================
# Test: Agent Initialization
# ============================================================================

def test_agent_initialization_with_dependencies(mock_discount_repository: AsyncMock):
    """Test that service initializes correctly with injected dependencies."""
    service = DiscountMatcherService(
        discount_repository=mock_discount_repository
    )
    
    assert service.discount_repository is mock_discount_repository
    assert service.cache_repository is None


def test_agent_initialization_with_cache(
    mock_discount_repository: AsyncMock,
    mock_cache_repository: AsyncMock
):
    """Test that service initializes correctly with cache repository."""
    service = DiscountMatcherService(
        discount_repository=mock_discount_repository,
        cache_repository=mock_cache_repository
    )
    
    assert service.cache_repository is mock_cache_repository


def test_input_validation_valid(test_location: Location, test_timeframe: Timeframe):
    """Test that valid input is accepted."""
    input_data = DiscountMatchingInput(
        location=test_location,
        radius_km=5.0,
        timeframe=test_timeframe,
        min_discount_percent=15.0,
        prefer_organic=True,
        max_results=50
    )
    
    assert input_data.location == test_location
    assert input_data.radius_km == 5.0
    assert input_data.min_discount_percent == 15.0


def test_input_validation_radius_too_large(test_location: Location, test_timeframe: Timeframe):
    """Test that radius > 100km is rejected by Pydantic."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        DiscountMatchingInput(
            location=test_location,
            radius_km=150.0,  # Max is 100.0
            timeframe=test_timeframe,
        )


def test_input_validation_negative_radius(test_location: Location, test_timeframe: Timeframe):
    """Test that negative radius is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        DiscountMatchingInput(
            location=test_location,
            radius_km=-5.0,  # Must be > 0
            timeframe=test_timeframe,
        )


def test_input_validation_invalid_discount_percent(
    test_location: Location,
    test_timeframe: Timeframe
):
    """Test that discount percent > 100 is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        DiscountMatchingInput(
            location=test_location,
            radius_km=5.0,
            timeframe=test_timeframe,
            min_discount_percent=150.0,  # Max is 100
        )


# ============================================================================
# Test: Output Validation
# ============================================================================

def test_output_validation_valid(sample_discounts: list[DiscountItem]):
    """Test that valid output is accepted."""
    output = DiscountMatchingOutput(
        discounts=sample_discounts[:3],
        total_found=5,
        total_matched=3,
        filters_applied="timeframe, min_discount_percent",
        cache_hit=False,
        organic_count=1,
        average_discount_percent=25.0
    )
    
    assert len(output.discounts) == 3
    assert output.total_found == 5
    assert output.total_matched == 3


# ============================================================================
# Test: Discount Fetching and Filtering
# ============================================================================

@pytest.mark.asyncio
async def test_match_discounts_basic(
    mock_discount_repository: AsyncMock,
    basic_input: DiscountMatchingInput
):
    """Test basic discount matching without cache."""
    agent = DiscountMatcherService(
        discount_repository=mock_discount_repository
    )
    
    # Act
    output = await agent.match_discounts(basic_input)
    
    # Assert
    assert isinstance(output, DiscountMatchingOutput)
    assert output.total_found == 5  # All discounts from repository
    assert output.total_matched == 3  # 3 pass filters (expired and low discount filtered out)
    assert output.cache_hit is False
    
    # Verify repository was called
    mock_discount_repository.fetch_discounts.assert_called_once_with(
        location=basic_input.location,
        radius_km=basic_input.radius_km
    )


@pytest.mark.asyncio
async def test_timeframe_filtering(
    mock_discount_repository: AsyncMock,
    test_location: Location
):
    """Test that expired discounts are filtered out."""
    today = date.today()
    timeframe = Timeframe(
        start_date=today,
        end_date=today + timedelta(days=7)
    )
    
    input_data = DiscountMatchingInput(
        location=test_location,
        radius_km=5.0,
        timeframe=timeframe,
        min_discount_percent=0.0,  # Accept all discount percentages
    )
    
    agent = DiscountMatcherService(
        discount_repository=mock_discount_repository
    )
    
    # Act
    output = await agent.match_discounts(input_data)
    
    # Assert - expired product should be filtered out
    assert all(d.expiration_date >= today for d in output.discounts)
    assert output.total_matched == 4  # 5 total - 1 expired


@pytest.mark.asyncio
async def test_min_discount_percent_filtering(
    mock_discount_repository: AsyncMock,
    test_location: Location,
    test_timeframe: Timeframe
):
    """Test that discounts below minimum percentage are filtered out."""
    input_data = DiscountMatchingInput(
        location=test_location,
        radius_km=5.0,
        timeframe=test_timeframe,
        min_discount_percent=15.0,  # Filter out 10% and 5% discounts
    )
    
    agent = DiscountMatcherService(
        discount_repository=mock_discount_repository
    )
    
    # Act
    output = await agent.match_discounts(input_data)
    
    # Assert - only discounts >= 15% should remain
    assert all(d.discount_percent >= 15.0 for d in output.discounts)
    assert output.total_matched == 2  # Only 25% and 30% discounts


# ============================================================================
# Test: Sorting and Prioritization
# ============================================================================

@pytest.mark.asyncio
async def test_organic_prioritization(
    mock_discount_repository: AsyncMock,
    test_location: Location,
    test_timeframe: Timeframe
):
    """Test that organic products are prioritized when prefer_organic is True."""
    input_data = DiscountMatchingInput(
        location=test_location,
        radius_km=5.0,
        timeframe=test_timeframe,
        min_discount_percent=10.0,
        prefer_organic=True,  # Prioritize organic
    )
    
    agent = DiscountMatcherService(
        discount_repository=mock_discount_repository
    )
    
    # Act
    output = await agent.match_discounts(input_data)
    
    # Assert - organic product should be first
    if output.discounts:
        first_discount = output.discounts[0]
        # First item should be organic (Organic Milk with 25% discount)
        assert first_discount.is_organic is True


@pytest.mark.asyncio
async def test_discount_percent_sorting(
    mock_discount_repository: AsyncMock,
    test_location: Location,
    test_timeframe: Timeframe
):
    """Test that discounts are sorted by percentage (highest first)."""
    input_data = DiscountMatchingInput(
        location=test_location,
        radius_km=5.0,
        timeframe=test_timeframe,
        min_discount_percent=10.0,
        prefer_organic=False,  # Don't prioritize organic
    )
    
    agent = DiscountMatcherService(
        discount_repository=mock_discount_repository
    )
    
    # Act
    output = await agent.match_discounts(input_data)
    
    # Assert - should be sorted by discount percent (descending)
    if len(output.discounts) >= 2:
        # First should be 30% discount (Hakket oksekød)
        assert output.discounts[0].discount_percent == 30.0
        # Second should be 25% discount (Organic Milk)
        assert output.discounts[1].discount_percent == 25.0


# ============================================================================
# Test: Caching
# ============================================================================

@pytest.mark.asyncio
async def test_cache_miss_fetches_from_repository(
    mock_discount_repository: AsyncMock,
    mock_cache_repository: AsyncMock,
    basic_input: DiscountMatchingInput
):
    """Test that cache miss triggers repository fetch."""
    # Cache returns None (miss)
    mock_cache_repository.get = AsyncMock(return_value=None)
    
    agent = DiscountMatcherService(
        discount_repository=mock_discount_repository,
        cache_repository=mock_cache_repository
    )
    
    # Act
    output = await agent.match_discounts(basic_input)
    
    # Assert
    assert output.cache_hit is False
    mock_discount_repository.fetch_discounts.assert_called_once()
    mock_cache_repository.get.assert_called_once()
    mock_cache_repository.set.assert_called_once()


@pytest.mark.asyncio
async def test_cache_hit_skips_repository(
    mock_discount_repository: AsyncMock,
    mock_cache_repository: AsyncMock,
    basic_input: DiscountMatchingInput,
    sample_discounts: list[DiscountItem]
):
    """Test that cache hit skips repository fetch."""
    import pickle
    
    # Create cached output
    cached_output = DiscountMatchingOutput(
        discounts=sample_discounts[:2],
        total_found=5,
        total_matched=2,
        filters_applied="cached",
        cache_hit=False,  # Will be set to True by agent
        organic_count=1,
        average_discount_percent=27.5
    )
    
    # Cache returns serialized output (hit)
    mock_cache_repository.get = AsyncMock(return_value=pickle.dumps(cached_output))
    
    agent = DiscountMatcherService(
        discount_repository=mock_discount_repository,
        cache_repository=mock_cache_repository
    )
    
    # Act
    output = await agent.match_discounts(basic_input)
    
    # Assert
    assert output.cache_hit is True
    assert output.total_matched == 2
    # Repository should NOT be called
    mock_discount_repository.fetch_discounts.assert_not_called()
    mock_cache_repository.get.assert_called_once()


@pytest.mark.asyncio
async def test_caching_disabled_skips_cache(
    monkeypatch,
    mock_discount_repository: AsyncMock,
    mock_cache_repository: AsyncMock,
    basic_input: DiscountMatchingInput
):
    """Test that caching is skipped when disabled in settings."""
    from agents.discount_optimizer import config
    
    # Disable caching
    monkeypatch.setattr(config.settings, "enable_caching", False)
    
    agent = DiscountMatcherService(
        discount_repository=mock_discount_repository,
        cache_repository=mock_cache_repository
    )
    
    # Act
    output = await agent.match_discounts(basic_input)
    
    # Assert
    assert output.cache_hit is False
    # Cache should not be accessed
    mock_cache_repository.get.assert_not_called()
    mock_cache_repository.set.assert_not_called()


# ============================================================================
# Test: Statistics Calculation
# ============================================================================

@pytest.mark.asyncio
async def test_statistics_calculation(
    mock_discount_repository: AsyncMock,
    basic_input: DiscountMatchingInput
):
    """Test that output statistics are calculated correctly."""
    agent = DiscountMatcherService(
        discount_repository=mock_discount_repository
    )
    
    # Act
    output = await agent.match_discounts(basic_input)
    
    # Assert
    assert output.total_found == 5  # All discounts from repository
    assert output.total_matched > 0
    assert output.organic_count >= 0
    assert 0.0 <= output.average_discount_percent <= 100.0
    
    # Verify organic count
    actual_organic_count = sum(1 for d in output.discounts if d.is_organic)
    assert output.organic_count == actual_organic_count
    
    # Verify average discount
    if output.discounts:
        expected_avg = sum(d.discount_percent for d in output.discounts) / len(output.discounts)
        assert abs(output.average_discount_percent - expected_avg) < 0.01


# ============================================================================
# Test: Max Results Limiting
# ============================================================================

@pytest.mark.asyncio
async def test_max_results_limiting(
    mock_discount_repository: AsyncMock,
    test_location: Location,
    test_timeframe: Timeframe
):
    """Test that results are limited to max_results."""
    input_data = DiscountMatchingInput(
        location=test_location,
        radius_km=5.0,
        timeframe=test_timeframe,
        min_discount_percent=0.0,  # Accept all
        max_results=2  # Limit to 2 results
    )
    
    agent = DiscountMatcherService(
        discount_repository=mock_discount_repository
    )
    
    # Act
    output = await agent.match_discounts(input_data)
    
    # Assert
    assert len(output.discounts) <= 2


# ============================================================================
# Test: Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_api_error_handling(
    mock_discount_repository: AsyncMock,
    basic_input: DiscountMatchingInput
):
    """Test that API errors are raised (not swallowed)."""
    # Mock repository to raise APIError
    mock_discount_repository.fetch_discounts = AsyncMock(
        side_effect=APIError("API is down")
    )
    
    service = DiscountMatcherService(
        discount_repository=mock_discount_repository
    )
    
    # Act & Assert - should raise APIError
    with pytest.raises(APIError, match="API is down"):
        await service.match_discounts(basic_input)


@pytest.mark.asyncio
async def test_cache_error_handling(
    mock_discount_repository: AsyncMock,
    mock_cache_repository: AsyncMock,
    basic_input: DiscountMatchingInput
):
    """Test that cache errors don't break the agent."""
    # Mock cache to raise exception
    mock_cache_repository.get = AsyncMock(side_effect=Exception("Cache error"))
    mock_cache_repository.set = AsyncMock(side_effect=Exception("Cache error"))
    
    agent = DiscountMatcherService(
        discount_repository=mock_discount_repository,
        cache_repository=mock_cache_repository
    )
    
    # Act - should not raise exception
    output = await agent.match_discounts(basic_input)
    
    # Assert - should still get results from repository
    assert isinstance(output, DiscountMatchingOutput)
    assert output.total_matched > 0


# ============================================================================
# Test: Filters Description
# ============================================================================

def test_filters_description_generation(test_location: Location, test_timeframe: Timeframe):
    """Test that filters description is generated correctly."""
    agent = DiscountMatcherService(
        discount_repository=AsyncMock()
    )
    
    input_data = DiscountMatchingInput(
        location=test_location,
        radius_km=5.0,
        timeframe=test_timeframe,
        min_discount_percent=15.0,
        prefer_organic=True
    )
    
    # Act
    description = agent._build_filters_description(input_data)
    
    # Assert
    assert "5.0km" in description or "5km" in description
    assert "15" in description or "15.0" in description
    assert "organic" in description.lower()


# ============================================================================
# Test: Cache Key Generation
# ============================================================================

def test_cache_key_generation_consistency(
    test_location: Location,
    test_timeframe: Timeframe
):
    """Test that same input generates same cache key."""
    agent = DiscountMatcherService(
        discount_repository=AsyncMock()
    )
    
    input_data = DiscountMatchingInput(
        location=test_location,
        radius_km=5.0,
        timeframe=test_timeframe,
        min_discount_percent=15.0,
        prefer_organic=True
    )
    
    # Generate key twice
    key1 = agent._generate_cache_key(input_data)
    key2 = agent._generate_cache_key(input_data)
    
    # Assert - should be identical
    assert key1 == key2
    assert "discount_match:" in key1


def test_cache_key_generation_different_inputs(
    test_location: Location,
    test_timeframe: Timeframe
):
    """Test that different inputs generate different cache keys."""
    agent = DiscountMatcherService(
        discount_repository=AsyncMock()
    )
    
    input1 = DiscountMatchingInput(
        location=test_location,
        radius_km=5.0,
        timeframe=test_timeframe,
        min_discount_percent=15.0,
    )
    
    input2 = DiscountMatchingInput(
        location=test_location,
        radius_km=10.0,  # Different radius
        timeframe=test_timeframe,
        min_discount_percent=15.0,
    )
    
    # Generate keys
    key1 = agent._generate_cache_key(input1)
    key2 = agent._generate_cache_key(input2)
    
    # Assert - should be different
    assert key1 != key2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

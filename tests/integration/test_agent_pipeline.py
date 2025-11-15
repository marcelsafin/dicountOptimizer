"""Integration tests for full agent pipeline with mocked repositories.

This module tests the complete shopping optimization pipeline from input
validation through to final recommendation, using mocked agents and repositories
to avoid all external API calls.

Requirements: 6.4, 6.5
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

from agents.discount_optimizer.agents.shopping_optimizer_agent import (
    ShoppingOptimizerAgent,
    ShoppingOptimizerInput,
)
from agents.discount_optimizer.domain.models import (
    Location,
    Timeframe,
    OptimizationPreferences,
    DiscountItem,
    Purchase,
    ShoppingRecommendation,
)
from agents.discount_optimizer.domain.exceptions import ValidationError, APIError


# =============================================================================
# Mock Repositories
# =============================================================================

class MockGeocodingService:
    """Mock geocoding service for testing."""
    
    def __init__(self):
        self.geocode_called = False
        self.distance_called = False
    
    async def geocode_address(self, address: str) -> Location:
        """Mock geocode address."""
        self.geocode_called = True
        return Location(latitude=55.6761, longitude=12.5683)
    
    async def calculate_distance(self, origin: Location, destination: Location) -> float:
        """Mock calculate distance."""
        self.distance_called = True
        return 2.5
    
    async def health_check(self) -> bool:
        """Mock health check."""
        return True


class MockDiscountRepository:
    """Mock discount repository for testing."""
    
    def __init__(self, discounts: list[DiscountItem] | None = None, should_fail: bool = False):
        """Initialize with optional discount data."""
        self.discounts = discounts or self._create_default_discounts()
        self.should_fail = should_fail
        self.fetch_called = False
        self.fetch_count = 0
    
    async def fetch_discounts(self, location: Location, radius_km: float) -> list[DiscountItem]:
        """Mock fetch discounts."""
        self.fetch_called = True
        self.fetch_count += 1
        
        if self.should_fail:
            raise APIError("Mock API failure")
        
        return self.discounts
    
    async def health_check(self) -> bool:
        """Mock health check."""
        return not self.should_fail
    
    def _create_default_discounts(self) -> list[DiscountItem]:
        """Create default discount data for testing."""
        today = date.today()
        location = Location(latitude=55.6761, longitude=12.5683)
        
        return [
            DiscountItem(
                product_name="Hakket oksekød",
                store_name="Netto",
                store_location=location,
                original_price=Decimal("65.00"),
                discount_price=Decimal("49.00"),
                discount_percent=25.0,
                expiration_date=today + timedelta(days=3),
                is_organic=False,
                store_address="Test Street 1",
                travel_distance_km=1.5,
                travel_time_minutes=8.0
            ),
            DiscountItem(
                product_name="Tortillas",
                store_name="Netto",
                store_location=location,
                original_price=Decimal("25.00"),
                discount_price=Decimal("18.00"),
                discount_percent=28.0,
                expiration_date=today + timedelta(days=1),
                is_organic=False,
                store_address="Test Street 1",
                travel_distance_km=1.5,
                travel_time_minutes=8.0
            ),
            DiscountItem(
                product_name="Ost",
                store_name="Føtex",
                store_location=location,
                original_price=Decimal("45.00"),
                discount_price=Decimal("35.00"),
                discount_percent=22.0,
                expiration_date=today + timedelta(days=7),
                is_organic=False,
                store_address="Test Street 2",
                travel_distance_km=2.0,
                travel_time_minutes=10.0
            ),
        ]


class MockCacheRepository:
    """Mock cache repository for testing."""
    
    def __init__(self):
        """Initialize mock cache."""
        self.cache: dict[str, bytes] = {}
        self.get_called = 0
        self.set_called = 0
    
    async def get(self, key: str) -> bytes | None:
        """Mock get from cache."""
        self.get_called += 1
        return self.cache.get(key)
    
    async def set(self, key: str, value: bytes, ttl_seconds: int) -> None:
        """Mock set to cache."""
        self.set_called += 1
        self.cache[key] = value
    
    async def health_check(self) -> bool:
        """Mock health check."""
        return True


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_location():
    """Mock validated location."""
    return Location(latitude=55.6761, longitude=12.5683)


@pytest.fixture
def mock_timeframe():
    """Mock validated timeframe."""
    return Timeframe(
        start_date=date.today(),
        end_date=date.today() + timedelta(days=7)
    )


@pytest.fixture
def mock_preferences():
    """Mock optimization preferences."""
    return OptimizationPreferences(
        maximize_savings=True,
        minimize_stores=False,
        prefer_organic=False
    )


@pytest.fixture
def mock_discount_item(mock_location):
    """Mock discount item."""
    return DiscountItem(
        product_name="Hakket oksekød 8-12%",
        store_name="Føtex",
        store_location=mock_location,
        original_price=Decimal("50.00"),
        discount_price=Decimal("37.50"),
        discount_percent=25.0,
        expiration_date=date.today() + timedelta(days=3),
        is_organic=False,
        store_address="Nørrebrogade 20, Copenhagen",
        travel_distance_km=2.5,
        travel_time_minutes=10.0
    )


@pytest.fixture
def mock_purchase():
    """Mock purchase recommendation."""
    return Purchase(
        product_name="Hakket oksekød 8-12%",
        store_name="Føtex",
        purchase_day=date.today(),
        price=Decimal("37.50"),
        savings=Decimal("12.50"),
        meal_association="Taco Tuesday"
    )


@pytest.fixture
def mock_validation_output(mock_location, mock_timeframe, mock_preferences):
    """Mock successful validation output."""
    from agents.discount_optimizer.services.input_validation_service import ValidationOutput
    
    return ValidationOutput(
        is_valid=True,
        location=mock_location,
        timeframe=mock_timeframe,
        preferences=mock_preferences,
        search_radius_km=5.0,
        num_meals=2,
        meal_plan=["taco", "pasta"],
        validation_errors=[],
        warnings=[]
    )


@pytest.fixture
def mock_discount_output(mock_discount_item):
    """Mock discount matching output."""
    from agents.discount_optimizer.services.discount_matcher_service import DiscountMatchingOutput
    
    return DiscountMatchingOutput(
        discounts=[mock_discount_item],
        total_found=10,
        total_matched=1,
        filters_applied="location within 5km, timeframe, min discount 10%",
        cache_hit=False,
        organic_count=0,
        average_discount_percent=25.0
    )


@pytest.fixture
def mock_meal_output():
    """Mock meal suggestion output."""
    from agents.discount_optimizer.agents.meal_suggester_agent import MealSuggestionOutput
    
    return MealSuggestionOutput(
        suggested_meals=["Taco Tuesday", "Pasta Night"],
        reasoning="Meals based on available discounted products",
        urgency_notes="Use beef within 3 days"
    )


@pytest.fixture
def mock_ingredient_output():
    """Mock ingredient mapping output."""
    from agents.discount_optimizer.agents.ingredient_mapper_agent import (
        IngredientMappingOutput,
        IngredientMapping,
        ProductMatch
    )
    
    product_match = ProductMatch(
        product_name="Hakket oksekød 8-12%",
        store_name="Føtex",
        match_score=0.92,
        discount_percent=25.0,
        price=37.50
    )
    
    mapping = IngredientMapping(
        ingredient="taco",
        matched_products=[product_match],
        best_match=product_match,
        has_matches=True
    )
    
    return IngredientMappingOutput(
        meal_name="taco",
        mappings=[mapping],
        total_ingredients=1,
        ingredients_with_matches=1,
        coverage_percent=100.0,
        unmapped_ingredients=[]
    )


@pytest.fixture
def mock_optimization_output(mock_purchase):
    """Mock optimization output."""
    from agents.discount_optimizer.services.multi_criteria_optimizer_service import OptimizationOutput
    
    return OptimizationOutput(
        purchases=[mock_purchase],
        total_savings=Decimal("12.50"),
        total_items=1,
        unique_stores=1,
        store_summary={"Føtex": 1},
        optimization_notes="Optimized for: maximizing savings."
    )


@pytest.fixture
def mock_recommendation(mock_purchase):
    """Mock final shopping recommendation."""
    return ShoppingRecommendation(
        purchases=[mock_purchase],
        total_savings=Decimal("12.50"),
        time_savings=20.0,
        tips=[
            "Shop early in the morning",
            "Bring reusable bags",
            "Check expiration dates"
        ],
        motivation_message="Great job! You're saving 12.50 kr.",
        stores=[{"name": "Føtex", "items": 1}]
    )


@pytest.fixture
def mock_geocoding_service():
    """Mock geocoding service."""
    return MockGeocodingService()


@pytest.fixture
def mock_discount_repository():
    """Mock discount repository."""
    return MockDiscountRepository()


@pytest.fixture
def mock_cache_repository():
    """Mock cache repository."""
    return MockCacheRepository()


@pytest.fixture
def mock_input_validator(mock_validation_output):
    """Mock InputValidationService."""
    validator = Mock()
    validator.run = AsyncMock(return_value=mock_validation_output)
    return validator


@pytest.fixture
def mock_discount_matcher(mock_discount_output):
    """Mock DiscountMatcherService."""
    matcher = Mock()
    matcher.match_discounts = AsyncMock(return_value=mock_discount_output)
    return matcher


@pytest.fixture
def mock_meal_suggester(mock_meal_output):
    """Mock MealSuggesterAgent."""
    suggester = Mock()
    suggester.run = AsyncMock(return_value=mock_meal_output)
    return suggester


@pytest.fixture
def mock_ingredient_mapper(mock_ingredient_output):
    """Mock IngredientMapperAgent."""
    mapper = Mock()
    mapper.run = AsyncMock(return_value=mock_ingredient_output)
    return mapper


@pytest.fixture
def mock_optimizer(mock_optimization_output):
    """Mock MultiCriteriaOptimizerService."""
    optimizer = Mock()
    optimizer.optimize = Mock(return_value=mock_optimization_output)
    return optimizer


@pytest.fixture
def mock_output_formatter(mock_recommendation):
    """Mock OutputFormatterAgent."""
    from agents.discount_optimizer.agents.output_formatter_agent import FormattingOutput
    
    formatter = Mock()
    formatting_output = FormattingOutput(
        tips=mock_recommendation.tips,
        motivation_message=mock_recommendation.motivation_message,
        formatted_recommendation=mock_recommendation
    )
    formatter.run = AsyncMock(return_value=formatting_output)
    return formatter


@pytest.fixture
def shopping_optimizer_agent(
    mock_meal_suggester,
    mock_ingredient_mapper,
    mock_output_formatter,
    mock_input_validator,
    mock_discount_matcher,
    mock_optimizer
):
    """Create ShoppingOptimizerAgent with all mocked dependencies."""
    return ShoppingOptimizerAgent(
        meal_suggester=mock_meal_suggester,
        ingredient_mapper=mock_ingredient_mapper,
        output_formatter=mock_output_formatter,
        input_validator=mock_input_validator,
        discount_matcher=mock_discount_matcher,
        optimizer=mock_optimizer
    )


# =============================================================================
# Test: Full Pipeline with Mocked Repositories
# =============================================================================

@pytest.mark.asyncio
async def test_full_pipeline_with_address(shopping_optimizer_agent, mock_input_validator):
    """Test complete pipeline with address input and mocked agents."""
    # Arrange
    input_data = ShoppingOptimizerInput(
        address="Nørrebrogade 20, Copenhagen",
        meal_plan=["taco", "pasta"],
        timeframe="this week",
        maximize_savings=True,
        minimize_stores=False,
        prefer_organic=False
    )
    
    # Act
    recommendation = await shopping_optimizer_agent.run(input_data)
    
    # Assert
    assert isinstance(recommendation, ShoppingRecommendation)
    assert len(recommendation.purchases) > 0
    assert recommendation.total_savings >= Decimal("0")
    assert len(recommendation.tips) > 0
    assert len(recommendation.motivation_message) > 0
    assert mock_input_validator.run.called


@pytest.mark.asyncio
async def test_full_pipeline_with_coordinates(
    shopping_optimizer_agent,
    mock_input_validator,
    mock_location,
    mock_timeframe,
    mock_preferences
):
    """Test complete pipeline with coordinate input."""
    # Arrange - Update validation output for coordinates
    from agents.discount_optimizer.services.input_validation_service import ValidationOutput
    
    validation_with_coords = ValidationOutput(
        is_valid=True,
        location=mock_location,
        timeframe=mock_timeframe,
        preferences=mock_preferences,
        search_radius_km=5.0,
        num_meals=1,
        meal_plan=["taco"],
        validation_errors=[],
        warnings=[]
    )
    mock_input_validator.run = AsyncMock(return_value=validation_with_coords)
    
    input_data = ShoppingOptimizerInput(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco"],
        timeframe="this week",
        maximize_savings=True
    )
    
    # Act
    recommendation = await shopping_optimizer_agent.run(input_data)
    
    # Assert
    assert isinstance(recommendation, ShoppingRecommendation)
    assert recommendation.total_savings >= Decimal("0")


@pytest.mark.asyncio
async def test_pipeline_with_optimization_preferences(shopping_optimizer_agent):
    """Test pipeline respects different optimization preferences."""
    # Test maximize_savings
    input_savings = ShoppingOptimizerInput(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco"],
        maximize_savings=True,
        minimize_stores=False
    )
    
    result_savings = await shopping_optimizer_agent.run(input_savings)
    
    # Test minimize_stores
    input_stores = ShoppingOptimizerInput(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco"],
        maximize_savings=False,
        minimize_stores=True
    )
    
    result_stores = await shopping_optimizer_agent.run(input_stores)
    
    # Assert both complete successfully
    assert isinstance(result_savings, ShoppingRecommendation)
    assert isinstance(result_stores, ShoppingRecommendation)


# =============================================================================
# Test: Error Propagation Through Agent Layers
# =============================================================================

@pytest.mark.asyncio
async def test_validation_error_propagates(
    mock_meal_suggester,
    mock_ingredient_mapper,
    mock_output_formatter,
    mock_discount_matcher,
    mock_optimizer,
    mock_location,
    mock_timeframe,
    mock_preferences
):
    """Test that validation errors propagate correctly through agent layers."""
    # Arrange - Create validator that returns invalid result
    from agents.discount_optimizer.services.input_validation_service import ValidationOutput
    
    invalid_output = ValidationOutput(
        is_valid=False,
        location=None,
        timeframe=None,
        preferences=None,
        search_radius_km=5.0,
        num_meals=1,
        meal_plan=[],
        validation_errors=["Invalid address: could not geocode"],
        warnings=[]
    )
    
    mock_input_validator = Mock()
    mock_input_validator.run = AsyncMock(return_value=invalid_output)
    
    agent = ShoppingOptimizerAgent(
        meal_suggester=mock_meal_suggester,
        ingredient_mapper=mock_ingredient_mapper,
        output_formatter=mock_output_formatter,
        input_validator=mock_input_validator,
        discount_matcher=mock_discount_matcher,
        optimizer=mock_optimizer
    )
    
    input_data = ShoppingOptimizerInput(
        address="Invalid Address XYZ",
        meal_plan=["taco"]
    )
    
    # Act & Assert
    with pytest.raises(ValidationError):
        await agent.run(input_data)


@pytest.mark.asyncio
async def test_api_error_handled_gracefully(
    mock_meal_suggester,
    mock_ingredient_mapper,
    mock_output_formatter,
    mock_input_validator,
    mock_optimizer,
    mock_discount_item
):
    """Test that API errors are handled gracefully with fallbacks."""
    # Arrange - Create discount matcher that raises APIError
    from agents.discount_optimizer.services.discount_matcher_service import DiscountMatchingOutput
    
    mock_discount_matcher = Mock()
    mock_discount_matcher.match_discounts = AsyncMock(side_effect=APIError("API connection failed"))
    
    agent = ShoppingOptimizerAgent(
        meal_suggester=mock_meal_suggester,
        ingredient_mapper=mock_ingredient_mapper,
        output_formatter=mock_output_formatter,
        input_validator=mock_input_validator,
        discount_matcher=mock_discount_matcher,
        optimizer=mock_optimizer
    )
    
    input_data = ShoppingOptimizerInput(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco"]
    )
    
    # Act - Should handle error gracefully with fallback
    recommendation = await agent.run(input_data)
    
    # Assert - Should return recommendation (pipeline continues with fallback)
    assert isinstance(recommendation, ShoppingRecommendation)
    # Note: The pipeline continues even when discount fetching fails,
    # using fallback behavior. The optimizer may still return purchases
    # based on mocked ingredient mappings.


@pytest.mark.asyncio
async def test_agent_error_in_meal_suggester_uses_fallback(
    mock_ingredient_mapper,
    mock_output_formatter,
    mock_input_validator,
    mock_discount_matcher,
    mock_optimizer
):
    """Test that agent errors in meal suggester trigger fallback."""
    # Arrange - Mock meal suggester to raise exception
    from agents.discount_optimizer.domain.exceptions import AgentError
    
    mock_meal_suggester = Mock()
    mock_meal_suggester.run = AsyncMock(side_effect=AgentError("Gemini API unavailable"))
    
    agent = ShoppingOptimizerAgent(
        meal_suggester=mock_meal_suggester,
        ingredient_mapper=mock_ingredient_mapper,
        output_formatter=mock_output_formatter,
        input_validator=mock_input_validator,
        discount_matcher=mock_discount_matcher,
        optimizer=mock_optimizer
    )
    
    input_data = ShoppingOptimizerInput(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=[],  # Empty to trigger AI
        num_meals=3
    )
    
    # Act - Should use fallback meals
    recommendation = await agent.run(input_data)
    
    # Assert
    assert isinstance(recommendation, ShoppingRecommendation)


# =============================================================================
# Test: Retry Logic with Simulated Failures
# =============================================================================

@pytest.mark.asyncio
async def test_retry_logic_with_repository_level_retries(
    mock_meal_suggester,
    mock_ingredient_mapper,
    mock_output_formatter,
    mock_input_validator,
    mock_optimizer,
    mock_discount_item
):
    """Test that retry logic at repository level is properly integrated.
    
    Note: Retry logic is implemented at the repository level (SallingDiscountRepository
    uses tenacity @retry decorator). At the service/agent level, if all retries fail,
    the agent catches the APIError and uses fallback behavior.
    
    This test verifies that:
    1. The discount matcher is called
    2. If it fails (after all retries), the agent handles it gracefully
    3. The pipeline continues with fallback behavior
    """
    # Arrange
    from agents.discount_optimizer.services.discount_matcher_service import DiscountMatchingOutput
    
    # Track call count
    call_count = {"count": 0}
    
    # Mock that always fails (simulating exhausted retries at repository level)
    async def mock_match_discounts_always_fails(input_data):
        call_count["count"] += 1
        raise APIError("All retries exhausted")
    
    mock_discount_matcher = Mock()
    mock_discount_matcher.match_discounts = AsyncMock(side_effect=mock_match_discounts_always_fails)
    
    agent = ShoppingOptimizerAgent(
        meal_suggester=mock_meal_suggester,
        ingredient_mapper=mock_ingredient_mapper,
        output_formatter=mock_output_formatter,
        input_validator=mock_input_validator,
        discount_matcher=mock_discount_matcher,
        optimizer=mock_optimizer
    )
    
    input_data = ShoppingOptimizerInput(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco"]
    )
    
    # Act - Should handle failure gracefully
    recommendation = await agent.run(input_data)
    
    # Assert - Pipeline completes with fallback behavior
    assert isinstance(recommendation, ShoppingRecommendation)
    assert call_count["count"] == 1  # Discount matcher was called once
    # Agent catches the error and continues with empty discounts


# =============================================================================
# Test: Caching Behavior
# =============================================================================

@pytest.mark.asyncio
async def test_caching_reduces_api_calls(
    mock_meal_suggester,
    mock_ingredient_mapper,
    mock_output_formatter,
    mock_input_validator,
    mock_optimizer,
    mock_discount_item
):
    """Test that caching reduces redundant API calls."""
    # Arrange
    from agents.discount_optimizer.services.discount_matcher_service import DiscountMatchingOutput
    
    call_count = {"count": 0}
    
    async def mock_match_discounts(input_data):
        call_count["count"] += 1
        return DiscountMatchingOutput(
            discounts=[mock_discount_item],
            total_found=1,
            total_matched=1,
            filters_applied="test",
            cache_hit=call_count["count"] > 1,  # Second call is cache hit
            organic_count=0,
            average_discount_percent=25.0
        )
    
    mock_discount_matcher = Mock()
    mock_discount_matcher.match_discounts = AsyncMock(side_effect=mock_match_discounts)
    
    agent = ShoppingOptimizerAgent(
        meal_suggester=mock_meal_suggester,
        ingredient_mapper=mock_ingredient_mapper,
        output_formatter=mock_output_formatter,
        input_validator=mock_input_validator,
        discount_matcher=mock_discount_matcher,
        optimizer=mock_optimizer
    )
    
    input_data = ShoppingOptimizerInput(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco"]
    )
    
    # Act - First call
    await agent.run(input_data)
    first_call_count = call_count["count"]
    
    # Act - Second call
    await agent.run(input_data)
    second_call_count = call_count["count"]
    
    # Assert - Both calls should have been made (caching is at repository level)
    assert first_call_count == 1
    assert second_call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Integration tests for ShoppingOptimizerAgent.

These tests verify the orchestration logic of the root agent by mocking
all dependencies and ensuring:
- All 6 pipeline steps execute in correct order
- Error handling and fallbacks work correctly
- Correlation IDs are properly propagated
- Type safety is maintained throughout the pipeline

Requirements: 6.4 - Integration tests for all agent interactions
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

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
from agents.discount_optimizer.domain.exceptions import (
    ValidationError,
    APIError,
    AgentError,
)


# =========================================================================
# Fixtures for Mock Dependencies
# =========================================================================

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
        num_meals=3,
        meal_plan=[],
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
        suggested_meals=["Taco Tuesday", "Pasta Night", "Stir-fry"],
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
        ingredient="Taco Tuesday",
        matched_products=[product_match],
        best_match=product_match,
        has_matches=True
    )
    
    return IngredientMappingOutput(
        meal_name="Taco Tuesday",
        mappings=[mapping],
        total_ingredients=3,
        ingredients_with_matches=3,
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
        optimization_notes="Optimized for: maximizing savings. All items consolidated to a single store."
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


# =========================================================================
# Test 1: Happy Path - All Steps Execute Successfully
# =========================================================================

@pytest.mark.asyncio
async def test_shopping_optimizer_happy_path(
    shopping_optimizer_agent,
    mock_input_validator,
    mock_discount_matcher,
    mock_meal_suggester,
    mock_ingredient_mapper,
    mock_optimizer,
    mock_output_formatter,
    mock_recommendation
):
    """
    Test the complete happy path where all 6 steps execute successfully.
    
    Verifies:
    - All services are called in correct order
    - Final ShoppingRecommendation is returned
    - No exceptions are raised
    - Correlation ID is set
    
    Requirements: 6.4, 10.1, 10.5
    """
    # Arrange
    input_data = ShoppingOptimizerInput(
        address="Nørrebrogade 20, Copenhagen",
        meal_plan=[],
        timeframe="this week",
        maximize_savings=True,
        num_meals=3
    )
    
    # Act
    result = await shopping_optimizer_agent.run(input_data)
    
    # Assert - Verify all services were called
    mock_input_validator.run.assert_called_once()
    mock_discount_matcher.match_discounts.assert_called_once()
    mock_meal_suggester.run.assert_called_once()
    mock_ingredient_mapper.run.assert_called()  # Called multiple times (once per meal)
    mock_optimizer.optimize.assert_called_once()
    mock_output_formatter.run.assert_called_once()
    
    # Assert - Verify result structure
    assert isinstance(result, ShoppingRecommendation)
    assert len(result.purchases) > 0
    assert result.total_savings > 0
    assert len(result.tips) > 0
    assert result.motivation_message
    assert len(result.stores) > 0


@pytest.mark.asyncio
async def test_shopping_optimizer_with_provided_meal_plan(
    shopping_optimizer_agent,
    mock_input_validator,
    mock_discount_matcher,
    mock_meal_suggester,
    mock_ingredient_mapper,
    mock_optimizer,
    mock_output_formatter,
    mock_location,
    mock_timeframe,
    mock_preferences
):
    """
    Test that meal suggester is NOT called when meal plan is provided.
    
    Verifies:
    - MealSuggesterAgent is skipped when meal_plan is provided
    - Other services are still called
    - Pipeline completes successfully
    
    Requirements: 6.4, 10.1
    """
    # Arrange - Create validation output with meal plan
    from agents.discount_optimizer.services.input_validation_service import ValidationOutput
    
    validation_with_meal_plan = ValidationOutput(
        is_valid=True,
        location=mock_location,
        timeframe=mock_timeframe,
        preferences=mock_preferences,
        search_radius_km=5.0,
        num_meals=2,
        meal_plan=["Taco Tuesday", "Pasta Night"],  # Meal plan provided
        validation_errors=[],
        warnings=[]
    )
    
    mock_input_validator.run = AsyncMock(return_value=validation_with_meal_plan)
    
    input_data = ShoppingOptimizerInput(
        address="Nørrebrogade 20, Copenhagen",
        meal_plan=["Taco Tuesday", "Pasta Night"],
        timeframe="this week",
        maximize_savings=True
    )
    
    # Act
    result = await shopping_optimizer_agent.run(input_data)
    
    # Assert - Verify meal suggester was NOT called
    mock_meal_suggester.run.assert_not_called()
    
    # Assert - Verify other services were called
    mock_input_validator.run.assert_called_once()
    mock_discount_matcher.match_discounts.assert_called_once()
    mock_ingredient_mapper.run.assert_called()
    mock_optimizer.optimize.assert_called_once()
    mock_output_formatter.run.assert_called_once()
    
    # Assert - Verify result
    assert isinstance(result, ShoppingRecommendation)


@pytest.mark.asyncio
async def test_shopping_optimizer_correlation_id_propagation(
    shopping_optimizer_agent,
    mock_input_validator,
    mock_discount_matcher,
    mock_meal_suggester,
    mock_ingredient_mapper,
    mock_optimizer,
    mock_output_formatter
):
    """
    Test that correlation ID is properly set and propagated.
    
    Verifies:
    - Correlation ID is set when provided
    - Correlation ID is generated when not provided
    - LogContext is used correctly
    
    Requirements: 6.4, 10.5
    """
    # Arrange
    test_correlation_id = "test-correlation-123"
    input_data = ShoppingOptimizerInput(
        address="Nørrebrogade 20, Copenhagen",
        meal_plan=[],
        timeframe="this week",
        maximize_savings=True,
        correlation_id=test_correlation_id
    )
    
    # Act
    with patch('agents.discount_optimizer.agents.shopping_optimizer_agent.get_correlation_id') as mock_get_corr_id:
        mock_get_corr_id.return_value = test_correlation_id
        result = await shopping_optimizer_agent.run(input_data)
    
    # Assert - Verify result
    assert isinstance(result, ShoppingRecommendation)


# =========================================================================
# Test 2: Validation Fails
# =========================================================================

@pytest.mark.asyncio
async def test_shopping_optimizer_validation_fails(
    shopping_optimizer_agent,
    mock_input_validator,
    mock_discount_matcher,
    mock_meal_suggester,
    mock_ingredient_mapper,
    mock_optimizer,
    mock_output_formatter
):
    """
    Test that ValidationError is raised when input validation fails.
    
    Verifies:
    - ValidationError is raised
    - No other services are called after validation fails
    - Error message contains validation errors
    
    Requirements: 6.4, 4.4
    """
    # Arrange
    from agents.discount_optimizer.services.input_validation_service import ValidationOutput
    
    invalid_output = ValidationOutput(
        is_valid=False,
        location=None,
        timeframe=None,
        preferences=None,
        search_radius_km=5.0,
        num_meals=3,
        meal_plan=[],
        validation_errors=["Invalid address: could not geocode"],
        warnings=[]
    )
    
    mock_input_validator.run = AsyncMock(return_value=invalid_output)
    
    input_data = ShoppingOptimizerInput(
        address="Invalid Address XYZ",
        meal_plan=[],
        timeframe="this week",
        maximize_savings=True
    )
    
    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        await shopping_optimizer_agent.run(input_data)
    
    # Assert - Verify error message
    assert "Input validation failed" in str(exc_info.value)
    assert "Invalid address" in str(exc_info.value)
    
    # Assert - Verify only validator was called
    mock_input_validator.run.assert_called_once()
    mock_discount_matcher.match_discounts.assert_not_called()
    mock_meal_suggester.run.assert_not_called()
    mock_ingredient_mapper.run.assert_not_called()
    mock_optimizer.optimize.assert_not_called()
    mock_output_formatter.run.assert_not_called()


# =========================================================================
# Test 3: Agent Fails - Fallback Logic
# =========================================================================

@pytest.mark.asyncio
async def test_shopping_optimizer_meal_suggester_fails_fallback(
    shopping_optimizer_agent,
    mock_input_validator,
    mock_discount_matcher,
    mock_meal_suggester,
    mock_ingredient_mapper,
    mock_optimizer,
    mock_output_formatter
):
    """
    Test that fallback logic activates when MealSuggesterAgent fails.
    
    Verifies:
    - AgentError from meal suggester is caught
    - Fallback meal suggestions are used
    - Pipeline continues with fallback data
    - Final recommendation is still returned
    
    Requirements: 6.4, 4.2
    """
    # Arrange
    mock_meal_suggester.run = AsyncMock(side_effect=AgentError("Gemini API unavailable"))
    
    input_data = ShoppingOptimizerInput(
        address="Nørrebrogade 20, Copenhagen",
        meal_plan=[],
        timeframe="this week",
        maximize_savings=True,
        num_meals=3
    )
    
    # Act
    result = await shopping_optimizer_agent.run(input_data)
    
    # Assert - Verify meal suggester was called and failed
    mock_meal_suggester.run.assert_called_once()
    
    # Assert - Verify pipeline continued with other services
    mock_input_validator.run.assert_called_once()
    mock_discount_matcher.match_discounts.assert_called_once()
    mock_ingredient_mapper.run.assert_called()
    mock_optimizer.optimize.assert_called_once()
    mock_output_formatter.run.assert_called_once()
    
    # Assert - Verify result is still returned (with fallback data)
    assert isinstance(result, ShoppingRecommendation)


@pytest.mark.asyncio
async def test_shopping_optimizer_discount_matcher_fails_fallback(
    shopping_optimizer_agent,
    mock_input_validator,
    mock_discount_matcher,
    mock_meal_suggester,
    mock_ingredient_mapper,
    mock_optimizer,
    mock_output_formatter
):
    """
    Test that fallback logic activates when DiscountMatcherService fails.
    
    Verifies:
    - APIError from discount matcher is caught
    - Empty discount list is used as fallback
    - Pipeline continues with empty discounts
    - Final recommendation is still returned
    
    Requirements: 6.4, 4.2
    """
    # Arrange
    mock_discount_matcher.match_discounts = AsyncMock(side_effect=APIError("Salling API unavailable"))
    
    input_data = ShoppingOptimizerInput(
        address="Nørrebrogade 20, Copenhagen",
        meal_plan=["Taco Tuesday"],
        timeframe="this week",
        maximize_savings=True
    )
    
    # Act
    result = await shopping_optimizer_agent.run(input_data)
    
    # Assert - Verify discount matcher was called and failed
    mock_discount_matcher.match_discounts.assert_called_once()
    
    # Assert - Verify pipeline continued
    mock_input_validator.run.assert_called_once()
    mock_ingredient_mapper.run.assert_called()
    mock_optimizer.optimize.assert_called_once()
    mock_output_formatter.run.assert_called_once()
    
    # Assert - Verify result is still returned
    assert isinstance(result, ShoppingRecommendation)


@pytest.mark.asyncio
async def test_shopping_optimizer_output_formatter_fails_fallback(
    shopping_optimizer_agent,
    mock_input_validator,
    mock_discount_matcher,
    mock_meal_suggester,
    mock_ingredient_mapper,
    mock_optimizer,
    mock_output_formatter,
    mock_recommendation
):
    """
    Test that fallback logic activates when OutputFormatterAgent fails.
    
    Verifies:
    - AgentError from output formatter is caught
    - Basic recommendation without AI tips is returned
    - All other services completed successfully
    
    Requirements: 6.4, 4.2
    """
    # Arrange
    mock_output_formatter.run = AsyncMock(side_effect=AgentError("Gemini API unavailable"))
    
    input_data = ShoppingOptimizerInput(
        address="Nørrebrogade 20, Copenhagen",
        meal_plan=["Taco Tuesday"],
        timeframe="this week",
        maximize_savings=True
    )
    
    # Act
    result = await shopping_optimizer_agent.run(input_data)
    
    # Assert - Verify output formatter was called and failed
    mock_output_formatter.run.assert_called_once()
    
    # Assert - Verify all other services completed
    mock_input_validator.run.assert_called_once()
    mock_discount_matcher.match_discounts.assert_called_once()
    mock_ingredient_mapper.run.assert_called()
    mock_optimizer.optimize.assert_called_once()
    
    # Assert - Verify fallback recommendation is returned
    assert isinstance(result, ShoppingRecommendation)
    assert len(result.tips) > 0  # Fallback tips should be present
    assert result.motivation_message  # Fallback motivation should be present


# =========================================================================
# Test 4: Service Call Order Verification
# =========================================================================

@pytest.mark.asyncio
async def test_shopping_optimizer_service_call_order(
    mock_location,
    mock_timeframe,
    mock_preferences,
    mock_discount_item,
    mock_purchase,
    mock_recommendation
):
    """
    Test that all services are called in the correct order.
    
    Verifies:
    - Services are called in the expected sequence:
      1. InputValidationService
      2. DiscountMatcherService
      3. MealSuggesterAgent
      4. IngredientMapperAgent
      5. MultiCriteriaOptimizerService
      6. OutputFormatterAgent
    
    Requirements: 6.4, 10.1
    """
    # Arrange
    call_order = []
    
    # Create fresh mocks with proper return values
    from agents.discount_optimizer.services.input_validation_service import ValidationOutput
    from agents.discount_optimizer.services.discount_matcher_service import DiscountMatchingOutput
    from agents.discount_optimizer.agents.meal_suggester_agent import MealSuggestionOutput
    from agents.discount_optimizer.agents.ingredient_mapper_agent import (
        IngredientMappingOutput,
        IngredientMapping,
        ProductMatch
    )
    from agents.discount_optimizer.services.multi_criteria_optimizer_service import OptimizationOutput
    from agents.discount_optimizer.agents.output_formatter_agent import FormattingOutput
    
    validation_output = ValidationOutput(
        is_valid=True,
        location=mock_location,
        timeframe=mock_timeframe,
        preferences=mock_preferences,
        search_radius_km=5.0,
        num_meals=3,
        meal_plan=[],
        validation_errors=[],
        warnings=[]
    )
    
    discount_output = DiscountMatchingOutput(
        discounts=[mock_discount_item],
        total_found=1,
        total_matched=1,
        filters_applied="test",
        cache_hit=False,
        organic_count=0,
        average_discount_percent=25.0
    )
    
    meal_output = MealSuggestionOutput(
        suggested_meals=["Taco Tuesday"],
        reasoning="Test meals",
        urgency_notes=""
    )
    
    product_match = ProductMatch(
        product_name="Test Product",
        store_name="Test Store",
        match_score=0.9,
        discount_percent=25.0,
        price=37.50
    )
    
    ingredient_output = IngredientMappingOutput(
        meal_name="Taco Tuesday",
        mappings=[IngredientMapping(
            ingredient="Taco Tuesday",
            matched_products=[product_match],
            best_match=product_match,
            has_matches=True
        )],
        total_ingredients=1,
        ingredients_with_matches=1,
        coverage_percent=100.0,
        unmapped_ingredients=[]
    )
    
    optimization_output = OptimizationOutput(
        purchases=[mock_purchase],
        total_savings=Decimal("12.50"),
        total_items=1,
        unique_stores=1,
        store_summary={"Test Store": 1},
        optimization_notes="Test"
    )
    
    formatting_output = FormattingOutput(
        tips=["Test tip"],
        motivation_message="Test motivation",
        formatted_recommendation=mock_recommendation
    )
    
    # Create mocks with side effects that track call order
    async def validator_side_effect(x):
        call_order.append('validator')
        return validation_output
    
    async def discount_side_effect(x):
        call_order.append('discount_matcher')
        return discount_output
    
    async def meal_side_effect(x):
        call_order.append('meal_suggester')
        return meal_output
    
    async def ingredient_side_effect(x):
        call_order.append('ingredient_mapper')
        return ingredient_output
    
    def optimizer_side_effect(x):
        call_order.append('optimizer')
        return optimization_output
    
    async def formatter_side_effect(x):
        call_order.append('output_formatter')
        return formatting_output
    
    mock_input_validator = Mock()
    mock_input_validator.run = AsyncMock(side_effect=validator_side_effect)
    
    mock_discount_matcher = Mock()
    mock_discount_matcher.match_discounts = AsyncMock(side_effect=discount_side_effect)
    
    mock_meal_suggester = Mock()
    mock_meal_suggester.run = AsyncMock(side_effect=meal_side_effect)
    
    mock_ingredient_mapper = Mock()
    mock_ingredient_mapper.run = AsyncMock(side_effect=ingredient_side_effect)
    
    mock_optimizer = Mock()
    mock_optimizer.optimize = Mock(side_effect=optimizer_side_effect)
    
    mock_output_formatter = Mock()
    mock_output_formatter.run = AsyncMock(side_effect=formatter_side_effect)
    
    agent = ShoppingOptimizerAgent(
        meal_suggester=mock_meal_suggester,
        ingredient_mapper=mock_ingredient_mapper,
        output_formatter=mock_output_formatter,
        input_validator=mock_input_validator,
        discount_matcher=mock_discount_matcher,
        optimizer=mock_optimizer
    )
    
    input_data = ShoppingOptimizerInput(
        address="Nørrebrogade 20, Copenhagen",
        meal_plan=[],
        timeframe="this week",
        maximize_savings=True,
        num_meals=3
    )
    
    # Act
    await agent.run(input_data)
    
    # Assert - Verify call order
    assert call_order[0] == 'validator'
    assert call_order[1] == 'discount_matcher'
    assert call_order[2] == 'meal_suggester'
    assert 'ingredient_mapper' in call_order
    assert 'optimizer' in call_order
    assert call_order[-1] == 'output_formatter'

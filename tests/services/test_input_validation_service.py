"""
Unit tests for InputValidationService with mocked GeocodingService.

This test suite verifies the service implementation without making real
API calls. All geocoding responses are mocked using pytest-mock.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date, timedelta

from agents.discount_optimizer.services.input_validation_service import (
    InputValidationService,
    ValidationInput,
    ValidationOutput,
)
from agents.discount_optimizer.domain.models import Location
from agents.discount_optimizer.domain.exceptions import ValidationError as DomainValidationError


# ============================================================================
# Mock GeocodingService
# ============================================================================

class MockGeocodingService:
    """Mock implementation of GeocodingService protocol."""
    
    def __init__(self):
        self.geocode_calls = []
        self.distance_calls = []
    
    async def geocode_address(self, address: str) -> Location:
        """Mock geocode_address method."""
        self.geocode_calls.append(address)
        
        # Return different locations based on address
        if "copenhagen" in address.lower() or "nørrebrogade" in address.lower():
            return Location(latitude=55.6761, longitude=12.5683)
        elif "aarhus" in address.lower():
            return Location(latitude=56.1629, longitude=10.2039)
        elif "invalid" in address.lower():
            raise Exception("Geocoding failed: Invalid address")
        else:
            # Default location
            return Location(latitude=55.0, longitude=12.0)
    
    async def calculate_distance(
        self,
        origin: Location,
        destination: Location
    ) -> float:
        """Mock calculate_distance method."""
        self.distance_calls.append((origin, destination))
        return 5.2  # Default distance
    
    async def health_check(self) -> bool:
        """Mock health check method."""
        return True


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_geocoding_service() -> MockGeocodingService:
    """Fixture providing a mock geocoding service."""
    return MockGeocodingService()


@pytest.fixture
def agent(mock_geocoding_service: MockGeocodingService) -> InputValidationService:
    """Fixture providing an InputValidationService with mock service."""
    return InputValidationService(geocoding_service=mock_geocoding_service)


@pytest.fixture
def valid_input_with_address() -> ValidationInput:
    """Fixture providing valid input with address."""
    return ValidationInput(
        address="Nørrebrogade 20, Copenhagen",
        timeframe="this week",
        maximize_savings=True
    )


@pytest.fixture
def valid_input_with_coordinates() -> ValidationInput:
    """Fixture providing valid input with coordinates."""
    return ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="next 7 days",
        maximize_savings=True
    )


@pytest.fixture
def valid_input_with_meal_plan() -> ValidationInput:
    """Fixture providing valid input with meal plan."""
    return ValidationInput(
        address="Aarhus, Denmark",
        meal_plan=["Taco Tuesday", "Pasta Night", "Salad Bowl"],
        timeframe="this week",
        maximize_savings=True,
        minimize_stores=True
    )


# ============================================================================
# Test: Service Initialization
# ============================================================================

def test_service_initialization_with_valid_service(mock_geocoding_service):
    """Test that service initializes correctly with valid geocoding service."""
    service = InputValidationService(geocoding_service=mock_geocoding_service)
    
    assert service.geocoding_service is not None
    assert service.geocoding_service == mock_geocoding_service


def test_service_initialization_with_invalid_service():
    """Test that service raises TypeError with invalid geocoding service."""
    # Pass a non-protocol-compliant object
    invalid_service = "not a geocoding service"
    
    with pytest.raises(TypeError, match="must implement GeocodingService protocol"):
        InputValidationService(geocoding_service=invalid_service)  # type: ignore


# ============================================================================
# Test: Input Validation - Valid Cases
# ============================================================================

def test_input_validation_valid_with_address():
    """Test that valid input with address is accepted."""
    input_data = ValidationInput(
        address="Copenhagen, Denmark",
        timeframe="this week",
        maximize_savings=True
    )
    
    assert input_data.address == "Copenhagen, Denmark"
    assert input_data.timeframe == "this week"
    assert input_data.maximize_savings is True


def test_input_validation_valid_with_coordinates():
    """Test that valid input with coordinates is accepted."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="next 3 days",
        maximize_savings=True
    )
    
    assert input_data.latitude == 55.6761
    assert input_data.longitude == 12.5683


def test_input_validation_valid_with_meal_plan():
    """Test that valid input with meal plan is accepted."""
    input_data = ValidationInput(
        address="Aarhus, Denmark",
        meal_plan=["Taco", "Pasta", "Salad"],
        timeframe="this week"
    )
    
    assert len(input_data.meal_plan) == 3


# ============================================================================
# Test: Input Validation - Invalid Cases
# ============================================================================

def test_input_validation_invalid_latitude():
    """Test that invalid latitude is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        ValidationInput(
            latitude=200,  # Invalid: > 90
            longitude=12.5683,
            timeframe="this week"
        )


def test_input_validation_invalid_longitude():
    """Test that invalid longitude is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        ValidationInput(
            latitude=55.6761,
            longitude=200,  # Invalid: > 180
            timeframe="this week"
        )


def test_input_validation_invalid_search_radius():
    """Test that invalid search radius is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        ValidationInput(
            address="Copenhagen",
            search_radius_km=-5,  # Invalid: negative
            timeframe="this week"
        )


def test_input_validation_invalid_num_meals():
    """Test that invalid num_meals is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        ValidationInput(
            address="Copenhagen",
            num_meals=0,  # Invalid: < 1
            timeframe="this week"
        )


# ============================================================================
# Test: Location Validation - Address
# ============================================================================

@pytest.mark.asyncio
async def test_validate_location_with_valid_address(
    agent: InputValidationService,
    valid_input_with_address: ValidationInput,
    mock_geocoding_service: MockGeocodingService
):
    """Test that valid address is geocoded correctly."""
    output = await agent.run(valid_input_with_address)
    
    assert output.is_valid is True
    assert output.location is not None
    assert output.location.latitude == 55.6761
    assert output.location.longitude == 12.5683
    assert len(output.validation_errors) == 0
    
    # Verify geocoding service was called
    assert len(mock_geocoding_service.geocode_calls) == 1
    assert "Nørrebrogade" in mock_geocoding_service.geocode_calls[0]


@pytest.mark.asyncio
async def test_validate_location_with_invalid_address(
    agent: InputValidationService,
    mock_geocoding_service: MockGeocodingService
):
    """Test that invalid address produces validation error."""
    input_data = ValidationInput(
        address="Invalid Address That Cannot Be Geocoded",
        timeframe="this week"
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is False
    assert output.location is None
    assert len(output.validation_errors) > 0
    assert any("geocode" in error.lower() for error in output.validation_errors)


# ============================================================================
# Test: Location Validation - Coordinates
# ============================================================================

@pytest.mark.asyncio
async def test_validate_location_with_valid_coordinates(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput,
    mock_geocoding_service: MockGeocodingService
):
    """Test that valid coordinates are accepted without geocoding."""
    output = await agent.run(valid_input_with_coordinates)
    
    assert output.is_valid is True
    assert output.location is not None
    assert output.location.latitude == 55.6761
    assert output.location.longitude == 12.5683
    assert len(output.validation_errors) == 0
    
    # Verify geocoding service was NOT called (coordinates provided)
    assert len(mock_geocoding_service.geocode_calls) == 0


@pytest.mark.asyncio
async def test_validate_location_missing_both_address_and_coordinates(
    agent: InputValidationService
):
    """Test that missing location produces validation error."""
    input_data = ValidationInput(
        timeframe="this week",
        maximize_savings=True
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is False
    assert output.location is None
    assert len(output.validation_errors) > 0
    assert any("location is required" in error.lower() for error in output.validation_errors)


# ============================================================================
# Test: Timeframe Validation
# ============================================================================

@pytest.mark.asyncio
async def test_validate_timeframe_this_week(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput
):
    """Test that 'this week' timeframe is parsed correctly."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="this week"
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is True
    assert output.timeframe is not None
    assert output.timeframe.start_date == date.today()
    assert output.timeframe.end_date == date.today() + timedelta(days=7)


@pytest.mark.asyncio
async def test_validate_timeframe_today(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput
):
    """Test that 'today' timeframe is parsed correctly."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="today"
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is True
    assert output.timeframe is not None
    assert output.timeframe.start_date == date.today()
    assert output.timeframe.end_date == date.today()


@pytest.mark.asyncio
async def test_validate_timeframe_next_3_days(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput
):
    """Test that 'next 3 days' timeframe is parsed correctly."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="next 3 days"
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is True
    assert output.timeframe is not None
    assert output.timeframe.start_date == date.today()
    assert output.timeframe.end_date == date.today() + timedelta(days=3)


@pytest.mark.asyncio
async def test_validate_timeframe_next_week(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput
):
    """Test that 'next week' timeframe is parsed correctly."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="next week"
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is True
    assert output.timeframe is not None
    assert output.timeframe.start_date == date.today() + timedelta(days=7)
    assert output.timeframe.end_date == date.today() + timedelta(days=14)


@pytest.mark.asyncio
async def test_validate_timeframe_too_long(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput
):
    """Test that timeframe > 30 days produces validation error."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="next 45 days"
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is False
    assert len(output.validation_errors) > 0
    assert any("too long" in error.lower() for error in output.validation_errors)


@pytest.mark.asyncio
async def test_validate_timeframe_unparseable_defaults_with_warning(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput
):
    """Test that unparseable timeframe defaults to 7 days with warning."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="some random text"
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is True
    assert output.timeframe is not None
    assert output.timeframe.start_date == date.today()
    assert output.timeframe.end_date == date.today() + timedelta(days=7)
    assert len(output.warnings) > 0
    assert any("could not parse" in warning.lower() for warning in output.warnings)


# ============================================================================
# Test: Preferences Validation
# ============================================================================

@pytest.mark.asyncio
async def test_validate_preferences_all_true(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput
):
    """Test that all preferences can be True."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="this week",
        maximize_savings=True,
        minimize_stores=True,
        prefer_organic=True
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is True
    assert output.preferences is not None
    assert output.preferences.maximize_savings is True
    assert output.preferences.minimize_stores is True
    assert output.preferences.prefer_organic is True


@pytest.mark.asyncio
async def test_validate_preferences_defaults(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput
):
    """Test that preferences have correct defaults."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="this week"
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is True
    assert output.preferences is not None
    assert output.preferences.maximize_savings is True  # Default
    assert output.preferences.minimize_stores is False  # Default
    assert output.preferences.prefer_organic is False  # Default


# ============================================================================
# Test: Search Radius Validation
# ============================================================================

@pytest.mark.asyncio
async def test_validate_search_radius_custom(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput
):
    """Test that custom search radius is accepted."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="this week",
        search_radius_km=10.0
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is True
    assert output.search_radius_km == 10.0


@pytest.mark.asyncio
async def test_validate_search_radius_default(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput
):
    """Test that search radius defaults to settings value."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="this week"
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is True
    assert output.search_radius_km > 0  # Should use default from settings


@pytest.mark.asyncio
async def test_validate_search_radius_too_large_rejected():
    """Test that search radius > 50 km is rejected by Pydantic."""
    # Pydantic validation should reject this at input level
    with pytest.raises(Exception):  # Pydantic ValidationError
        ValidationInput(
            latitude=55.6761,
            longitude=12.5683,
            timeframe="this week",
            search_radius_km=100.0  # Max is 50
        )


# ============================================================================
# Test: Meal Plan Validation
# ============================================================================

@pytest.mark.asyncio
async def test_validate_meal_plan_with_meals(
    agent: InputValidationService,
    valid_input_with_meal_plan: ValidationInput
):
    """Test that meal plan with meals is validated correctly."""
    output = await agent.run(valid_input_with_meal_plan)
    
    assert output.is_valid is True
    assert len(output.meal_plan) == 3
    assert "Taco Tuesday" in output.meal_plan
    assert "Pasta Night" in output.meal_plan
    assert "Salad Bowl" in output.meal_plan


@pytest.mark.asyncio
async def test_validate_meal_plan_empty_means_ai_suggestions(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput
):
    """Test that empty meal plan means AI suggestions will be used."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="this week",
        meal_plan=[]
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is True
    assert len(output.meal_plan) == 0


@pytest.mark.asyncio
async def test_validate_meal_plan_filters_empty_strings(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput
):
    """Test that empty strings in meal plan are filtered out."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="this week",
        meal_plan=["Taco", "", "  ", "Pasta", ""]
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is True
    assert len(output.meal_plan) == 2
    assert "Taco" in output.meal_plan
    assert "Pasta" in output.meal_plan


@pytest.mark.asyncio
async def test_validate_meal_plan_too_many_meals_rejected():
    """Test that meal plan > 20 meals is rejected by Pydantic."""
    # Pydantic validation should reject this at input level
    with pytest.raises(Exception):  # Pydantic ValidationError
        ValidationInput(
            latitude=55.6761,
            longitude=12.5683,
            timeframe="this week",
            meal_plan=[f"Meal {i}" for i in range(25)]  # Max is 20
        )


# ============================================================================
# Test: Number of Meals Validation
# ============================================================================

@pytest.mark.asyncio
async def test_validate_num_meals_from_meal_plan(
    agent: InputValidationService,
    valid_input_with_meal_plan: ValidationInput
):
    """Test that num_meals is derived from meal plan length."""
    output = await agent.run(valid_input_with_meal_plan)
    
    assert output.is_valid is True
    assert output.num_meals == 3  # From meal plan length


@pytest.mark.asyncio
async def test_validate_num_meals_custom(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput
):
    """Test that custom num_meals is accepted."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="this week",
        num_meals=5
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is True
    assert output.num_meals == 5


@pytest.mark.asyncio
async def test_validate_num_meals_default(
    agent: InputValidationService,
    valid_input_with_coordinates: ValidationInput
):
    """Test that num_meals defaults to 3."""
    input_data = ValidationInput(
        latitude=55.6761,
        longitude=12.5683,
        timeframe="this week"
    )
    
    output = await agent.run(input_data)
    
    assert output.is_valid is True
    assert output.num_meals == 3  # Default


@pytest.mark.asyncio
async def test_validate_num_meals_too_large_rejected():
    """Test that num_meals > 10 is rejected by Pydantic."""
    # Pydantic validation should reject this at input level
    with pytest.raises(Exception):  # Pydantic ValidationError
        ValidationInput(
            latitude=55.6761,
            longitude=12.5683,
            timeframe="this week",
            num_meals=15  # Max is 10
        )


# ============================================================================
# Test: Output Validation
# ============================================================================

def test_output_validation_valid():
    """Test that valid output is accepted."""
    output = ValidationOutput(
        is_valid=True,
        location=Location(latitude=55.6761, longitude=12.5683),
        timeframe=None,
        preferences=None,
        search_radius_km=5.0,
        num_meals=3,
        meal_plan=[],
        validation_errors=[],
        warnings=[]
    )
    
    assert output.is_valid is True
    assert output.location is not None


# ============================================================================
# Test: Complete Validation Flow
# ============================================================================

@pytest.mark.asyncio
async def test_complete_validation_flow_success(
    agent: InputValidationService,
    valid_input_with_address: ValidationInput
):
    """Test complete validation flow with all valid inputs."""
    output = await agent.run(valid_input_with_address)
    
    assert output.is_valid is True
    assert output.location is not None
    assert output.timeframe is not None
    assert output.preferences is not None
    assert output.search_radius_km > 0
    assert output.num_meals > 0
    assert len(output.validation_errors) == 0


@pytest.mark.asyncio
async def test_complete_validation_flow_multiple_errors(
    agent: InputValidationService
):
    """Test that multiple validation errors are collected at agent level."""
    input_data = ValidationInput(
        # Missing location (will be caught by agent)
        timeframe="next 100 days",  # Too long (will be caught by agent)
        maximize_savings=True
    )
    
    output = await agent.run(input_data)
    
    # Should have validation errors for missing location and timeframe too long
    assert output.is_valid is False
    assert len(output.validation_errors) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

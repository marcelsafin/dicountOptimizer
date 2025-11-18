"""
Unit tests for MultiCriteriaOptimizerService.

This test suite verifies the multi-criteria optimization algorithm including:
- Scoring calculations for different preferences
- Store consolidation logic
- Purchase day optimization
- Type safety and validation
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from agents.discount_optimizer.domain.models import (
    Location,
    OptimizationPreferences,
)
from agents.discount_optimizer.services.multi_criteria_optimizer_service import (
    MultiCriteriaOptimizerService,
    OptimizationInput,
    OptimizationOutput,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def user_location() -> Location:
    """Fixture providing user location (Copenhagen)."""
    return Location(latitude=55.6761, longitude=12.5683)


@pytest.fixture
def store_location_nearby() -> Location:
    """Fixture providing nearby store location."""
    return Location(latitude=55.6800, longitude=12.5700)


@pytest.fixture
def store_location_far() -> Location:
    """Fixture providing far store location."""
    return Location(latitude=55.7500, longitude=12.7000)


@pytest.fixture
def discount_item_high_savings(store_location_nearby: Location) -> dict:
    """Fixture providing discount item with high savings."""
    return {
        "product_name": "Organic Milk",
        "store_name": "Føtex",
        "store_location": {
            "latitude": store_location_nearby.latitude,
            "longitude": store_location_nearby.longitude,
        },
        "original_price": 30.00,
        "discount_price": 15.00,  # 50% off
        "discount_percent": 50.0,
        "expiration_date": date.today() + timedelta(days=5),
        "is_organic": True,
        "store_address": "Føtex Copenhagen",
        "travel_distance_km": 0.5,
        "travel_time_minutes": 5.0,
    }


@pytest.fixture
def discount_item_low_savings(store_location_far: Location) -> dict:
    """Fixture providing discount item with low savings but far away."""
    return {
        "product_name": "Regular Milk",
        "store_name": "Netto",
        "store_location": {
            "latitude": store_location_far.latitude,
            "longitude": store_location_far.longitude,
        },
        "original_price": 20.00,
        "discount_price": 18.00,  # 10% off
        "discount_percent": 10.0,
        "expiration_date": date.today() + timedelta(days=5),
        "is_organic": False,
        "store_address": "Netto Far Away",
        "travel_distance_km": 10.0,
        "travel_time_minutes": 30.0,
    }


@pytest.fixture
def basic_optimization_input(
    user_location: Location, discount_item_high_savings: dict, discount_item_low_savings: dict
) -> OptimizationInput:
    """Fixture providing basic optimization input."""
    return OptimizationInput(
        ingredient_matches={"milk": [discount_item_high_savings, discount_item_low_savings]},
        preferences=OptimizationPreferences(
            maximize_savings=True, minimize_stores=False, prefer_organic=False
        ),
        user_location=user_location,
        timeframe_start=date.today(),
        timeframe_end=date.today() + timedelta(days=7),
    )


# ============================================================================
# Test: Service Initialization
# ============================================================================


def test_service_initialization():
    """Test that service initializes correctly."""
    service = MultiCriteriaOptimizerService()

    assert service is not None


# ============================================================================
# Test: Input Validation
# ============================================================================


def test_input_validation_valid(basic_optimization_input: OptimizationInput):
    """Test that valid input is accepted."""
    assert len(basic_optimization_input.ingredient_matches) == 1
    assert basic_optimization_input.preferences.maximize_savings is True


def test_input_validation_end_before_start(user_location: Location):
    """Test that timeframe_end before timeframe_start is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        OptimizationInput(
            ingredient_matches={"milk": []},
            preferences=OptimizationPreferences(maximize_savings=True),
            user_location=user_location,
            timeframe_start=date.today(),
            timeframe_end=date.today() - timedelta(days=1),  # Invalid
        )


# ============================================================================
# Test: Output Validation
# ============================================================================


def test_output_validation_valid():
    """Test that valid output is accepted."""
    output = OptimizationOutput(
        purchases=[],
        total_savings=Decimal("50.00"),
        total_items=5,
        unique_stores=2,
        store_summary={"Føtex": 3, "Netto": 2},
        optimization_notes="Optimized for savings",
    )

    assert output.total_savings == Decimal("50.00")
    assert output.unique_stores == 2


# ============================================================================
# Test: Distance Calculation
# ============================================================================


def test_calculate_distance():
    """Test Haversine distance calculation."""
    service = MultiCriteriaOptimizerService()

    # Copenhagen to Aarhus (approximately 157 km)
    copenhagen = Location(latitude=55.6761, longitude=12.5683)
    aarhus = Location(latitude=56.1629, longitude=10.2039)

    distance = service._calculate_distance(copenhagen, aarhus)

    # Should be approximately 157 km (allow some tolerance)
    assert 150 < distance < 170


def test_calculate_distance_same_location():
    """Test distance calculation for same location."""
    service = MultiCriteriaOptimizerService()

    location = Location(latitude=55.6761, longitude=12.5683)
    distance = service._calculate_distance(location, location)

    assert distance == 0.0


# ============================================================================
# Test: Scoring Algorithm - Maximize Savings
# ============================================================================


def test_optimize_maximize_savings(basic_optimization_input: OptimizationInput):
    """Test that maximize_savings preference selects highest discount."""
    service = MultiCriteriaOptimizerService()

    # Set preference to maximize savings only
    basic_optimization_input.preferences = OptimizationPreferences(
        maximize_savings=True, minimize_stores=False, prefer_organic=False
    )

    output = service.optimize(basic_optimization_input)

    # Should select the item with 50% discount (high savings)
    assert len(output.purchases) == 1
    assert output.purchases[0].product_name == "Organic Milk"
    assert output.purchases[0].store_name == "Føtex"
    assert output.total_savings == Decimal("15.00")


# ============================================================================
# Test: Scoring Algorithm - Minimize Stores
# ============================================================================


def test_optimize_minimize_stores(
    user_location: Location, discount_item_high_savings: dict, store_location_nearby: Location
):
    """Test that minimize_stores preference selects nearby stores."""
    service = MultiCriteriaOptimizerService()

    # Create items from same store vs different stores
    item_nearby = discount_item_high_savings.copy()
    item_nearby["product_name"] = "Bread"
    item_nearby["store_name"] = "Føtex"

    item_far = discount_item_high_savings.copy()
    item_far["product_name"] = "Cheese"
    item_far["store_name"] = "Netto"
    item_far["store_location"] = {"latitude": 55.7500, "longitude": 12.7000}

    input_data = OptimizationInput(
        ingredient_matches={"bread": [item_nearby], "cheese": [item_far]},
        preferences=OptimizationPreferences(
            maximize_savings=False, minimize_stores=True, prefer_organic=False
        ),
        user_location=user_location,
        timeframe_start=date.today(),
        timeframe_end=date.today() + timedelta(days=7),
    )

    output = service.optimize(input_data)

    # Should select items, preferring nearby store
    assert len(output.purchases) == 2


# ============================================================================
# Test: Scoring Algorithm - Prefer Organic
# ============================================================================


def test_optimize_prefer_organic(user_location: Location):
    """Test that prefer_organic preference selects organic products."""
    service = MultiCriteriaOptimizerService()

    # Create organic and non-organic items
    organic_item = {
        "product_name": "Organic Milk",
        "store_name": "Føtex",
        "store_location": {"latitude": 55.6800, "longitude": 12.5700},
        "original_price": 30.00,
        "discount_price": 25.00,
        "discount_percent": 16.67,
        "expiration_date": date.today() + timedelta(days=5),
        "is_organic": True,
        "store_address": "Føtex",
        "travel_distance_km": 0.5,
        "travel_time_minutes": 5.0,
    }

    regular_item = {
        "product_name": "Regular Milk",
        "store_name": "Netto",
        "store_location": {"latitude": 55.6800, "longitude": 12.5700},
        "original_price": 20.00,
        "discount_price": 15.00,
        "discount_percent": 25.0,
        "expiration_date": date.today() + timedelta(days=5),
        "is_organic": False,
        "store_address": "Netto",
        "travel_distance_km": 0.5,
        "travel_time_minutes": 5.0,
    }

    input_data = OptimizationInput(
        ingredient_matches={"milk": [organic_item, regular_item]},
        preferences=OptimizationPreferences(
            maximize_savings=False, minimize_stores=False, prefer_organic=True
        ),
        user_location=user_location,
        timeframe_start=date.today(),
        timeframe_end=date.today() + timedelta(days=7),
    )

    output = service.optimize(input_data)

    # Should select organic item despite lower discount
    assert len(output.purchases) == 1
    assert output.purchases[0].product_name == "Organic Milk"
    assert output.purchases[0].store_name == "Føtex"


# ============================================================================
# Test: Store Consolidation Logic
# ============================================================================


def test_store_consolidation_bonus(user_location: Location):
    """Test that store consolidation bonus affects selection."""
    service = MultiCriteriaOptimizerService()

    # Create multiple items from same store
    fotex_item1 = {
        "product_name": "Milk",
        "store_name": "Føtex",
        "store_location": {"latitude": 55.6800, "longitude": 12.5700},
        "original_price": 30.00,
        "discount_price": 25.00,
        "discount_percent": 16.67,
        "expiration_date": date.today() + timedelta(days=5),
        "is_organic": False,
        "store_address": "Føtex",
        "travel_distance_km": 0.5,
        "travel_time_minutes": 5.0,
    }

    fotex_item2 = {
        "product_name": "Bread",
        "store_name": "Føtex",
        "store_location": {"latitude": 55.6800, "longitude": 12.5700},
        "original_price": 20.00,
        "discount_price": 15.00,
        "discount_percent": 25.0,
        "expiration_date": date.today() + timedelta(days=5),
        "is_organic": False,
        "store_address": "Føtex",
        "travel_distance_km": 0.5,
        "travel_time_minutes": 5.0,
    }

    input_data = OptimizationInput(
        ingredient_matches={"milk": [fotex_item1], "bread": [fotex_item2]},
        preferences=OptimizationPreferences(
            maximize_savings=True, minimize_stores=True, prefer_organic=False
        ),
        user_location=user_location,
        timeframe_start=date.today(),
        timeframe_end=date.today() + timedelta(days=7),
    )

    output = service.optimize(input_data)

    # Should consolidate to single store
    assert output.unique_stores == 1
    assert output.store_summary["Føtex"] == 2


# ============================================================================
# Test: Purchase Day Optimization
# ============================================================================


def test_calculate_optimal_purchase_day_urgent():
    """Test purchase day for items expiring soon."""
    service = MultiCriteriaOptimizerService()

    timeframe_start = date.today()
    expiration_date = date.today() + timedelta(days=2)  # Expires in 2 days

    purchase_day = service._calculate_optimal_purchase_day(expiration_date, timeframe_start)

    # Should buy immediately
    assert purchase_day == timeframe_start


def test_calculate_optimal_purchase_day_soon():
    """Test purchase day for items expiring within a week."""
    service = MultiCriteriaOptimizerService()

    timeframe_start = date.today()
    expiration_date = date.today() + timedelta(days=5)  # Expires in 5 days

    purchase_day = service._calculate_optimal_purchase_day(expiration_date, timeframe_start)

    # Should buy within first few days
    assert purchase_day == timeframe_start


def test_calculate_optimal_purchase_day_flexible():
    """Test purchase day for items with longer expiration."""
    service = MultiCriteriaOptimizerService()

    timeframe_start = date.today()
    expiration_date = date.today() + timedelta(days=14)  # Expires in 2 weeks

    purchase_day = service._calculate_optimal_purchase_day(expiration_date, timeframe_start)

    # Can buy anytime
    assert purchase_day == timeframe_start


# ============================================================================
# Test: Optimization Notes Generation
# ============================================================================


def test_generate_optimization_notes_single_store():
    """Test optimization notes for single store."""
    service = MultiCriteriaOptimizerService()

    preferences = OptimizationPreferences(
        maximize_savings=True, minimize_stores=True, prefer_organic=False
    )
    store_summary = {"Føtex": 5}
    total_savings = Decimal("45.50")

    notes = service._generate_optimization_notes(preferences, store_summary, total_savings)

    assert "single store" in notes.lower()
    assert "45.50" in notes


def test_generate_optimization_notes_multiple_stores():
    """Test optimization notes for multiple stores."""
    service = MultiCriteriaOptimizerService()

    preferences = OptimizationPreferences(
        maximize_savings=True, minimize_stores=False, prefer_organic=False
    )
    store_summary = {"Føtex": 3, "Netto": 2}
    total_savings = Decimal("30.00")

    notes = service._generate_optimization_notes(preferences, store_summary, total_savings)

    assert "2 stores" in notes
    assert "30.00" in notes


# ============================================================================
# Test: Empty Input Handling
# ============================================================================


def test_optimize_empty_matches(user_location: Location):
    """Test optimization with no ingredient matches."""
    service = MultiCriteriaOptimizerService()

    input_data = OptimizationInput(
        ingredient_matches={},  # Empty
        preferences=OptimizationPreferences(maximize_savings=True),
        user_location=user_location,
        timeframe_start=date.today(),
        timeframe_end=date.today() + timedelta(days=7),
    )

    output = service.optimize(input_data)

    assert len(output.purchases) == 0
    assert output.total_savings == Decimal("0.00")
    assert output.unique_stores == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

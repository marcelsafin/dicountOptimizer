"""
Example: Agent Composition and Usage

This example demonstrates how to use the Shopping Optimizer agent system
with various configurations and patterns.
"""

import asyncio
from datetime import date
from decimal import Decimal

from agents.discount_optimizer.agents.shopping_optimizer_agent import (
    ShoppingOptimizerInput,
)
from agents.discount_optimizer.config import settings
from agents.discount_optimizer.domain.exceptions import (
    APIError,
    ShoppingOptimizerError,
    ValidationError,
)
from agents.discount_optimizer.factory import (
    AgentFactory,
    create_production_agent,
    create_test_agent,
)


# =========================================================================
# Example 1: Basic Usage with Factory
# =========================================================================


async def example_basic_usage():
    """
    Simplest way to use the Shopping Optimizer.

    The factory handles all dependency injection and wiring.
    """
    print("=" * 70)
    print("Example 1: Basic Usage with Factory")
    print("=" * 70)

    # Create agent with all dependencies wired
    agent = create_production_agent()

    # Create input with address
    input_data = ShoppingOptimizerInput(
        address="Nørrebrogade 20, Copenhagen",
        meal_plan=[],  # Empty for AI suggestions
        timeframe="this week",
        maximize_savings=True,
        num_meals=5,
    )

    try:
        # Run optimization
        recommendation = await agent.run(input_data)

        # Display results
        print("\n✓ Optimization completed successfully!")
        print(f"  Total savings: {recommendation.total_savings} kr")
        print(f"  Time savings: {recommendation.time_savings} minutes")
        print(f"  Stores to visit: {len(recommendation.stores)}")
        print(f"  Total purchases: {len(recommendation.purchases)}")

        print("\n  Purchases:")
        for purchase in recommendation.purchases[:3]:  # Show first 3
            print(f"    - {purchase.product_name} at {purchase.store_name}")
            print(f"      Price: {purchase.price} kr (save {purchase.savings} kr)")

        print("\n  Tips:")
        for tip in recommendation.tips[:3]:  # Show first 3
            print(f"    - {tip}")

        print(f"\n  Motivation: {recommendation.motivation_message}")

    except ValidationError as e:
        print(f"✗ Validation error: {e}")
    except APIError as e:
        print(f"✗ API error: {e}")
    except ShoppingOptimizerError as e:
        print(f"✗ Optimization error: {e}")


# =========================================================================
# Example 2: Using Coordinates Instead of Address
# =========================================================================


async def example_with_coordinates():
    """
    Use coordinates directly instead of address.

    Useful when you already have coordinates or want to avoid geocoding.
    """
    print("\n" + "=" * 70)
    print("Example 2: Using Coordinates")
    print("=" * 70)

    agent = create_production_agent()

    # Copenhagen coordinates
    input_data = ShoppingOptimizerInput(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["Taco", "Pasta Carbonara", "Greek Salad"],
        timeframe="next 3 days",
        maximize_savings=True,
        minimize_stores=True,
    )

    try:
        recommendation = await agent.run(input_data)

        print("\n✓ Found recommendations for provided meal plan")
        print(f"  Meals: {', '.join(input_data.meal_plan)}")
        print(f"  Total savings: {recommendation.total_savings} kr")
        print(f"  Stores: {len(recommendation.stores)}")

    except Exception as e:
        print(f"✗ Error: {e}")


# =========================================================================
# Example 3: Custom Configuration
# =========================================================================


async def example_custom_configuration():
    """
    Use custom configuration for agent behavior.

    Demonstrates how to override default settings.
    """
    print("\n" + "=" * 70)
    print("Example 3: Custom Configuration")
    print("=" * 70)

    from agents.discount_optimizer.config import Settings

    # Create custom settings
    custom_settings = Settings(
        agent_temperature=0.9,  # More creative suggestions
        agent_max_tokens=3000,  # Longer responses
        cache_ttl_seconds=7200,  # 2-hour cache
        max_stores_per_recommendation=2,  # Limit to 2 stores
        min_discount_percent=20.0,  # Only show 20%+ discounts
        enable_ai_meal_suggestions=True,
    )

    print("\n  Custom settings:")
    print(f"    Temperature: {custom_settings.agent_temperature}")
    print(f"    Max tokens: {custom_settings.agent_max_tokens}")
    print(f"    Cache TTL: {custom_settings.cache_ttl_seconds}s")
    print(f"    Max stores: {custom_settings.max_stores_per_recommendation}")
    print(f"    Min discount: {custom_settings.min_discount_percent}%")

    # Create factory with custom settings
    factory = AgentFactory(config=custom_settings)
    agent = factory.create_shopping_optimizer_agent()

    input_data = ShoppingOptimizerInput(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=[],
        timeframe="this week",
        maximize_savings=True,
        num_meals=3,
    )

    try:
        recommendation = await agent.run(input_data)
        print("\n✓ Optimization with custom settings completed")
        print(f"  Total savings: {recommendation.total_savings} kr")

    except Exception as e:
        print(f"✗ Error: {e}")


# =========================================================================
# Example 4: Using Individual Agents
# =========================================================================


async def example_individual_agents():
    """
    Use individual agents directly for specific tasks.

    Useful when you only need one component of the system.
    """
    print("\n" + "=" * 70)
    print("Example 4: Using Individual Agents")
    print("=" * 70)

    from agents.discount_optimizer.agents.meal_suggester_agent import (
        MealSuggesterAgent,
        MealSuggestionInput,
    )

    # Create meal suggester agent
    api_key = settings.google_api_key.get_secret_value()
    meal_suggester = MealSuggesterAgent(api_key=api_key)

    # Suggest meals based on available products
    input_data = MealSuggestionInput(
        available_products=["tortillas", "hakket oksekød", "ost", "tomater", "løg", "salat"],
        num_meals=3,
        meal_types=["lunch", "dinner"],
    )

    try:
        result = await meal_suggester.run(input_data)

        print("\n✓ Meal suggestions generated")
        print("  Suggested meals:")
        for i, meal in enumerate(result.suggested_meals, 1):
            print(f"    {i}. {meal}")

        print(f"\n  Reasoning: {result.reasoning}")

    except Exception as e:
        print(f"✗ Error: {e}")


# =========================================================================
# Example 5: Testing with Mocks
# =========================================================================


async def example_testing_with_mocks():
    """
    Use mocks for testing without real API calls.

    Demonstrates dependency injection for testing.
    """
    print("\n" + "=" * 70)
    print("Example 5: Testing with Mocks")
    print("=" * 70)

    from agents.discount_optimizer.domain.models import DiscountItem, Location

    # Create mock implementations
    class MockGeocodingService:
        """Mock geocoding service for testing."""

        async def geocode_address(self, address: str) -> Location:
            print(f"  [Mock] Geocoding address: {address}")
            return Location(latitude=55.6761, longitude=12.5683)

        async def calculate_distance(self, origin: Location, destination: Location) -> float:
            print("  [Mock] Calculating distance")
            return 1.5  # km

        async def health_check(self) -> bool:
            return True

    class MockDiscountRepository:
        """Mock discount repository for testing."""

        async def fetch_discounts(self, location: Location, radius_km: float) -> list[DiscountItem]:
            print(f"  [Mock] Fetching discounts near {location.latitude}, {location.longitude}")

            # Return mock discount items
            return [
                DiscountItem(
                    product_name="Organic Milk",
                    store_name="Føtex",
                    store_location=location,
                    original_price=Decimal("35.00"),
                    discount_price=Decimal("25.00"),
                    discount_percent=28.6,
                    expiration_date=date(2025, 11, 20),
                    is_organic=True,
                    store_address="Nørrebrogade 20, Copenhagen",
                    travel_distance_km=1.2,
                    travel_time_minutes=15.0,
                ),
                DiscountItem(
                    product_name="Fresh Bread",
                    store_name="Netto",
                    store_location=location,
                    original_price=Decimal("20.00"),
                    discount_price=Decimal("10.00"),
                    discount_percent=50.0,
                    expiration_date=date(2025, 11, 18),
                    is_organic=False,
                    store_address="Nørrebrogade 45, Copenhagen",
                    travel_distance_km=0.8,
                    travel_time_minutes=10.0,
                ),
            ]

        async def health_check(self) -> bool:
            return True

    # Create agent with mocks
    print("\n  Creating agent with mock dependencies...")
    agent = create_test_agent(
        geocoding_service=MockGeocodingService(), discount_repository=MockDiscountRepository()
    )

    input_data = ShoppingOptimizerInput(
        address="Test Address, Copenhagen",
        meal_plan=["Breakfast", "Lunch"],
        timeframe="today",
        maximize_savings=True,
    )

    try:
        print("\n  Running optimization with mocks...")
        recommendation = await agent.run(input_data)

        print("\n✓ Test completed successfully")
        print(f"  Total savings: {recommendation.total_savings} kr")
        print(f"  Purchases: {len(recommendation.purchases)}")

    except Exception as e:
        print(f"✗ Error: {e}")


# =========================================================================
# Example 6: Error Handling Patterns
# =========================================================================


async def example_error_handling():
    """
    Demonstrate comprehensive error handling.

    Shows how to handle different types of errors gracefully.
    """
    print("\n" + "=" * 70)
    print("Example 6: Error Handling Patterns")
    print("=" * 70)

    agent = create_production_agent()

    # Test 1: Invalid coordinates
    print("\n  Test 1: Invalid coordinates")
    try:
        input_data = ShoppingOptimizerInput(
            latitude=999.0,  # Invalid latitude
            longitude=12.5683,
            meal_plan=[],
            timeframe="this week",
        )
        await agent.run(input_data)
    except ValidationError as e:
        print(f"  ✓ Caught validation error: {e}")

    # Test 2: Invalid timeframe
    print("\n  Test 2: Invalid timeframe")
    try:
        input_data = ShoppingOptimizerInput(
            latitude=55.6761, longitude=12.5683, meal_plan=[], timeframe="invalid timeframe format"
        )
        await agent.run(input_data)
    except ValidationError as e:
        print(f"  ✓ Caught validation error: {e}")

    # Test 3: Empty meal plan with num_meals=0
    print("\n  Test 3: Invalid num_meals")
    try:
        input_data = ShoppingOptimizerInput(
            latitude=55.6761,
            longitude=12.5683,
            meal_plan=[],
            num_meals=0,  # Invalid
            timeframe="this week",
        )
        await agent.run(input_data)
    except ValidationError as e:
        print(f"  ✓ Caught validation error: {e}")

    print("\n  All error handling tests completed")


# =========================================================================
# Example 7: Correlation IDs for Tracing
# =========================================================================


async def example_correlation_ids():
    """
    Use correlation IDs for distributed tracing.

    Useful for debugging and monitoring in production.
    """
    print("\n" + "=" * 70)
    print("Example 7: Correlation IDs for Tracing")
    print("=" * 70)

    import uuid

    agent = create_production_agent()

    # Generate correlation ID
    correlation_id = str(uuid.uuid4())

    print(f"\n  Correlation ID: {correlation_id}")

    input_data = ShoppingOptimizerInput(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["Taco"],
        timeframe="today",
        maximize_savings=True,
        correlation_id=correlation_id,  # Pass correlation ID
    )

    try:
        recommendation = await agent.run(input_data)

        print("\n✓ Request completed")
        print(f"  Correlation ID: {correlation_id}")
        print(f"  Total savings: {recommendation.total_savings} kr")
        print(f"\n  Check logs for entries with correlation_id={correlation_id}")

    except Exception as e:
        print(f"✗ Error (correlation_id={correlation_id}): {e}")


# =========================================================================
# Main Function
# =========================================================================


async def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("Shopping Optimizer Agent Composition Examples")
    print("=" * 70)

    # Run examples
    await example_basic_usage()
    await example_with_coordinates()
    await example_custom_configuration()
    await example_individual_agents()
    await example_testing_with_mocks()
    await example_error_handling()
    await example_correlation_ids()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    # Run async main function
    asyncio.run(main())

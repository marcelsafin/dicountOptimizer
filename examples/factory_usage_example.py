"""
Example: Using AgentFactory for dependency injection.

This example demonstrates how to use the AgentFactory to create
fully-wired agent instances for both production and testing scenarios.
"""

import asyncio

from agents.discount_optimizer.agents.shopping_optimizer_agent import ShoppingOptimizerInput
from agents.discount_optimizer.domain.models import Location
from agents.discount_optimizer.factory import (
    AgentFactory,
    create_production_agent,
    create_test_agent,
)


async def production_example():
    """
    Example: Create and use a production agent.

    This is the simplest way to create a production-ready agent
    with all real services and repositories.
    """
    print("=" * 60)
    print("Production Example")
    print("=" * 60)

    # Create production agent using convenience function
    agent = create_production_agent()

    # Create input data
    input_data = ShoppingOptimizerInput(
        address="Nørrebrogade 20, Copenhagen",
        meal_plan=[],  # Empty for AI suggestions
        timeframe="this week",
        maximize_savings=True,
        num_meals=3,
    )

    print("\nInput:")
    print(f"  Address: {input_data.address}")
    print(f"  Timeframe: {input_data.timeframe}")
    print(f"  Meal plan: {'AI suggestions' if not input_data.meal_plan else input_data.meal_plan}")
    print(f"  Preferences: maximize_savings={input_data.maximize_savings}")

    # Run optimization
    try:
        recommendation = await agent.run(input_data)

        print("\nResults:")
        print(f"  Total purchases: {len(recommendation.purchases)}")
        print(f"  Total savings: {recommendation.total_savings} kr")
        print(f"  Time savings: {recommendation.time_savings:.0f} minutes")
        print(f"  Stores to visit: {len(recommendation.stores)}")
        print(f"  Tips: {len(recommendation.tips)}")

    except Exception as e:
        print(f"\nError: {e}")


async def factory_example():
    """
    Example: Create agent using factory with custom configuration.

    This demonstrates how to use the factory directly for more control
    over the agent creation process.
    """
    print("\n" + "=" * 60)
    print("Factory Example")
    print("=" * 60)

    # Create factory
    factory = AgentFactory()

    # Create agent with all dependencies wired
    agent = factory.create_shopping_optimizer_agent()

    # Verify all dependencies are wired
    print("\nAgent dependencies:")
    print(f"  Meal Suggester: {type(agent.meal_suggester).__name__}")
    print(f"  Ingredient Mapper: {type(agent.ingredient_mapper).__name__}")
    print(f"  Output Formatter: {type(agent.output_formatter).__name__}")
    print(f"  Input Validator: {type(agent.input_validator).__name__}")
    print(f"  Discount Matcher: {type(agent.discount_matcher).__name__}")
    print(f"  Optimizer: {type(agent.optimizer).__name__}")

    print("\nAgent is ready to use!")


async def test_example():
    """
    Example: Create agent with mock dependencies for testing.

    This demonstrates how to inject mock implementations for testing
    without modifying the agent code.
    """
    print("\n" + "=" * 60)
    print("Test Example (with mocks)")
    print("=" * 60)

    # Create mock geocoding service
    class MockGeocodingService:
        async def geocode_address(self, address: str) -> Location:
            print(f"  [MOCK] Geocoding address: {address}")
            return Location(latitude=55.6761, longitude=12.5683)

        async def calculate_distance(self, origin: Location, destination: Location) -> float:
            return 2.5

        async def health_check(self) -> bool:
            return True

    # Create mock discount repository
    class MockDiscountRepository:
        async def fetch_discounts(self, location: Location, radius_km: float) -> list:
            print(f"  [MOCK] Fetching discounts near ({location.latitude}, {location.longitude})")
            return []

        async def health_check(self) -> bool:
            return True

    # Create agent with mocks
    mock_geocoding = MockGeocodingService()
    mock_discounts = MockDiscountRepository()

    agent = create_test_agent(
        geocoding_service=mock_geocoding,
        discount_repository=mock_discounts,
    )

    print("\nAgent created with mock dependencies")
    print("  Geocoding: MockGeocodingService")
    print("  Discounts: MockDiscountRepository")

    # Create input data
    input_data = ShoppingOptimizerInput(
        address="Test Address",
        meal_plan=["Pasta", "Salad"],
        timeframe="today",
        maximize_savings=True,
    )

    print("\nRunning with test input:")
    print(f"  Address: {input_data.address}")
    print(f"  Meal plan: {input_data.meal_plan}")

    # Run optimization (will use mocks)
    try:
        recommendation = await agent.run(input_data)
        print("\nTest completed successfully!")
        print(f"  Purchases: {len(recommendation.purchases)}")
    except Exception as e:
        print(f"\nTest error: {e}")


async def lazy_initialization_example():
    """
    Example: Demonstrate lazy initialization of dependencies.

    This shows how the factory creates instances only when needed,
    improving startup performance.
    """
    print("\n" + "=" * 60)
    print("Lazy Initialization Example")
    print("=" * 60)

    # Create factory
    factory = AgentFactory()

    print("\nFactory created (no agents instantiated yet)")

    # Get individual agents (lazy initialization)
    print("\nGetting meal suggester agent...")
    meal_suggester = factory.get_meal_suggester_agent()
    print(f"  Created: {type(meal_suggester).__name__}")

    print("\nGetting meal suggester agent again...")
    meal_suggester2 = factory.get_meal_suggester_agent()
    print(f"  Same instance: {meal_suggester is meal_suggester2}")

    print("\nGetting other agents...")
    ingredient_mapper = factory.get_ingredient_mapper_agent()
    output_formatter = factory.get_output_formatter_agent()
    print(f"  Created: {type(ingredient_mapper).__name__}")
    print(f"  Created: {type(output_formatter).__name__}")

    # Reset factory
    print("\nResetting factory...")
    factory.reset()

    print("\nGetting meal suggester agent after reset...")
    meal_suggester3 = factory.get_meal_suggester_agent()
    print(f"  New instance: {meal_suggester3 is not meal_suggester}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("AgentFactory Usage Examples")
    print("=" * 60)

    # Run examples
    await factory_example()
    await lazy_initialization_example()
    await test_example()

    # Uncomment to run production example (requires valid API keys)
    # await production_example()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

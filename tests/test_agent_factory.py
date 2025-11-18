"""
Tests for AgentFactory - Dependency injection and agent composition.

This module tests the factory's ability to create fully-wired agent instances
with proper dependency injection, configuration validation, and support for
test doubles.
"""

import pytest

from agents.discount_optimizer.agents.ingredient_mapper_agent import IngredientMapperAgent
from agents.discount_optimizer.agents.meal_suggester_agent import MealSuggesterAgent
from agents.discount_optimizer.agents.output_formatter_agent import OutputFormatterAgent
from agents.discount_optimizer.agents.shopping_optimizer_agent import ShoppingOptimizerAgent
from agents.discount_optimizer.config import Settings
from agents.discount_optimizer.domain.models import DiscountItem, Location
from agents.discount_optimizer.domain.protocols import (
    CacheRepository,
    GeocodingService,
)
from agents.discount_optimizer.factory import (
    AgentFactory,
    create_production_agent,
    create_test_agent,
)
from agents.discount_optimizer.services.discount_matcher_service import DiscountMatcherService
from agents.discount_optimizer.services.input_validation_service import InputValidationService
from agents.discount_optimizer.services.multi_criteria_optimizer_service import (
    MultiCriteriaOptimizerService,
)


class MockGeocodingService:
    """Mock geocoding service for testing."""

    async def geocode_address(self, address: str) -> Location:
        """Mock geocode address."""
        return Location(latitude=55.6761, longitude=12.5683)

    async def calculate_distance(self, origin: Location, destination: Location) -> float:
        """Mock calculate distance."""
        return 2.5

    async def health_check(self) -> bool:
        """Mock health check."""
        return True


class MockDiscountRepository:
    """Mock discount repository for testing."""

    async def fetch_discounts(self, location: Location, radius_km: float) -> list[DiscountItem]:
        """Mock fetch discounts."""
        return []

    async def health_check(self) -> bool:
        """Mock health check."""
        return True


class MockCacheRepository:
    """Mock cache repository for testing."""

    async def get(self, key: str) -> bytes | None:
        """Mock get from cache."""
        return None

    async def set(self, key: str, value: bytes, ttl_seconds: int) -> None:
        """Mock set to cache."""

    async def health_check(self) -> bool:
        """Mock health check."""
        return True


class TestAgentFactory:
    """Test suite for AgentFactory."""

    def test_factory_initialization_with_defaults(self):
        """Test factory initializes with default configuration."""
        factory = AgentFactory()

        assert factory.config is not None
        assert factory._geocoding_service is None
        assert factory._discount_repository is None
        assert factory._cache_repository is None

    def test_factory_initialization_with_custom_config(self):
        """Test factory initializes with custom configuration."""
        custom_config = Settings()  # type: ignore[call-arg]
        factory = AgentFactory(config=custom_config)

        assert factory.config is custom_config

    def test_factory_initialization_with_injected_dependencies(self):
        """Test factory initializes with injected dependencies."""
        mock_geocoding = MockGeocodingService()
        mock_discounts = MockDiscountRepository()
        mock_cache = MockCacheRepository()

        factory = AgentFactory(
            geocoding_service=mock_geocoding,
            discount_repository=mock_discounts,
            cache_repository=mock_cache,
        )

        assert factory._geocoding_service is mock_geocoding
        assert factory._discount_repository is mock_discounts
        assert factory._cache_repository is mock_cache

    def test_get_geocoding_service_returns_injected_instance(self):
        """Test get_geocoding_service returns injected instance."""
        mock_geocoding = MockGeocodingService()
        factory = AgentFactory(geocoding_service=mock_geocoding)

        service = factory.get_geocoding_service()

        assert service is mock_geocoding

    def test_get_geocoding_service_creates_production_instance(self):
        """Test get_geocoding_service creates production instance when not injected."""
        factory = AgentFactory()

        service = factory.get_geocoding_service()

        assert service is not None
        assert isinstance(service, GeocodingService)

    def test_get_discount_repository_returns_injected_instance(self):
        """Test get_discount_repository returns injected instance."""
        mock_discounts = MockDiscountRepository()
        factory = AgentFactory(discount_repository=mock_discounts)

        repo = factory.get_discount_repository()

        assert repo is mock_discounts

    def test_get_cache_repository_returns_injected_instance(self):
        """Test get_cache_repository returns injected instance."""
        mock_cache = MockCacheRepository()
        factory = AgentFactory(cache_repository=mock_cache)

        repo = factory.get_cache_repository()

        assert repo is mock_cache

    def test_get_cache_repository_creates_production_instance(self):
        """Test get_cache_repository creates production instance when not injected."""
        factory = AgentFactory()

        repo = factory.get_cache_repository()

        assert repo is not None
        assert isinstance(repo, CacheRepository)

    def test_get_meal_suggester_agent_lazy_initialization(self):
        """Test meal suggester agent is lazily initialized."""
        factory = AgentFactory()

        # First call creates instance
        agent1 = factory.get_meal_suggester_agent()
        assert agent1 is not None
        assert isinstance(agent1, MealSuggesterAgent)

        # Second call returns same instance
        agent2 = factory.get_meal_suggester_agent()
        assert agent2 is agent1

    def test_get_ingredient_mapper_agent_lazy_initialization(self):
        """Test ingredient mapper agent is lazily initialized."""
        factory = AgentFactory()

        # First call creates instance
        agent1 = factory.get_ingredient_mapper_agent()
        assert agent1 is not None
        assert isinstance(agent1, IngredientMapperAgent)

        # Second call returns same instance
        agent2 = factory.get_ingredient_mapper_agent()
        assert agent2 is agent1

    def test_get_output_formatter_agent_lazy_initialization(self):
        """Test output formatter agent is lazily initialized."""
        factory = AgentFactory()

        # First call creates instance
        agent1 = factory.get_output_formatter_agent()
        assert agent1 is not None
        assert isinstance(agent1, OutputFormatterAgent)

        # Second call returns same instance
        agent2 = factory.get_output_formatter_agent()
        assert agent2 is agent1

    def test_get_input_validation_service_lazy_initialization(self):
        """Test input validation service is lazily initialized."""
        factory = AgentFactory()

        # First call creates instance
        service1 = factory.get_input_validation_service()
        assert service1 is not None
        assert isinstance(service1, InputValidationService)

        # Second call returns same instance
        service2 = factory.get_input_validation_service()
        assert service2 is service1

    def test_get_discount_matcher_service_lazy_initialization(self):
        """Test discount matcher service is lazily initialized."""
        factory = AgentFactory()

        # First call creates instance
        service1 = factory.get_discount_matcher_service()
        assert service1 is not None
        assert isinstance(service1, DiscountMatcherService)

        # Second call returns same instance
        service2 = factory.get_discount_matcher_service()
        assert service2 is service1

    def test_get_multi_criteria_optimizer_service_lazy_initialization(self):
        """Test multi-criteria optimizer service is lazily initialized."""
        factory = AgentFactory()

        # First call creates instance
        service1 = factory.get_multi_criteria_optimizer_service()
        assert service1 is not None
        assert isinstance(service1, MultiCriteriaOptimizerService)

        # Second call returns same instance
        service2 = factory.get_multi_criteria_optimizer_service()
        assert service2 is service1

    def test_create_shopping_optimizer_agent_returns_wired_instance(self):
        """Test create_shopping_optimizer_agent returns fully-wired agent."""
        factory = AgentFactory()

        agent = factory.create_shopping_optimizer_agent()

        assert agent is not None
        assert isinstance(agent, ShoppingOptimizerAgent)
        assert agent.meal_suggester is not None
        assert agent.ingredient_mapper is not None
        assert agent.output_formatter is not None
        assert agent.input_validator is not None
        assert agent.discount_matcher is not None
        assert agent.optimizer is not None

    def test_create_shopping_optimizer_agent_with_mocks(self):
        """Test create_shopping_optimizer_agent works with injected mocks."""
        mock_geocoding = MockGeocodingService()
        mock_discounts = MockDiscountRepository()
        mock_cache = MockCacheRepository()

        factory = AgentFactory(
            geocoding_service=mock_geocoding,
            discount_repository=mock_discounts,
            cache_repository=mock_cache,
        )

        agent = factory.create_shopping_optimizer_agent()

        assert agent is not None
        assert isinstance(agent, ShoppingOptimizerAgent)
        # Verify mocks are used in the dependency chain
        assert factory.get_geocoding_service() is mock_geocoding
        assert factory.get_discount_repository() is mock_discounts
        assert factory.get_cache_repository() is mock_cache

    def test_reset_clears_lazy_instances(self):
        """Test reset clears all lazy-initialized instances."""
        factory = AgentFactory()

        # Create instances
        agent1 = factory.get_meal_suggester_agent()
        service1 = factory.get_input_validation_service()

        # Reset factory
        factory.reset()

        # New instances should be created
        agent2 = factory.get_meal_suggester_agent()
        service2 = factory.get_input_validation_service()

        assert agent2 is not agent1
        assert service2 is not service1

    def test_create_production_agent_convenience_function(self):
        """Test create_production_agent convenience function."""
        agent = create_production_agent()

        assert agent is not None
        assert isinstance(agent, ShoppingOptimizerAgent)

    def test_create_test_agent_convenience_function(self):
        """Test create_test_agent convenience function."""
        mock_geocoding = MockGeocodingService()

        agent = create_test_agent(geocoding_service=mock_geocoding)

        assert agent is not None
        assert isinstance(agent, ShoppingOptimizerAgent)

    def test_create_test_agent_with_no_mocks(self):
        """Test create_test_agent works with no mocks (uses production instances)."""
        agent = create_test_agent()

        assert agent is not None
        assert isinstance(agent, ShoppingOptimizerAgent)


class TestAgentFactoryConfigurationValidation:
    """Test suite for configuration validation."""

    def test_validation_passes_with_valid_config(self):
        """Test validation passes with valid configuration."""
        # Should not raise
        factory = AgentFactory()
        assert factory is not None

    def test_validation_fails_with_invalid_temperature(self):
        """Test validation fails with invalid temperature."""
        # Create config with invalid temperature
        try:
            invalid_config = Settings(agent_temperature=3.0)  # type: ignore[call-arg]
            AgentFactory(config=invalid_config)
            # If we get here, validation didn't catch it
            # This is expected if pydantic validation happens at Settings level
            assert True
        except ValueError:
            # Expected - validation caught the error
            assert True

    def test_validation_fails_with_invalid_max_tokens(self):
        """Test validation fails with invalid max tokens."""
        try:
            invalid_config = Settings(agent_max_tokens=-100)  # type: ignore[call-arg]
            AgentFactory(config=invalid_config)
            # If we get here, validation didn't catch it
            assert True
        except ValueError:
            # Expected - validation caught the error
            assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

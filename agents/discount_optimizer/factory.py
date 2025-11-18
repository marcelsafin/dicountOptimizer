"""
Agent Factory - Dependency injection and agent composition.

This module provides a factory for creating fully-wired agent instances with
all dependencies properly injected. It supports different configurations for
testing vs production environments and validates all required configuration
at startup.

The factory follows enterprise-grade patterns:
- Dependency injection for all components
- Configuration validation before instantiation
- Support for test doubles (mocks) via optional parameters
- Clear separation of concerns
- Type-safe construction

Requirements: 3.7, 5.5, 5.7, 9.3
"""

from .agents.ingredient_mapper_agent import IngredientMapperAgent
from .agents.meal_suggester_agent import MealSuggesterAgent
from .agents.output_formatter_agent import OutputFormatterAgent
from .agents.shopping_optimizer_agent import ShoppingOptimizerAgent
from .config import Settings, settings
from .domain.protocols import CacheRepository, DiscountRepository, GeocodingService
from .infrastructure.google_maps_repository import GoogleMapsRepository
from .infrastructure.redis_cache_repository import create_cache_repository
from .infrastructure.salling_repository import SallingDiscountRepository
from .logging import get_logger
from .services.discount_matcher_service import DiscountMatcherService
from .services.input_validation_service import InputValidationService
from .services.multi_criteria_optimizer_service import MultiCriteriaOptimizerService


# Get logger for this module
logger = get_logger(__name__)


class AgentFactory:
    """
    Factory for creating fully-wired agent instances with dependency injection.

    This factory handles the complex task of wiring together all agents, services,
    and repositories with proper dependency injection. It supports:

    - Production configuration: Uses real API clients and services
    - Test configuration: Allows injection of mocks/test doubles
    - Configuration validation: Ensures all required settings are present
    - Lazy initialization: Creates instances only when needed
    - Type safety: All dependencies are type-checked

    The factory follows the Abstract Factory pattern, providing a single
    entry point for creating the complete agent hierarchy.

    Example (Production):
        >>> factory = AgentFactory()
        >>> agent = factory.create_shopping_optimizer_agent()
        >>> result = await agent.run(input_data)

    Example (Testing):
        >>> mock_geocoding = MockGeocodingService()
        >>> mock_discounts = MockDiscountRepository()
        >>> factory = AgentFactory(
        ...     geocoding_service=mock_geocoding, discount_repository=mock_discounts
        ... )
        >>> agent = factory.create_shopping_optimizer_agent()
        >>> # Agent now uses mocks instead of real services

    Requirements: 3.7, 5.5, 5.7, 9.3
    """

    def __init__(
        self,
        config: Settings | None = None,
        geocoding_service: GeocodingService | None = None,
        discount_repository: DiscountRepository | None = None,
        cache_repository: CacheRepository | None = None,
        api_key: str | None = None,
    ):
        """
        Initialize AgentFactory with optional dependency overrides.

        All dependencies are optional - if not provided, the factory will
        create production instances using the configuration. This allows
        for easy testing by injecting mocks while maintaining clean
        production code.

        Args:
            config: Optional Settings instance (defaults to global settings)
            geocoding_service: Optional geocoding service (defaults to GoogleMapsRepository)
            discount_repository: Optional discount repository (defaults to SallingDiscountRepository)
            cache_repository: Optional cache repository (defaults to InMemoryCacheRepository)
            api_key: Optional Google API key override (defaults to config.google_api_key)

        Raises:
            ValueError: If required configuration is missing

        Requirements: 3.7, 5.5, 5.7, 9.3
        """
        # Use provided config or global settings
        self.config = config or settings

        # Validate required configuration
        self._validate_configuration()

        # Store optional dependency overrides
        self._geocoding_service = geocoding_service
        self._discount_repository = discount_repository
        self._cache_repository = cache_repository
        self._api_key = api_key

        # Lazy-initialized instances
        self._meal_suggester: MealSuggesterAgent | None = None
        self._ingredient_mapper: IngredientMapperAgent | None = None
        self._output_formatter: OutputFormatterAgent | None = None
        self._input_validator: InputValidationService | None = None
        self._discount_matcher: DiscountMatcherService | None = None
        self._optimizer: MultiCriteriaOptimizerService | None = None

        logger.info(
            "agent_factory_initialized",
            environment=self.config.environment,
            has_custom_geocoding=geocoding_service is not None,
            has_custom_discount_repo=discount_repository is not None,
            has_custom_cache=cache_repository is not None,
            has_custom_api_key=api_key is not None,
        )

    def _validate_configuration(self) -> None:
        """
        Validate that all required configuration is present.

        This method checks that essential configuration values are set
        before attempting to create any agents. It provides clear error
        messages for missing configuration.

        Raises:
            ValueError: If required configuration is missing

        Requirements: 9.3
        """
        errors: list[str] = []

        # Validate Google API key
        if not self.config.google_api_key:
            errors.append("GOOGLE_API_KEY is required")

        # Validate Salling API key in production
        if self.config.is_production() and not self.config.salling_group_api_key:
            errors.append("SALLING_GROUP_API_KEY is required in production environment")

        # Validate agent model
        if not self.config.agent_model:
            errors.append("AGENT_MODEL is required")

        # Validate numeric ranges
        if self.config.agent_temperature < 0.0 or self.config.agent_temperature > 2.0:
            errors.append(
                f"AGENT_TEMPERATURE must be between 0.0 and 2.0, got {self.config.agent_temperature}"
            )

        if self.config.agent_max_tokens <= 0:
            errors.append(f"AGENT_MAX_TOKENS must be positive, got {self.config.agent_max_tokens}")

        if self.config.cache_ttl_seconds <= 0:
            errors.append(
                f"CACHE_TTL_SECONDS must be positive, got {self.config.cache_ttl_seconds}"
            )

        if self.config.api_timeout_seconds <= 0:
            errors.append(
                f"API_TIMEOUT_SECONDS must be positive, got {self.config.api_timeout_seconds}"
            )

        # Raise if any errors found
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(
                f"  - {e}" for e in errors
            )
            logger.error("configuration_validation_failed", errors=errors)
            raise ValueError(error_message)

        logger.debug("configuration_validated_successfully")

    def get_geocoding_service(self) -> GeocodingService:
        """
        Get or create geocoding service instance.

        Returns the injected geocoding service if provided, otherwise creates
        a new GoogleMapsRepository instance.

        Returns:
            GeocodingService instance

        Requirements: 3.7, 5.5
        """
        if self._geocoding_service is not None:
            logger.debug("using_injected_geocoding_service")
            return self._geocoding_service

        # Create production instance
        api_key = self.config.get_google_maps_key()
        geocoding_service = GoogleMapsRepository(api_key=api_key)

        logger.debug("created_google_maps_repository")
        return geocoding_service

    def get_discount_repository(self) -> DiscountRepository:
        """
        Get or create discount repository instance.

        Returns the injected discount repository if provided, otherwise creates
        a new SallingDiscountRepository instance.

        Returns:
            DiscountRepository instance

        Requirements: 3.7, 5.5
        """
        if self._discount_repository is not None:
            logger.debug("using_injected_discount_repository")
            return self._discount_repository

        # Create production instance
        if self.config.salling_group_api_key:
            api_key = self.config.salling_group_api_key.get_secret_value()
            discount_repository = SallingDiscountRepository(api_key=api_key)
            logger.debug("created_salling_discount_repository")
        else:
            # In development, we might not have Salling API key
            # Return a mock or raise an error
            logger.warning("salling_api_key_not_configured_using_fallback")
            # For now, create with empty key (will fail on actual API calls)
            discount_repository = SallingDiscountRepository(api_key="")

        return discount_repository

    def get_cache_repository(self) -> CacheRepository:
        """
        Get or create cache repository instance.

        Returns the injected cache repository if provided, otherwise creates
        a cache repository based on configuration (memory or redis).

        Returns:
            CacheRepository instance

        Requirements: 3.7, 5.5
        """
        if self._cache_repository is not None:
            logger.debug("using_injected_cache_repository")
            return self._cache_repository

        # Create cache based on configuration
        redis_config = self.config.get_redis_config()
        cache_repository = create_cache_repository(
            cache_type=self.config.cache_type,
            redis_host=redis_config["host"],
            redis_port=redis_config["port"],
            redis_db=redis_config["db"],
            redis_password=redis_config.get("password"),
        )

        logger.debug("created_cache_repository", cache_type=self.config.cache_type)
        return cache_repository

    def get_meal_suggester_agent(self) -> MealSuggesterAgent:
        """
        Get or create MealSuggester agent instance.

        Uses lazy initialization - creates the agent only once and reuses it
        for subsequent calls.

        Returns:
            MealSuggesterAgent instance

        Requirements: 3.7, 5.5
        """
        if self._meal_suggester is None:
            api_key = self._api_key or self.config.google_api_key.get_secret_value()
            self._meal_suggester = MealSuggesterAgent(api_key=api_key)
            logger.debug("created_meal_suggester_agent")

        return self._meal_suggester

    def get_ingredient_mapper_agent(self) -> IngredientMapperAgent:
        """
        Get or create IngredientMapper agent instance.

        Uses lazy initialization - creates the agent only once and reuses it
        for subsequent calls.

        Returns:
            IngredientMapperAgent instance

        Requirements: 3.7, 5.5
        """
        if self._ingredient_mapper is None:
            api_key = self._api_key or self.config.google_api_key.get_secret_value()
            self._ingredient_mapper = IngredientMapperAgent(api_key=api_key)
            logger.debug("created_ingredient_mapper_agent")

        return self._ingredient_mapper

    def get_output_formatter_agent(self) -> OutputFormatterAgent:
        """
        Get or create OutputFormatter agent instance.

        Uses lazy initialization - creates the agent only once and reuses it
        for subsequent calls.

        Returns:
            OutputFormatterAgent instance

        Requirements: 3.7, 5.5
        """
        if self._output_formatter is None:
            api_key = self._api_key or self.config.google_api_key.get_secret_value()
            self._output_formatter = OutputFormatterAgent(api_key=api_key)
            logger.debug("created_output_formatter_agent")

        return self._output_formatter

    def get_input_validation_service(self) -> InputValidationService:
        """
        Get or create InputValidation service instance.

        Uses lazy initialization - creates the service only once and reuses it
        for subsequent calls.

        Returns:
            InputValidationService instance

        Requirements: 3.7, 5.5
        """
        if self._input_validator is None:
            geocoding_service = self.get_geocoding_service()
            self._input_validator = InputValidationService(geocoding_service=geocoding_service)
            logger.debug("created_input_validation_service")

        return self._input_validator

    def get_discount_matcher_service(self) -> DiscountMatcherService:
        """
        Get or create DiscountMatcher service instance.

        Uses lazy initialization - creates the service only once and reuses it
        for subsequent calls.

        Returns:
            DiscountMatcherService instance

        Requirements: 3.7, 5.5
        """
        if self._discount_matcher is None:
            discount_repository = self.get_discount_repository()
            cache_repository = self.get_cache_repository() if self.config.enable_caching else None
            self._discount_matcher = DiscountMatcherService(
                discount_repository=discount_repository, cache_repository=cache_repository
            )
            logger.debug("created_discount_matcher_service")

        return self._discount_matcher

    def get_multi_criteria_optimizer_service(self) -> MultiCriteriaOptimizerService:
        """
        Get or create MultiCriteriaOptimizer service instance.

        Uses lazy initialization - creates the service only once and reuses it
        for subsequent calls.

        Returns:
            MultiCriteriaOptimizerService instance

        Requirements: 3.7, 5.5
        """
        if self._optimizer is None:
            self._optimizer = MultiCriteriaOptimizerService()
            logger.debug("created_multi_criteria_optimizer_service")

        return self._optimizer

    def create_shopping_optimizer_agent(self) -> ShoppingOptimizerAgent:
        """
        Create a fully-wired ShoppingOptimizer agent with all dependencies.

        This is the main factory method that creates the root agent with all
        sub-agents and services properly injected. The agent is ready to use
        immediately after creation.

        The method:
        1. Creates or retrieves all sub-agents
        2. Creates or retrieves all services
        3. Wires them together via dependency injection
        4. Returns the fully-configured root agent

        Returns:
            ShoppingOptimizerAgent instance with all dependencies injected

        Example:
            >>> factory = AgentFactory()
            >>> agent = factory.create_shopping_optimizer_agent()
            >>> input_data = ShoppingOptimizerInput(
            ...     address="Nørrebrogade 20, Copenhagen",
            ...     meal_plan=[],
            ...     timeframe="this week",
            ...     maximize_savings=True,
            ... )
            >>> recommendation = await agent.run(input_data)

        Requirements: 3.7, 5.5, 5.7
        """
        logger.info("creating_shopping_optimizer_agent")

        # Get all sub-agents
        meal_suggester = self.get_meal_suggester_agent()
        ingredient_mapper = self.get_ingredient_mapper_agent()
        output_formatter = self.get_output_formatter_agent()

        # Get all services
        input_validator = self.get_input_validation_service()
        discount_matcher = self.get_discount_matcher_service()
        optimizer = self.get_multi_criteria_optimizer_service()

        # Create root agent with dependency injection
        shopping_optimizer = ShoppingOptimizerAgent(
            meal_suggester=meal_suggester,
            ingredient_mapper=ingredient_mapper,
            output_formatter=output_formatter,
            input_validator=input_validator,
            discount_matcher=discount_matcher,
            optimizer=optimizer,
        )

        logger.info(
            "shopping_optimizer_agent_created",
            environment=self.config.environment,
            caching_enabled=self.config.enable_caching,
            ai_suggestions_enabled=self.config.enable_ai_meal_suggestions,
        )

        return shopping_optimizer

    def reset(self) -> None:
        """
        Reset all lazy-initialized instances.

        This method clears all cached instances, forcing them to be recreated
        on the next access. Useful for testing or when configuration changes.

        Requirements: 5.7
        """
        self._meal_suggester = None
        self._ingredient_mapper = None
        self._output_formatter = None
        self._input_validator = None
        self._discount_matcher = None
        self._optimizer = None

        logger.debug("agent_factory_reset")


# =========================================================================
# Convenience Functions
# =========================================================================


def create_production_agent() -> ShoppingOptimizerAgent:
    """
    Create a production-ready ShoppingOptimizer agent with default configuration.

    This is a convenience function for the most common use case: creating
    a production agent with all real services and repositories.

    Returns:
        ShoppingOptimizerAgent instance configured for production

    Example:
        >>> agent = create_production_agent()
        >>> result = await agent.run(input_data)

    Requirements: 3.7, 5.5, 5.7
    """
    factory = AgentFactory()
    return factory.create_shopping_optimizer_agent()


def create_test_agent(
    geocoding_service: GeocodingService | None = None,
    discount_repository: DiscountRepository | None = None,
    cache_repository: CacheRepository | None = None,
    api_key: str | None = None,
) -> ShoppingOptimizerAgent:
    """
    Create a test ShoppingOptimizer agent with optional mock dependencies.

    This is a convenience function for testing: it allows you to inject
    mock implementations of services while using real implementations for
    the rest.

    Args:
        geocoding_service: Optional mock geocoding service
        discount_repository: Optional mock discount repository
        cache_repository: Optional mock cache repository
        api_key: Optional test API key

    Returns:
        ShoppingOptimizerAgent instance configured for testing

    Example:
        >>> mock_geocoding = MockGeocodingService()
        >>> agent = create_test_agent(geocoding_service=mock_geocoding)
        >>> result = await agent.run(input_data)

    Requirements: 3.7, 5.5, 5.7
    """
    factory = AgentFactory(
        geocoding_service=geocoding_service,
        discount_repository=discount_repository,
        cache_repository=cache_repository,
        api_key=api_key,
    )
    return factory.create_shopping_optimizer_agent()

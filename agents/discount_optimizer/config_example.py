"""
Example usage of the configuration module.

This file demonstrates how to use the Settings class and access configuration
values throughout the application.
"""

from config import get_settings, settings


def example_basic_usage():
    """Basic usage: accessing configuration values."""
    print("=== Basic Usage ===")

    # Access configuration values directly
    print(f"Environment: {settings.environment}")
    print(f"Agent model: {settings.agent_model}")
    print(f"Log level: {settings.log_level}")

    # Access API keys (SecretStr)
    api_key = settings.google_api_key.get_secret_value()
    print(f"API key loaded: {api_key[:10]}...")

    # Check feature flags
    if settings.enable_ai_meal_suggestions:
        print("AI meal suggestions are enabled")

    if settings.enable_caching:
        print(f"Caching enabled with TTL: {settings.cache_ttl_seconds}s")


def example_helper_methods():
    """Using helper methods for common operations."""
    print("\n=== Helper Methods ===")

    # Get Google Maps API key (with fallback)
    maps_key = settings.get_google_maps_key()
    print(f"Google Maps key: {maps_key[:10]}...")

    # Get logging level as Python constant
    import logging

    log_level = settings.get_logging_level()
    print(f"Logging level constant: {log_level} (INFO={logging.INFO})")

    # Check environment
    if settings.is_development():
        print("Running in development mode")
    elif settings.is_production():
        print("Running in production mode")

    # Get agent configuration for ADK
    agent_config = settings.get_agent_config()
    print(f"Agent config: {agent_config}")


def example_dependency_injection():
    """Using settings with dependency injection."""
    print("\n=== Dependency Injection ===")

    # For dependency injection, use get_settings()
    def create_agent(config: type[settings] | None = None):
        config = config or get_settings()
        print(f"Creating agent with model: {config.agent_model}")
        print(f"Temperature: {config.agent_temperature}")
        return "agent_instance"

    agent = create_agent()
    print(f"Agent created: {agent}")


def example_environment_override():
    """Demonstrating environment variable override."""
    print("\n=== Environment Override ===")

    # You can override settings via environment variables
    # For example, in your shell:
    # export LOG_LEVEL=DEBUG
    # export AGENT_TEMPERATURE=0.9

    print(f"Current log level: {settings.log_level}")
    print(f"Current temperature: {settings.agent_temperature}")

    # To reload settings after environment changes:
    # new_settings = reload_settings()


def example_validation():
    """Demonstrating configuration validation."""
    print("\n=== Validation ===")

    from config import Settings
    from pydantic import ValidationError

    # Valid configuration
    try:
        Settings(google_api_key="test-key", agent_temperature=0.8, cache_ttl_seconds=7200)
        print("✓ Valid configuration accepted")
    except ValidationError as e:
        print(f"✗ Validation failed: {e}")

    # Invalid configuration (temperature out of range)
    try:
        Settings(
            google_api_key="test-key",
            agent_temperature=3.0,  # Invalid: > 2.0
        )
        print("✗ Invalid configuration should have been rejected!")
    except ValidationError:
        print("✓ Invalid configuration correctly rejected")


if __name__ == "__main__":
    example_basic_usage()
    example_helper_methods()
    example_dependency_injection()
    example_environment_override()
    example_validation()

    print("\n=== Configuration Summary ===")
    print(f"Environment: {settings.environment}")
    print(f"Debug mode: {settings.debug}")
    print(f"Agent model: {settings.agent_model}")
    print("Feature flags:")
    print(f"  - AI suggestions: {settings.enable_ai_meal_suggestions}")
    print(f"  - Caching: {settings.enable_caching}")
    print(f"  - Metrics: {settings.enable_metrics}")
    print(f"  - Structured logging: {settings.enable_structured_logging}")
    print(f"  - Distributed tracing: {settings.enable_distributed_tracing}")

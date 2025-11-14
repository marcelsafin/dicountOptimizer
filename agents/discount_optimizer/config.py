"""
Configuration management using Pydantic Settings.

This module provides type-safe configuration management with environment variable
validation, secrets handling, and feature flags for gradual rollout.
"""

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal
import logging


class Settings(BaseSettings):
    """
    Application settings with environment variable validation.
    
    All settings can be configured via environment variables with the same name
    (case-insensitive). Sensitive values like API keys use SecretStr to prevent
    accidental logging.
    
    Example:
        >>> settings = Settings()
        >>> settings.google_api_key.get_secret_value()
        'your-api-key'
    """
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',  # Ignore extra environment variables
        validate_default=True,
    )
    
    # =========================================================================
    # API Keys (Secrets)
    # =========================================================================
    
    google_api_key: SecretStr = Field(
        description="Google Gemini API key for AI agent functionality"
    )
    
    salling_group_api_key: SecretStr | None = Field(
        default=None,
        description="Salling Group API key for discount data (optional for testing)"
    )
    
    google_maps_api_key: SecretStr | None = Field(
        default=None,
        description="Google Maps API key for geocoding (optional, falls back to google_api_key)"
    )
    
    # =========================================================================
    # Environment Configuration
    # =========================================================================
    
    environment: Literal['dev', 'staging', 'production'] = Field(
        default='dev',
        description="Deployment environment"
    )
    
    debug: bool = Field(
        default=False,
        description="Enable debug mode with verbose logging"
    )
    
    # =========================================================================
    # Agent Configuration
    # =========================================================================
    
    agent_model: str = Field(
        default='gemini-2.0-flash-exp',
        description="Gemini model name for AI agents"
    )
    
    agent_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for agent responses (0.0 = deterministic, 2.0 = creative)"
    )
    
    agent_max_tokens: int = Field(
        default=2000,
        gt=0,
        le=8192,
        description="Maximum output tokens per agent response"
    )
    
    agent_top_p: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter for agent responses"
    )
    
    agent_top_k: int = Field(
        default=40,
        ge=1,
        le=100,
        description="Top-k sampling parameter for agent responses"
    )
    
    # =========================================================================
    # Performance Configuration
    # =========================================================================
    
    cache_ttl_seconds: int = Field(
        default=3600,
        gt=0,
        description="Time-to-live for cached API responses (seconds)"
    )
    
    api_timeout_seconds: int = Field(
        default=30,
        gt=0,
        le=300,
        description="Timeout for external API calls (seconds)"
    )
    
    max_concurrent_requests: int = Field(
        default=10,
        gt=0,
        le=100,
        description="Maximum concurrent HTTP requests"
    )
    
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed API calls"
    )
    
    retry_min_wait_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Minimum wait time between retries (seconds)"
    )
    
    retry_max_wait_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=300.0,
        description="Maximum wait time between retries (seconds)"
    )
    
    # =========================================================================
    # Feature Flags
    # =========================================================================
    
    enable_ai_meal_suggestions: bool = Field(
        default=True,
        description="Enable AI-powered meal suggestions using Gemini"
    )
    
    enable_caching: bool = Field(
        default=True,
        description="Enable caching of API responses"
    )
    
    enable_metrics: bool = Field(
        default=True,
        description="Enable metrics collection and monitoring"
    )
    
    enable_structured_logging: bool = Field(
        default=True,
        description="Enable structured JSON logging"
    )
    
    enable_distributed_tracing: bool = Field(
        default=False,
        description="Enable distributed tracing with correlation IDs"
    )
    
    enable_async_operations: bool = Field(
        default=True,
        description="Enable async/await for I/O operations"
    )
    
    enable_connection_pooling: bool = Field(
        default=True,
        description="Enable HTTP connection pooling"
    )
    
    # =========================================================================
    # Logging Configuration
    # =========================================================================
    
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = Field(
        default='INFO',
        description="Logging level"
    )
    
    log_format: Literal['json', 'console', 'text'] = Field(
        default='console',
        description="Log output format (json for production, console for development)"
    )
    
    log_file: str | None = Field(
        default=None,
        description="Path to log file (None = stdout only)"
    )
    
    log_max_bytes: int = Field(
        default=10_485_760,  # 10 MB
        gt=0,
        description="Maximum log file size before rotation (bytes)"
    )
    
    log_backup_count: int = Field(
        default=5,
        ge=0,
        description="Number of rotated log files to keep"
    )
    
    # =========================================================================
    # Business Logic Configuration
    # =========================================================================
    
    default_search_radius_km: float = Field(
        default=5.0,
        gt=0.0,
        le=50.0,
        description="Default search radius for discount lookup (kilometers)"
    )
    
    max_stores_per_recommendation: int = Field(
        default=3,
        gt=0,
        le=10,
        description="Maximum number of stores in a shopping recommendation"
    )
    
    min_discount_percent: float = Field(
        default=10.0,
        ge=0.0,
        le=100.0,
        description="Minimum discount percentage to consider"
    )
    
    max_travel_distance_km: float = Field(
        default=20.0,
        gt=0.0,
        le=100.0,
        description="Maximum travel distance for store recommendations (kilometers)"
    )
    
    # =========================================================================
    # Validators
    # =========================================================================
    
    @field_validator('retry_max_wait_seconds')
    @classmethod
    def validate_retry_wait_times(cls, v: float, info) -> float:
        """Ensure max wait time is greater than min wait time."""
        if 'retry_min_wait_seconds' in info.data:
            min_wait = info.data['retry_min_wait_seconds']
            if v <= min_wait:
                raise ValueError(
                    f'retry_max_wait_seconds ({v}) must be greater than '
                    f'retry_min_wait_seconds ({min_wait})'
                )
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid Python logging level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def get_google_maps_key(self) -> str:
        """
        Get Google Maps API key, falling back to main Google API key if not set.
        
        Returns:
            API key as plain string (secret value extracted)
        """
        if self.google_maps_api_key:
            return self.google_maps_api_key.get_secret_value()
        return self.google_api_key.get_secret_value()
    
    def get_logging_level(self) -> int:
        """
        Get Python logging level constant.
        
        Returns:
            Logging level constant (e.g., logging.INFO)
        """
        return getattr(logging, self.log_level)
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == 'dev'
    
    def get_agent_config(self) -> dict:
        """
        Get agent generation configuration as a dictionary.
        
        Returns:
            Dictionary suitable for Google ADK Agent generation_config
        """
        return {
            'temperature': self.agent_temperature,
            'max_output_tokens': self.agent_max_tokens,
            'top_p': self.agent_top_p,
            'top_k': self.agent_top_k,
        }
    
    def validate_required_keys(self) -> None:
        """
        Validate that all required API keys are present.
        
        Raises:
            ValueError: If required API keys are missing
        """
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required")
        
        # Salling API key is optional for testing
        if self.is_production() and not self.salling_group_api_key:
            raise ValueError("SALLING_GROUP_API_KEY is required in production")


# =========================================================================
# Singleton Instance
# =========================================================================

# Global settings instance - loaded once at module import
# This ensures consistent configuration across the application
settings = Settings()

# Validate required keys on startup
try:
    settings.validate_required_keys()
except ValueError as e:
    # In development, we might want to continue with warnings
    if settings.is_production():
        raise
    else:
        import warnings
        warnings.warn(f"Configuration warning: {e}", UserWarning)


# =========================================================================
# Convenience Functions
# =========================================================================

def get_settings() -> Settings:
    """
    Get the global settings instance.
    
    This function is provided for dependency injection and testing purposes.
    In most cases, you can import `settings` directly.
    
    Returns:
        Global Settings instance
    """
    return settings


def reload_settings() -> Settings:
    """
    Reload settings from environment variables.
    
    Useful for testing or when environment variables change at runtime.
    
    Returns:
        New Settings instance
    """
    global settings
    settings = Settings()
    return settings

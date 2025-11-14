# Implementation Plan: Google ADK Modernization

## Overview
Transform the Shopping Optimizer into an enterprise-grade, type-safe system using Google ADK best practices (November 2025). Each task builds incrementally on previous work.

---

## Phase 1: Type System Foundation

- [x] 1. Set up type checking infrastructure
  - Install mypy and configure strict mode in pyproject.toml
  - Install required dependencies: pydantic, pydantic-settings, tenacity, structlog, httpx
  - Update requirements.txt with all new dependencies
  - Create mypy.ini with gradual typing strategy:
    - Global policy: Permissive for legacy code (strict = False)
    - Per-module overrides: Strict only for refactored modules (agents.discount_optimizer.domain.*)
    - Legacy modules: Explicitly ignore_errors = True during migration
  - This allows new code to be fully type-safe while legacy code remains unchanged
  - _Requirements: 1.5, 5.1, 5.4_

- [x] 2. Create core domain models with Pydantic
  - Create agents/discount_optimizer/domain/ directory structure
  - Implement Location model with coordinate validation
  - Implement Timeframe model with date validation
  - Implement OptimizationPreferences model with at-least-one validator
  - Implement DiscountItem model with Decimal prices and field validators
  - Implement Purchase model with type constraints
  - Implement ShoppingRecommendation model
  - _Requirements: 1.1, 1.4, 5.1_

- [x] 3. Define Protocol interfaces for dependency injection
  - Create agents/discount_optimizer/domain/protocols.py
  - Define DiscountRepository protocol with async methods
  - Define GeocodingService protocol with async methods
  - Define CacheRepository protocol with async methods
  - Mark all protocols as @runtime_checkable
  - _Requirements: 1.2, 5.5, 3.7_

- [x] 4. Create exception hierarchy
  - Create agents/discount_optimizer/domain/exceptions.py
  - Define ShoppingOptimizerError base exception
  - Define ValidationError for input validation failures
  - Define APIError for external API failures
  - Define AgentError for agent execution failures
  - _Requirements: 4.3, 4.5_

- [ ] 5. Implement configuration management with Pydantic Settings
  - Create agents/discount_optimizer/config.py
  - Define Settings class with all configuration fields
  - Add environment variable validation
  - Add API key fields with SecretStr
  - Add feature flags for gradual rollout
  - Add logging configuration
  - Create singleton settings instance
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.6_

---

## Phase 2: Infrastructure Layer

- [ ] 6. Implement async Salling API repository
  - Create agents/discount_optimizer/infrastructure/ directory
  - Create salling_repository.py with SallingDiscountRepository class
  - Implement __init__ with httpx.AsyncClient and connection pooling
  - Implement fetch_discounts with @retry decorator and exponential backoff
  - Implement health_check method
  - Implement _parse_discount with Pydantic validation
  - Add context manager support (__aenter__, __aexit__)
  - _Requirements: 2.5, 4.1, 5.6, 8.2, 8.3, 8.5_

- [ ] 7. Implement async Google Maps repository
  - Create google_maps_repository.py with GoogleMapsRepository class
  - Implement geocode_address with @retry decorator
  - Implement calculate_distance using Haversine formula
  - Implement find_nearby_stores method
  - Add connection pooling and timeout configuration
  - Implement health_check method
  - _Requirements: 2.5, 4.1, 8.2, 8.3_

- [ ] 8. Implement caching layer
  - Create cache_repository.py with CacheRepository implementation
  - Use in-memory cache with TTL support (consider using aiocache)
  - Implement async get method
  - Implement async set method with TTL
  - Implement cache key generation utilities
  - Add cache metrics (hit rate, miss rate)
  - _Requirements: 8.1, 10.2_

- [ ] 9. Set up structured logging
  - Configure structlog in a logging.py module
  - Add correlation ID generation for request tracing
  - Configure log formatters (JSON for production, console for dev)
  - Add context processors for automatic field injection
  - Integrate with Python's standard logging
  - _Requirements: 10.1, 10.4_

---

## Phase 3: Agent Layer (Google ADK)

- [ ] 10. Create MealSuggester ADK agent
  - Create agents/discount_optimizer/agents/ directory
  - Create meal_suggester_agent.py
  - Define MealSuggestionInput Pydantic model
  - Define MealSuggestionOutput Pydantic model
  - Implement MealSuggesterAgent class with ADK Agent
  - Implement @tool decorated suggest_meals method
  - Add system instruction for creative meal suggestions
  - Add structured logging for agent execution
  - _Requirements: 2.1, 2.3, 3.1, 3.3, 10.1_

- [ ] 11. Create IngredientMapper ADK agent
  - Create ingredient_mapper_agent.py
  - Define IngredientMappingInput Pydantic model
  - Define IngredientMappingOutput Pydantic model
  - Implement IngredientMapperAgent class with ADK Agent
  - Implement @tool decorated map_ingredients method
  - Implement fuzzy matching logic with type safety
  - Add logging for mapping decisions
  - _Requirements: 2.1, 2.3, 3.1, 3.3_

- [ ] 12. Create DiscountMatcher ADK agent
  - Create discount_matcher_agent.py
  - Define DiscountMatchingInput Pydantic model
  - Define DiscountMatchingOutput Pydantic model
  - Implement DiscountMatcherAgent class
  - Inject DiscountRepository via constructor
  - Implement location and timeframe filtering
  - Add caching for discount data
  - _Requirements: 2.1, 2.3, 3.1, 3.2, 8.1_

- [ ] 13. Create MultiCriteriaOptimizer ADK agent
  - Create multi_criteria_optimizer_agent.py
  - Define OptimizationInput Pydantic model
  - Define OptimizationOutput Pydantic model
  - Implement MultiCriteriaOptimizerAgent class
  - Implement scoring algorithm with type-safe calculations
  - Implement store consolidation logic
  - Add logging for optimization decisions
  - _Requirements: 2.1, 2.3, 3.1, 3.3_

- [ ] 14. Create OutputFormatter ADK agent
  - Create output_formatter_agent.py
  - Define FormattingInput Pydantic model
  - Define FormattingOutput Pydantic model
  - Implement OutputFormatterAgent class
  - Implement tip generation logic
  - Implement motivation message generation
  - Format output with proper structure
  - _Requirements: 2.1, 2.3, 3.1, 3.3_

- [ ] 15. Create InputValidation agent
  - Create input_validation_agent.py
  - Define ValidationInput Pydantic model
  - Define ValidationOutput Pydantic model
  - Implement InputValidationAgent class
  - Use Pydantic validators for all input validation
  - Inject GeocodingService for address validation
  - Return typed ValidationError on failures
  - _Requirements: 1.4, 2.1, 2.3, 4.4_

- [ ] 16. Implement root ShoppingOptimizer agent with composition
  - Create shopping_optimizer_agent.py
  - Define ShoppingOptimizerInput Pydantic model
  - Implement ShoppingOptimizerAgent class
  - Inject all sub-agents via constructor (dependency injection)
  - Implement @tool decorated optimize_shopping method
  - Orchestrate sub-agents in correct order
  - Add correlation IDs for distributed tracing
  - Add comprehensive error handling with typed exceptions
  - _Requirements: 2.2, 3.2, 3.3, 3.4, 10.1, 10.5_

---

## Phase 4: Integration and Testing

- [ ] 17. Create agent factory for dependency injection
  - Create agents/discount_optimizer/factory.py
  - Implement AgentFactory class
  - Implement create_shopping_optimizer_agent factory method
  - Wire all dependencies (repositories, agents, config)
  - Add validation for required configuration
  - Support different configurations for testing vs production
  - _Requirements: 3.7, 5.5, 5.7, 9.3_

- [ ] 18. Update Flask API to use new agent architecture
  - Modify app.py to use AgentFactory
  - Replace optimize_shopping function with agent invocation
  - Add async support to Flask routes (use async def)
  - Add health check endpoint using repository health checks
  - Add proper error handling with typed responses
  - Add request correlation IDs
  - _Requirements: 10.1, 10.3_

- [ ] 19. Migrate existing tests to new architecture
  - Update test files to use Pydantic models
  - Create mock implementations of Protocol interfaces
  - Add pytest fixtures for agent instances
  - Update test assertions to use Pydantic model validation
  - Add async test support with pytest-asyncio
  - _Requirements: 6.1, 6.3, 6.4_

- [ ] 20. Add comprehensive type checking validation
  - Run mypy agents/discount_optimizer/domain/ to validate refactored modules
  - Gradually expand strict checking to new modules as they are refactored
  - Ensure 100% type coverage for all domain and agent modules
  - Add mypy to CI/CD pipeline with per-module configuration
  - Document any necessary type: ignore comments with justification
  - Strategy: Use mypy.ini overrides to enforce strict checking only on refactored code
  - _Requirements: 1.5, 5.4, 6.1_

- [ ] 21. Add integration tests for agent composition
  - Create tests/integration/ directory
  - Test full agent pipeline with mocked repositories
  - Test error propagation through agent layers
  - Test retry logic with simulated failures
  - Test caching behavior
  - Validate all Pydantic models with edge cases
  - _Requirements: 6.4, 6.5_

- [ ] 22. Add observability and monitoring
  - Add metrics collection for agent execution time
  - Add metrics for API call latency and success rate
  - Add metrics for cache hit/miss rate
  - Implement health check aggregation endpoint
  - Add performance profiling hooks
  - Create dashboard configuration (Grafana/Prometheus format)
  - _Requirements: 10.2, 10.3, 10.6_

- [ ] 23. Create documentation and examples
  - Update README.md with new architecture overview
  - Document all Pydantic models with Field descriptions
  - Add docstring examples for all public agent methods
  - Create example usage code for agent composition
  - Document configuration options with examples
  - Add migration guide from old to new architecture
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 24. Performance optimization and validation
  - Profile agent execution with realistic workloads
  - Optimize slow paths identified in profiling
  - Validate async operations are non-blocking
  - Test connection pooling under load
  - Validate cache effectiveness
  - Benchmark against old implementation
  - _Requirements: 8.2, 8.3, 8.4, 8.6_

---

## Notes

- All tasks build incrementally - complete in order
- Each task should pass mypy strict type checking before moving to next
- Use structured logging in all new code
- All external I/O must be async
- All data models must use Pydantic with validation
- All dependencies must be injected via constructors
- Write tests alongside implementation (not marked optional to emphasize quality)

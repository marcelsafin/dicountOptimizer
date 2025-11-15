# Integration Tests

This directory contains integration tests for the Shopping Optimizer agent composition and full pipeline testing.

## Test Coverage

### Agent Pipeline (`test_agent_pipeline.py`)
Integration tests for full agent composition with mocked agents and services:

1. **test_full_pipeline_with_address** - Complete flow with address geocoding
2. **test_full_pipeline_with_coordinates** - Direct coordinate input
3. **test_pipeline_with_optimization_preferences** - Different optimization strategies
4. **test_validation_error_propagates** - Input validation error handling
5. **test_api_error_handled_gracefully** - Graceful fallback when external APIs fail
6. **test_agent_error_in_meal_suggester_uses_fallback** - AI agent failure handling
7. **test_retry_logic_with_repository_level_retries** - Repository-level retry integration
8. **test_caching_reduces_api_calls** - Cache effectiveness verification

**Status**: ✅ All 8 tests passing in ~3 seconds

## Running Tests

Run all integration tests:
```bash
python3 -m pytest tests/integration/ -v
```

Run specific test:
```bash
python3 -m pytest tests/integration/test_agent_pipeline.py::test_full_pipeline_with_address -v
```

## Test Requirements

These tests validate:
- **Requirement 6.4**: Integration tests for all agent interactions
- **Requirement 6.5**: Error propagation and retry logic through agent layers

## Testing Approach

### No Live API Calls
All tests use mocked agents and services - **NO live network calls**:
- All Gemini agents (MealSuggester, IngredientMapper, OutputFormatter) are mocked
- All services (InputValidator, DiscountMatcher, Optimizer) are mocked
- All repositories (Geocoding, Discounts, Cache) are mocked

### Mocking Strategy
Following the pattern from `tests/agents/test_shopping_optimizer_agent.py`:
- Use `unittest.mock.Mock` and `AsyncMock` for all dependencies
- Mock the `run()` method of agents to return predefined outputs
- Mock service methods to return controlled test data
- Inject all mocks via `ShoppingOptimizerAgent` constructor

### Verification
Tests verify:
- Pipeline orchestration (correct order of operations)
- Error propagation (ValidationError, APIError, AgentError)
- Fallback behavior (graceful degradation)
- Type safety (all inputs/outputs use Pydantic models)

## Key Test Scenarios

### Integration Scenarios Covered
1. **Full Pipeline with Address**: Complete flow with geocoding
2. **Full Pipeline with Coordinates**: Direct coordinate input
3. **Optimization Preferences**: maximize_savings vs minimize_stores
4. **Validation Errors**: Invalid input handling
5. **API Failures**: Graceful fallback when external APIs fail
6. **Agent Failures**: Fallback when AI agents fail
7. **Retry Logic**: Repository-level retry integration and fallback
8. **Caching**: Cache effectiveness verification

### Testing Approach
- **Direct Mocking**: All agents and services are mocked directly
- **No Live API Calls**: Execution time < 3 seconds confirms no network calls
- **Fallback Verification**: Tests verify graceful degradation
- **Type Safety**: All mocks return properly typed Pydantic models

## Notes

- Tests use `pytest-asyncio` for async test support
- All tests are isolated and can run in parallel
- Tests follow AAA pattern (Arrange, Act, Assert)
- No external dependencies - all mocked via `unittest.mock`
- Execution time < 3 seconds confirms no live API calls
- No "AFC is enabled" messages in logs confirms proper mocking

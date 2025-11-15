# Integration Tests

This directory contains integration tests for the Shopping Optimizer agent composition and full pipeline testing.

## Test Coverage

### Agent Pipeline (`test_agent_pipeline.py`)
Integration tests for full agent composition with mocked repositories:
- **Full Pipeline with Address**: End-to-end testing with address geocoding
- **Full Pipeline with Coordinates**: Direct coordinate input testing
- **Optimization Preferences**: Different optimization strategies
- **Validation Error Propagation**: Input validation error handling
- **API Error Handling**: Graceful fallback when external APIs fail
- **Transient Failures**: Handling of temporary service failures
- **Caching Behavior**: Cache effectiveness and API call reduction
- **Cache Hit Behavior**: Cached data retrieval without API calls

**Status**: ✅ All 8 tests passing

## Running Tests

Run all integration tests:
```bash
python3 -m pytest tests/integration/ -v
```

Run specific test file:
```bash
python3 -m pytest tests/integration/test_agent_pipeline.py -v
```

Run with coverage:
```bash
python3 -m pytest tests/integration/ --cov=agents.discount_optimizer --cov-report=html
```

## Test Requirements

These tests validate:
- **Requirement 6.4**: Integration tests for all agent interactions
- **Requirement 6.5**: Error propagation and retry logic through agent layers

## Mock Repositories

The tests use mock implementations of:
- `MockGeocodingService`: Mocks Google Maps geocoding
- `MockDiscountRepository`: Mocks Salling Group API with configurable behavior
- `MockCacheRepository`: Mocks in-memory cache with metrics tracking
- `RetryableDiscountRepository`: Simulates transient failures for retry testing

These mocks are injected via `create_test_agent()` from the AgentFactory, ensuring:
- No live API calls during testing
- Type safety through Protocol interfaces
- Configurable failure scenarios
- Metrics tracking for verification

## Key Test Scenarios

### Integration Scenarios Covered
1. **Full Pipeline with Address**: Complete flow with geocoding
2. **Full Pipeline with Coordinates**: Direct coordinate input
3. **Optimization Preferences**: maximize_savings vs minimize_stores
4. **Validation Errors**: Invalid input handling
5. **API Failures**: Graceful fallback when external APIs fail
6. **Transient Failures**: Handling temporary service failures
7. **Caching**: Cache effectiveness and API call reduction
8. **Cache Hits**: Cached data retrieval without API calls

### Testing Approach
- **Factory Pattern**: Uses `create_test_agent()` to inject mocks
- **No Live API Calls**: All external dependencies are mocked
- **Fallback Verification**: Tests verify graceful degradation
- **Metrics Tracking**: Mock repositories track call counts
- **Type Safety**: All mocks implement Protocol interfaces

## Notes

- Tests use `pytest-asyncio` for async test support
- All tests are isolated and can run in parallel
- Mock repositories implement Protocol interfaces for type safety
- Tests follow AAA pattern (Arrange, Act, Assert)
- Uses AgentFactory's `create_test_agent()` for proper dependency injection
- No Gemini API calls - agents use fallback behavior when API key is invalid

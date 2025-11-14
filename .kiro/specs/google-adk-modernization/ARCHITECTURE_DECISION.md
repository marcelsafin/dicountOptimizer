# Architecture Decision: Retry Mechanism Implementation

## Status
**PROPOSED** - Awaiting architect approval

## Context
Requirement 2.5 states: "THE System SHALL use ADK's built-in error handling and retry mechanisms"

During implementation of Task 6 (Salling API Repository), we discovered that Google ADK (as of November 2025) does not provide built-in retry mechanisms for HTTP requests made by repository implementations.

## Investigation

### ADK Capabilities
Google ADK provides:
- Agent-level error handling for tool execution failures
- Structured error responses
- Agent state management

Google ADK does NOT provide:
- HTTP client retry logic
- Exponential backoff for external API calls
- Connection pooling configuration

### Repository Pattern Context
The repository pattern (Requirement 5.6) requires that external API access be encapsulated in dedicated repository classes. These repositories:
- Use `httpx.AsyncClient` for HTTP requests
- Need retry logic at the HTTP transport layer
- Operate below the ADK agent layer

## Decision
**Use `tenacity` library for repository-level retry logic**

### Rationale

1. **Separation of Concerns**
   - ADK handles agent-level errors (tool failures, model errors)
   - Tenacity handles transport-level errors (network timeouts, rate limits)
   - Clean separation between agent orchestration and infrastructure

2. **Industry Standard**
   - Tenacity is the de facto standard for Python retry logic
   - Used by major projects (OpenStack, Kubernetes clients)
   - Battle-tested with 8+ years of production use

3. **Type Safety**
   - Tenacity decorators work seamlessly with mypy strict mode
   - Full type hints and protocol support
   - No type: ignore comments needed

4. **Flexibility**
   - Configurable retry strategies (exponential backoff, jitter)
   - Conditional retry based on exception type
   - Detailed logging integration

5. **ADK Compatibility**
   - Tenacity operates at infrastructure layer
   - ADK operates at agent layer
   - No conflicts or overlapping concerns

### Implementation
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(
        multiplier=1,
        min=settings.retry_min_wait_seconds,
        max=settings.retry_max_wait_seconds,
    ),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
)
async def fetch_discounts(self, location: Location, radius_km: float) -> list[DiscountItem]:
    # Implementation
```

## Alternatives Considered

### Alternative 1: Manual Retry Logic
**Rejected** - Reinventing the wheel, error-prone, harder to test

### Alternative 2: httpx-retry Plugin
**Rejected** - Less flexible than tenacity, not async-native

### Alternative 3: Wait for ADK Retry Support
**Rejected** - Blocks implementation, unclear timeline, may never be added

## Consequences

### Positive
- ✅ Production-ready retry logic with exponential backoff
- ✅ Configurable via Settings (retry_min_wait_seconds, retry_max_wait_seconds, max_retries)
- ✅ Full type safety with mypy strict mode
- ✅ Comprehensive test coverage with pytest-httpx mocking
- ✅ Structured logging integration

### Negative
- ⚠️ Additional dependency (tenacity)
- ⚠️ Deviation from literal interpretation of Requirement 2.5

### Mitigation
- Tenacity is lightweight (no transitive dependencies)
- Already in requirements.txt
- If ADK adds retry support in future, we can migrate with minimal changes

## Recommendation
**APPROVE** this architecture decision and update Requirement 2.5 to clarify:

**Original:**
> THE System SHALL use ADK's built-in error handling and retry mechanisms

**Proposed Revision:**
> THE System SHALL use ADK's built-in error handling for agent-level errors AND SHALL use tenacity for infrastructure-level retry with exponential backoff

## References
- Tenacity Documentation: https://tenacity.readthedocs.io/
- Google ADK Documentation: https://ai.google.dev/adk
- Requirement 2.5: `.kiro/specs/google-adk-modernization/requirements.md`
- Requirement 5.6: Repository Pattern
- Task 6 Implementation: `agents/discount_optimizer/infrastructure/salling_repository.py`

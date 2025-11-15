# Architecture Documentation

Complete architecture documentation for the Shopping Optimizer system using Google ADK.

## Table of Contents

- [Overview](#overview)
- [Architectural Principles](#architectural-principles)
- [Layered Architecture](#layered-architecture)
- [Agent Composition](#agent-composition)
- [Data Flow](#data-flow)
- [Dependency Injection](#dependency-injection)
- [Error Handling Strategy](#error-handling-strategy)
- [Type Safety](#type-safety)
- [Performance Considerations](#performance-considerations)
- [Observability](#observability)

---

## Overview

The Shopping Optimizer is built on a modern, enterprise-grade architecture using **Google ADK (Agent Development Kit)** with comprehensive type safety, dependency injection, and clean separation of concerns.

### Key Characteristics

- **Agent-Oriented**: Uses Google ADK for AI-powered components
- **Type-Safe**: 100% type coverage with Pydantic and mypy strict mode
- **Layered**: Clear separation between presentation, agents, business logic, and infrastructure
- **Testable**: Full dependency injection enables easy testing
- **Async**: Non-blocking I/O throughout the system
- **Observable**: Structured logging with correlation IDs

---

## Architectural Principles

### SOLID Principles

1. **Single Responsibility**: Each agent/service has one clear purpose
2. **Open/Closed**: Extensible through interfaces, closed for modification
3. **Liskov Substitution**: Protocol interfaces enable substitutability
4. **Interface Segregation**: Small, focused interfaces
5. **Dependency Inversion**: Depend on abstractions (Protocols), not concretions

### Design Patterns

- **Repository Pattern**: Abstract external data sources
- **Factory Pattern**: Create complex object graphs
- **Strategy Pattern**: Pluggable optimization strategies
- **Dependency Injection**: Constructor injection throughout
- **Protocol Pattern**: Structural subtyping for interfaces

---

## Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Presentation Layer                          │
│  - Flask API endpoints                                   │
│  - Request/response handling                             │
│  - Web UI (HTML/CSS/JS)                                 │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Agent Layer (Google ADK)                    │
│  - ShoppingOptimizerAgent (root orchestrator)           │
│  - MealSuggesterAgent (AI meal suggestions)             │
│  - IngredientMapperAgent (ingredient mapping)           │
│  - OutputFormatterAgent (output formatting)             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Business Logic Layer                        │
│  - InputValidationService                               │
│  - DiscountMatcherService                               │
│  - MultiCriteriaOptimizerService                        │
│  - Domain models (Pydantic)                             │
│  - Business rules and validation                        │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Infrastructure Layer                        │
│  - SallingDiscountRepository (API client)               │
│  - GoogleMapsRepository (geocoding)                     │
│  - InMemoryCacheRepository (caching)                    │
│  - External API integration                             │
└─────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

#### Presentation Layer
- HTTP request/response handling
- Input parsing and output serialization
- Web UI rendering
- API endpoint definitions

**Dependencies**: Agent Layer

#### Agent Layer
- AI-powered decision making (Gemini)
- Agent orchestration and composition
- Tool function definitions
- Agent-specific error handling

**Dependencies**: Business Logic Layer, Infrastructure Layer (via DI)

#### Business Logic Layer
- Core business rules
- Data validation
- Optimization algorithms
- Domain model definitions

**Dependencies**: None (pure business logic)

#### Infrastructure Layer
- External API communication
- Data persistence (caching)
- Network I/O
- Third-party service integration

**Dependencies**: None (implements Protocols)

---

## Agent Composition

### Root Agent: ShoppingOptimizerAgent

The root agent orchestrates all sub-agents and services:

```
ShoppingOptimizerAgent
├── InputValidationService
│   └── GeocodingService (GoogleMapsRepository)
├── DiscountMatcherService
│   ├── DiscountRepository (SallingDiscountRepository)
│   └── CacheRepository (InMemoryCacheRepository)
├── MealSuggesterAgent
│   └── Gemini API (via Google ADK)
├── IngredientMapperAgent
│   └── Gemini API (via Google ADK)
├── MultiCriteriaOptimizerService
│   └── Pure business logic
└── OutputFormatterAgent
    └── Gemini API (via Google ADK)
```

### Agent Characteristics

Each agent:
- **Single Responsibility**: Performs one specific task
- **Typed I/O**: Uses Pydantic models for input/output
- **Error Handling**: Implements retry logic and fallbacks
- **Logging**: Structured logging with context
- **Testable**: Can be tested independently with mocks

### Sub-Agent Details

#### MealSuggesterAgent
- **Purpose**: Generate creative meal suggestions
- **Input**: Available products, preferences, constraints
- **Output**: List of meal names with reasoning
- **AI Model**: Gemini 2.0 Flash
- **Fallback**: Rule-based suggestions if AI fails

#### IngredientMapperAgent
- **Purpose**: Map meals to available products
- **Input**: Meal names, available products
- **Output**: Ingredient-to-product mappings with confidence scores
- **AI Model**: Gemini 2.0 Flash
- **Fallback**: Fuzzy string matching

#### OutputFormatterAgent
- **Purpose**: Format recommendations with tips and motivation
- **Input**: Purchases, savings, stores
- **Output**: Formatted recommendation with tips
- **AI Model**: Gemini 2.0 Flash
- **Fallback**: Template-based formatting

---

## Data Flow

### Complete Request Flow

```
1. User Input
   ↓
2. Flask API Endpoint
   ↓
3. ShoppingOptimizerAgent.run()
   ↓
4. InputValidationService
   ├── Validate coordinates/address
   ├── Parse timeframe
   └── Validate preferences
   ↓
5. DiscountMatcherService
   ├── Check cache
   ├── Fetch from Salling API (if cache miss)
   ├── Filter by distance
   ├── Filter by discount %
   └── Sort by relevance
   ↓
6. MealSuggesterAgent (if no meal plan provided)
   ├── Analyze available products
   ├── Consider expiration dates
   ├── Generate meal suggestions (Gemini)
   └── Return meal list
   ↓
7. IngredientMapperAgent
   ├── For each meal:
   │   ├── Extract ingredients
   │   ├── Match to available products
   │   └── Calculate confidence scores
   └── Return mappings
   ↓
8. MultiCriteriaOptimizerService
   ├── Score each product:
   │   ├── Discount percentage
   │   ├── Travel distance
   │   ├── Store consolidation
   │   ├── Expiration urgency
   │   └── Organic preference
   ├── Select optimal purchases
   └── Group by store
   ↓
9. OutputFormatterAgent
   ├── Generate shopping tips
   ├── Create motivation message
   ├── Format store summary
   └── Return formatted recommendation
   ↓
10. Flask API Response
    ↓
11. User Display
```

### Data Transformations

```
User Input (dict/form)
  → ShoppingOptimizerInput (Pydantic)
    → ValidationOutput (Pydantic)
      → DiscountMatchingOutput (Pydantic)
        → MealSuggestionOutput (Pydantic)
          → IngredientMappingOutput (Pydantic)
            → OptimizationOutput (Pydantic)
              → FormattingOutput (Pydantic)
                → ShoppingRecommendation (Pydantic)
                  → JSON Response
```

Every transformation is type-safe and validated.

---

## Dependency Injection

### Factory Pattern

The `AgentFactory` creates fully-wired agent instances:

```python
# Production usage
factory = AgentFactory()
agent = factory.create_shopping_optimizer_agent()

# Testing with mocks
factory = AgentFactory(
    geocoding_service=mock_geocoding,
    discount_repository=mock_repository,
    cache_repository=mock_cache
)
agent = factory.create_shopping_optimizer_agent()
```

### Dependency Graph

```
AgentFactory
├── Creates: ShoppingOptimizerAgent
│   ├── Injects: MealSuggesterAgent
│   ├── Injects: IngredientMapperAgent
│   ├── Injects: OutputFormatterAgent
│   ├── Injects: InputValidationService
│   │   └── Injects: GeocodingService
│   ├── Injects: DiscountMatcherService
│   │   ├── Injects: DiscountRepository
│   │   └── Injects: CacheRepository
│   └── Injects: MultiCriteriaOptimizerService
```

### Protocol Interfaces

All dependencies use Protocol interfaces for flexibility:

```python
@runtime_checkable
class DiscountRepository(Protocol):
    async def fetch_discounts(
        self, 
        location: Location, 
        radius_km: float
    ) -> list[DiscountItem]: ...
    
    async def health_check(self) -> bool: ...
```

This enables:
- **Testing**: Inject mocks that implement the Protocol
- **Flexibility**: Swap implementations without changing code
- **Type Safety**: mypy validates Protocol compliance

---

## Error Handling Strategy

### Exception Hierarchy

```
ShoppingOptimizerError (base)
├── ValidationError (input validation)
├── APIError (external API failures)
└── AgentError (agent execution failures)
```

### Error Handling Layers

1. **Infrastructure Layer**: Retry with exponential backoff
2. **Agent Layer**: Graceful fallbacks to rule-based alternatives
3. **Service Layer**: Validate inputs, return typed errors
4. **Presentation Layer**: Convert to HTTP status codes

### Retry Strategy

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.HTTPError)
)
async def fetch_with_retry(...):
    ...
```

### Fallback Strategy

```python
try:
    # Try AI-powered suggestion
    result = await meal_suggester.run(input_data)
except AgentError:
    # Fall back to rule-based suggestion
    result = generate_fallback_meals(input_data)
```

---

## Type Safety

### Type Coverage

- **Domain Layer**: 100% (strict mode)
- **Agent Layer**: 100% (strict mode)
- **Infrastructure Layer**: 100% (strict mode)
- **Services Layer**: 100% (strict mode)
- **Legacy Code**: Gradual migration (permissive mode)

### Pydantic Validation

All data models use Pydantic for:
- **Runtime validation**: Catch errors at boundaries
- **Type hints**: Enable static type checking
- **Serialization**: JSON encoding/decoding
- **Documentation**: Auto-generated schemas

Example:
```python
class DiscountItem(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    original_price: Annotated[Decimal, Field(gt=0, decimal_places=2)]
    discount_price: Annotated[Decimal, Field(gt=0, decimal_places=2)]
    
    @field_validator('discount_price')
    @classmethod
    def discount_less_than_original(cls, v, info):
        if v >= info.data['original_price']:
            raise ValueError('discount_price must be less than original_price')
        return v
```

### mypy Configuration

```ini
[mypy]
python_version = 3.11
strict = False  # Global default

# Strict checking for refactored modules
[mypy-agents.discount_optimizer.domain.*]
strict = True

[mypy-agents.discount_optimizer.agents.*]
strict = True
```

---

## Performance Considerations

### Async/Await

All I/O operations use async/await:
- **Non-blocking**: Multiple requests can be processed concurrently
- **Efficient**: Better resource utilization
- **Scalable**: Handles more concurrent users

### Connection Pooling

HTTP clients use connection pooling:
```python
httpx.AsyncClient(
    timeout=30,
    limits=httpx.Limits(
        max_connections=10,
        max_keepalive_connections=5
    )
)
```

### Caching Strategy

- **TTL-based**: Configurable time-to-live
- **In-memory**: Fast access
- **Automatic cleanup**: Expired entries removed
- **Metrics**: Track hit/miss rates

### Optimization Techniques

1. **Lazy Loading**: Create agents only when needed
2. **Parallel Execution**: Run independent agents concurrently
3. **Early Validation**: Fail fast on invalid input
4. **Streaming**: Use ADK streaming for real-time feedback
5. **Batch Processing**: Group similar operations

---

## Observability

### Structured Logging

All logs use structured format with context:

```python
logger.info(
    "shopping_optimization_started",
    correlation_id=correlation_id,
    has_meal_plan=bool(meal_plan),
    timeframe=timeframe,
    maximize_savings=maximize_savings
)
```

### Correlation IDs

Every request gets a unique correlation ID:
- **Tracing**: Follow request through all layers
- **Debugging**: Find all logs for a specific request
- **Monitoring**: Track request latency

### Metrics

Key metrics collected:
- Agent execution time
- API call latency
- Cache hit/miss rate
- Error rate by type
- Request throughput

### Health Checks

Each repository implements health checks:
```python
async def health_check() -> bool:
    try:
        response = await self._client.get("/health")
        return response.status_code == 200
    except:
        return False
```

Aggregated at application level:
```python
{
    "salling_api": True,
    "google_maps": True,
    "cache": True,
    "overall": True
}
```

---

## Deployment Considerations

### Environment Configuration

Three environments supported:
- **Development**: Permissive settings, verbose logging
- **Staging**: Production-like, with test data
- **Production**: Strict settings, JSON logging

### Scaling Strategy

- **Horizontal**: Multiple Flask instances behind load balancer
- **Vertical**: Increase connection pool sizes
- **Caching**: Reduce API calls with longer TTL
- **Rate Limiting**: Protect external APIs

### Monitoring

Recommended monitoring:
- **Application**: Prometheus + Grafana
- **Logs**: ELK Stack or CloudWatch
- **Tracing**: Jaeger or X-Ray
- **Alerts**: PagerDuty or Opsgenie

---

## Future Enhancements

### Potential Improvements

1. **Database**: Replace in-memory cache with Redis
2. **Message Queue**: Add async task processing with Celery
3. **GraphQL**: Add GraphQL API alongside REST
4. **WebSockets**: Real-time updates for long-running optimizations
5. **Multi-tenancy**: Support multiple users with isolation
6. **A/B Testing**: Test different optimization strategies
7. **Machine Learning**: Learn from user preferences over time
8. **Mobile App**: Native iOS/Android apps

### Extensibility Points

- **New Agents**: Add specialized agents for new features
- **New Repositories**: Support additional data sources
- **New Optimization Strategies**: Plug in different algorithms
- **New Output Formats**: Support PDF, email, SMS, etc.

---

## References

- [Google ADK Documentation](https://ai.google.dev/gemini-api/docs/adk)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [Dependency Injection](https://en.wikipedia.org/wiki/Dependency_injection)

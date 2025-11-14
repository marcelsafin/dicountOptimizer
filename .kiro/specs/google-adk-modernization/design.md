# Design Document: Google ADK Modernization

## Overview

This design transforms the Shopping Optimizer from a procedural pipeline into a modern, type-safe, agent-oriented architecture using Google ADK (November 2025 best practices). The system will demonstrate enterprise-grade code quality with maximum type safety, SOLID principles, and clean architecture patterns.

### Current State Analysis

**Problems:**
- Google ADK is barely used (only a `root_agent` definition that's never invoked)
- MealSuggester uses direct `google-genai` API calls instead of ADK agents
- No type safety: missing Pydantic models, Protocol classes, TypedDict
- Procedural pipeline in `optimize_shopping()` function (300+ lines)
- No dependency injection or testability
- Mixed concerns: business logic, API calls, and formatting in one place
- No async/await despite I/O-heavy operations

**Goals:**
- Transform each component into a proper ADK agent
- Achieve 100% type coverage with mypy strict mode
- Implement layered architecture with clear separation of concerns
- Use Pydantic for all data validation
- Apply SOLID principles and design patterns
- Enable async operations for performance

## Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Presentation Layer                          │
│  (Flask API, CLI, Agent Orchestration)                  │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Agent Layer (Google ADK)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ MealSuggester│  │IngredientMap │  │OutputFormatter│ │
│  │    Agent     │  │    Agent     │  │    Agent      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │DiscountMatch │  │MultiCriteria │                    │
│  │    Agent     │  │Optimizer Agent│                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Business Logic Layer                        │
│  (Domain Models, Validation, Scoring Algorithms)        │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Infrastructure Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Salling API  │  │ Google Maps  │  │   Cache      │ │
│  │  Repository  │  │  Repository  │  │  Repository  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Agent Composition Pattern

The root `ShoppingOptimizerAgent` composes specialized sub-agents:

```python
ShoppingOptimizerAgent
├── InputValidationAgent (validates user input)
├── DiscountMatcherAgent (fetches and filters discounts)
├── MealSuggesterAgent (AI meal suggestions)
├── IngredientMapperAgent (maps meals to ingredients)
├── MultiCriteriaOptimizerAgent (optimizes purchases)
└── OutputFormatterAgent (formats recommendations)
```

Each agent:
- Has a single responsibility
- Uses typed tool functions
- Validates inputs/outputs with Pydantic
- Can be tested independently
- Implements retry and error handling

## Components and Interfaces

### 1. Type System Foundation

#### Core Domain Models (Pydantic)

```python
# agents/discount_optimizer/domain/models.py

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import date, datetime
from typing import Annotated
from decimal import Decimal

class Location(BaseModel):
    """Geographic location with validated coordinates."""
    model_config = ConfigDict(frozen=True)  # Immutable
    
    latitude: Annotated[float, Field(ge=-90, le=90, description="Latitude in degrees")]
    longitude: Annotated[float, Field(ge=-180, le=180, description="Longitude in degrees")]

class Timeframe(BaseModel):
    """Shopping timeframe with validation."""
    model_config = ConfigDict(frozen=True)
    
    start_date: date = Field(description="Start date of shopping period")
    end_date: date = Field(description="End date of shopping period")
    
    @field_validator('end_date')
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v

class OptimizationPreferences(BaseModel):
    """User preferences for optimization."""
    model_config = ConfigDict(frozen=True)
    
    maximize_savings: bool = Field(default=True)
    minimize_stores: bool = Field(default=False)
    prefer_organic: bool = Field(default=False)
    
    @field_validator('*')
    @classmethod
    def at_least_one_preference(cls, v, info) -> bool:
        # Validated at model level
        return v

class DiscountItem(BaseModel):
    """Discounted product with full type safety."""
    product_name: str = Field(min_length=1, max_length=200)
    store_name: str = Field(min_length=1, max_length=100)
    store_location: Location
    original_price: Annotated[Decimal, Field(gt=0, decimal_places=2)]
    discount_price: Annotated[Decimal, Field(gt=0, decimal_places=2)]
    discount_percent: Annotated[float, Field(ge=0, le=100)]
    expiration_date: date
    is_organic: bool
    store_address: str = Field(default="")
    travel_distance_km: Annotated[float, Field(ge=0)] = 0.0
    travel_time_minutes: Annotated[float, Field(ge=0)] = 0.0
    
    @field_validator('discount_price')
    @classmethod
    def discount_less_than_original(cls, v: Decimal, info) -> Decimal:
        if 'original_price' in info.data and v >= info.data['original_price']:
            raise ValueError('discount_price must be less than original_price')
        return v

class Purchase(BaseModel):
    """Recommended purchase with meal association."""
    product_name: str
    store_name: str
    purchase_day: date
    price: Annotated[Decimal, Field(gt=0, decimal_places=2)]
    savings: Annotated[Decimal, Field(ge=0, decimal_places=2)]
    meal_association: str

class ShoppingRecommendation(BaseModel):
    """Complete shopping recommendation output."""
    purchases: list[Purchase]
    total_savings: Annotated[Decimal, Field(ge=0, decimal_places=2)]
    time_savings: Annotated[float, Field(ge=0)]
    tips: list[str]
    motivation_message: str
    stores: list[dict]  # Will be typed with StoreInfo model
```

#### Protocol Interfaces

```python
# agents/discount_optimizer/domain/protocols.py

from typing import Protocol, runtime_checkable
from .models import Location, DiscountItem, Timeframe

@runtime_checkable
class DiscountRepository(Protocol):
    """Protocol for discount data sources."""
    
    async def fetch_discounts(
        self, 
        location: Location, 
        radius_km: float
    ) -> list[DiscountItem]:
        """Fetch discounts near location."""
        ...
    
    async def health_check(self) -> bool:
        """Check if repository is healthy."""
        ...

@runtime_checkable
class GeocodingService(Protocol):
    """Protocol for geocoding services."""
    
    async def geocode_address(self, address: str) -> Location:
        """Convert address to coordinates."""
        ...
    
    async def calculate_distance(
        self, 
        origin: Location, 
        destination: Location
    ) -> float:
        """Calculate distance in kilometers."""
        ...

@runtime_checkable
class CacheRepository(Protocol):
    """Protocol for caching layer."""
    
    async def get(self, key: str) -> bytes | None:
        """Get cached value."""
        ...
    
    async def set(self, key: str, value: bytes, ttl_seconds: int) -> None:
        """Set cached value with TTL."""
        ...
```

### 2. Configuration Management

```python
# agents/discount_optimizer/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Literal

class Settings(BaseSettings):
    """Application settings with environment variable validation."""
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    # API Keys
    google_api_key: SecretStr = Field(description="Google Gemini API key")
    salling_api_key: SecretStr | None = Field(default=None, description="Salling Group API key")
    
    # Environment
    environment: Literal['dev', 'staging', 'production'] = Field(default='dev')
    
    # Agent Configuration
    agent_model: str = Field(default='gemini-2.5-flash', description="Gemini model name")
    agent_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    agent_max_tokens: int = Field(default=2000, gt=0)
    
    # Performance
    cache_ttl_seconds: int = Field(default=3600, gt=0)
    api_timeout_seconds: int = Field(default=30, gt=0)
    max_concurrent_requests: int = Field(default=10, gt=0)
    
    # Feature Flags
    enable_ai_meal_suggestions: bool = Field(default=True)
    enable_caching: bool = Field(default=True)
    enable_metrics: bool = Field(default=True)
    
    # Logging
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = Field(default='INFO')
    structured_logging: bool = Field(default=True)

# Singleton instance
settings = Settings()
```

### 3. Infrastructure Layer

#### Repository Pattern for External APIs

```python
# agents/discount_optimizer/infrastructure/salling_repository.py

from typing import Protocol
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from ..domain.models import Location, DiscountItem
from ..domain.protocols import DiscountRepository
from ..config import settings
import structlog

logger = structlog.get_logger()

class SallingDiscountRepository:
    """Repository for Salling Group API with connection pooling."""
    
    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None
    ):
        self.api_key = api_key
        self._client = client or httpx.AsyncClient(
            timeout=settings.api_timeout_seconds,
            limits=httpx.Limits(
                max_connections=settings.max_concurrent_requests,
                max_keepalive_connections=5
            )
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        before_sleep=lambda retry_state: logger.warning(
            "retrying_api_call",
            attempt=retry_state.attempt_number,
            wait_seconds=retry_state.next_action.sleep
        )
    )
    async def fetch_discounts(
        self, 
        location: Location, 
        radius_km: float
    ) -> list[DiscountItem]:
        """Fetch discounts from Salling API with automatic retry logic."""
        response = await self._client.get(
            "https://api.sallinggroup.com/v2/offers",
            headers={"Authorization": f"Bearer {self.api_key}"},
            params={
                "latitude": location.latitude,
                "longitude": location.longitude,
                "radius": radius_km * 1000  # Convert to meters
            }
        )
        response.raise_for_status()
        
        data = response.json()
        return [self._parse_discount(item) for item in data]
    
    async def health_check(self) -> bool:
        """Check API health."""
        try:
            response = await self._client.get(
                "https://api.sallinggroup.com/v2/health",
                timeout=5.0
            )
            return response.status_code == 200
        except:
            return False
    
    def _parse_discount(self, data: dict) -> DiscountItem:
        """Parse API response into DiscountItem model."""
        # Implementation with Pydantic validation
        ...
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self._client.aclose()
```

### 4. Agent Layer (Google ADK)

#### MealSuggester Agent

```python
# agents/discount_optimizer/agents/meal_suggester_agent.py

from google.genai.adk import Agent, tool
from pydantic import BaseModel, Field
from ..domain.models import DiscountItem
from ..config import settings
import structlog

logger = structlog.get_logger()

class MealSuggestionInput(BaseModel):
    """Input for meal suggestion tool."""
    available_products: list[str] = Field(description="List of available product names")
    user_preferences: str = Field(default="", description="User dietary preferences")
    num_meals: int = Field(default=3, ge=1, le=10)
    meal_types: list[str] = Field(default_factory=lambda: ['breakfast', 'lunch', 'dinner'])
    excluded_ingredients: list[str] = Field(default_factory=list)

class MealSuggestionOutput(BaseModel):
    """Output from meal suggestion tool."""
    suggested_meals: list[str] = Field(description="List of suggested meal names")
    reasoning: str = Field(description="Explanation of suggestions")

class MealSuggesterAgent:
    """ADK agent for AI-powered meal suggestions."""
    
    def __init__(self):
        self.agent = Agent(
            model=f'models/{settings.agent_model}',
            name='meal_suggester',
            description="Suggests creative meals based on available discounted products",
            instruction=self._get_system_instruction(),
            tools=[self.suggest_meals],
            generation_config={
                'temperature': settings.agent_temperature,
                'max_output_tokens': settings.agent_max_tokens,
            }
        )
    
    @tool
    async def suggest_meals(self, input_data: MealSuggestionInput) -> MealSuggestionOutput:
        """
        Suggest meals based on available products.
        
        This tool uses Gemini to generate creative meal suggestions that:
        - Utilize available discounted products
        - Respect dietary preferences and restrictions
        - Prioritize products expiring soon
        - Offer diverse meal types
        """
        logger.info(
            "suggesting_meals",
            num_products=len(input_data.available_products),
            preferences=input_data.user_preferences
        )
        
        # Agent will handle the LLM call internally
        # We just define the tool interface
        ...
    
    def _get_system_instruction(self) -> str:
        """Get system instruction for the agent."""
        return """You are a creative chef helping reduce food waste by suggesting meals.

Your goals:
1. Suggest diverse, practical meals using available discounted products
2. Prioritize products expiring soon to reduce waste
3. Respect dietary preferences and restrictions
4. Be creative with flavor combinations and cuisines
5. Ensure meals are realistic and achievable

Output format: Return meal names and brief reasoning."""
    
    async def run(self, input_data: MealSuggestionInput) -> MealSuggestionOutput:
        """Run the agent with input data."""
        response = await self.agent.run(input_data.model_dump())
        return MealSuggestionOutput.model_validate(response)
```

#### Root Shopping Optimizer Agent

```python
# agents/discount_optimizer/agents/shopping_optimizer_agent.py

from google.genai.adk import Agent, tool
from pydantic import BaseModel
from ..domain.models import Location, ShoppingRecommendation
from ..config import settings
from .meal_suggester_agent import MealSuggesterAgent
from .ingredient_mapper_agent import IngredientMapperAgent
# ... other agents
import structlog

logger = structlog.get_logger()

class ShoppingOptimizerInput(BaseModel):
    """Input for shopping optimization."""
    latitude: float
    longitude: float
    meal_plan: list[str]
    timeframe: str = "this week"
    maximize_savings: bool = True
    minimize_stores: bool = False
    prefer_organic: bool = False

class ShoppingOptimizerAgent:
    """Root agent that orchestrates the shopping optimization pipeline."""
    
    def __init__(
        self,
        meal_suggester: MealSuggesterAgent,
        ingredient_mapper: IngredientMapperAgent,
        # ... inject other agents
    ):
        self.meal_suggester = meal_suggester
        self.ingredient_mapper = ingredient_mapper
        # ... other agents
        
        self.agent = Agent(
            model=f'models/{settings.agent_model}',
            name='shopping_optimizer',
            description="Optimizes grocery shopping based on discounts and preferences",
            instruction=self._get_system_instruction(),
            tools=[self.optimize_shopping],
        )
    
    @tool
    async def optimize_shopping(
        self, 
        input_data: ShoppingOptimizerInput
    ) -> ShoppingRecommendation:
        """
        Optimize shopping plan based on user input.
        
        Pipeline:
        1. Validate input
        2. Fetch discounts
        3. Suggest meals (if needed)
        4. Map ingredients
        5. Optimize purchases
        6. Format output
        """
        logger.info("optimizing_shopping", location=(input_data.latitude, input_data.longitude))
        
        # Orchestrate sub-agents
        # Each step is type-safe and validated
        ...
    
    async def run(self, input_data: ShoppingOptimizerInput) -> ShoppingRecommendation:
        """Run the optimization pipeline."""
        response = await self.agent.run(input_data.model_dump())
        return ShoppingRecommendation.model_validate(response)
```

## Data Models

All data models use Pydantic BaseModel with:
- Strict type validation
- Field constraints (min/max, regex, etc.)
- Custom validators
- Immutability where appropriate (frozen=True)
- JSON schema generation
- Serialization/deserialization

See "Components and Interfaces" section for detailed model definitions.

## Error Handling

### Error Hierarchy

```python
# agents/discount_optimizer/domain/exceptions.py

class ShoppingOptimizerError(Exception):
    """Base exception for all shopping optimizer errors."""
    pass

class ValidationError(ShoppingOptimizerError):
    """Input validation failed."""
    pass

class APIError(ShoppingOptimizerError):
    """External API call failed."""
    pass

class AgentError(ShoppingOptimizerError):
    """Agent execution failed."""
    pass
```

### Retry Strategy

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.HTTPError)
)
async def fetch_with_retry(...):
    ...
```

## Testing Strategy

### Unit Tests
- Test each agent independently with mocked dependencies
- Validate Pydantic models with edge cases
- Test scoring algorithms with known inputs
- Verify Protocol implementations

### Integration Tests
- Test agent composition
- Test with real API responses (recorded)
- Validate end-to-end type safety

### Type Checking
```bash
mypy --strict agents/
```

### Test Structure
```python
# tests/test_meal_suggester_agent.py

import pytest
from agents.discount_optimizer.agents.meal_suggester_agent import (
    MealSuggesterAgent,
    MealSuggestionInput,
    MealSuggestionOutput
)

@pytest.fixture
def meal_suggester() -> MealSuggesterAgent:
    return MealSuggesterAgent()

@pytest.mark.asyncio
async def test_suggest_meals_with_valid_input(meal_suggester):
    input_data = MealSuggestionInput(
        available_products=["tortillas", "hakket oksekød", "ost"],
        num_meals=2
    )
    
    output = await meal_suggester.run(input_data)
    
    assert isinstance(output, MealSuggestionOutput)
    assert len(output.suggested_meals) == 2
    assert all(isinstance(meal, str) for meal in output.suggested_meals)
```

## Migration Strategy

### Phase 1: Type System Foundation
1. Create Pydantic models for all data structures
2. Define Protocol interfaces
3. Set up configuration management with Pydantic Settings
4. Enable mypy strict mode

### Phase 2: Infrastructure Layer
1. Implement repository pattern for APIs
2. Add async/await support
3. Implement caching layer
4. Add structured logging

### Phase 3: Agent Layer
1. Convert MealSuggester to ADK agent
2. Convert IngredientMapper to ADK agent
3. Convert other components to agents
4. Implement root agent with composition

### Phase 4: Testing and Validation
1. Add comprehensive unit tests
2. Add integration tests
3. Validate type coverage
4. Performance testing

## Performance Considerations

- **Async I/O**: All external calls use async/await
- **Connection Pooling**: Reuse HTTP connections
- **Caching**: Cache API responses with TTL
- **Lazy Loading**: Load agents on-demand
- **Parallel Execution**: Run independent agents concurrently

## Observability

### Structured Logging
```python
import structlog

logger = structlog.get_logger()
logger.info(
    "agent_execution",
    agent_name="meal_suggester",
    duration_ms=123,
    success=True
)
```

### Metrics
- Agent execution time
- API call latency
- Cache hit rate
- Error rate by type

### Health Checks
```python
async def health_check() -> dict:
    return {
        "salling_api": await salling_repo.health_check(),
        "google_maps": await maps_repo.health_check(),
        "cache": await cache_repo.health_check(),
    }
```

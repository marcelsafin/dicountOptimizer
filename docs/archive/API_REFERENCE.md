# API Reference

Complete API reference for the Shopping Optimizer system with all Pydantic models, agents, services, and repositories.

## Table of Contents

- [Domain Models](#domain-models)
- [Agent Input/Output Models](#agent-inputoutput-models)
- [Agents](#agents)
- [Services](#services)
- [Repositories](#repositories)
- [Configuration](#configuration)
- [Exceptions](#exceptions)

---

## Domain Models

### Location

Geographic location with validated coordinates.

```python
from agents.discount_optimizer.domain.models import Location

location = Location(
    latitude=55.6761,  # -90 to 90
    longitude=12.5683  # -180 to 180
)
```

**Fields:**
- `latitude` (float): Latitude in degrees, must be between -90 and 90
- `longitude` (float): Longitude in degrees, must be between -180 and 180

**Configuration:**
- Immutable (frozen=True)

**Example:**
```python
>>> location = Location(latitude=55.6761, longitude=12.5683)
>>> location.latitude
55.6761
>>> location.longitude = 10.0  # Raises error (immutable)
```

---

### Timeframe

Shopping timeframe with validation.

```python
from agents.discount_optimizer.domain.models import Timeframe
from datetime import date

timeframe = Timeframe(
    start_date=date(2025, 11, 14),
    end_date=date(2025, 11, 21)
)
```

**Fields:**
- `start_date` (date): Start date of shopping period
- `end_date` (date): End date of shopping period (must be after start_date)

**Validation:**
- `end_date` must be after `start_date`

**Configuration:**
- Immutable (frozen=True)

---

### OptimizationPreferences

User preferences for optimization.

```python
from agents.discount_optimizer.domain.models import OptimizationPreferences

prefs = OptimizationPreferences(
    maximize_savings=True,
    minimize_stores=False,
    prefer_organic=False
)
```

**Fields:**
- `maximize_savings` (bool): Prioritize maximum cost savings (default: True)
- `minimize_stores` (bool): Prioritize shopping at fewer stores (default: False)
- `prefer_organic` (bool): Prioritize organic products (default: False)

**Validation:**
- At least one preference must be True

**Configuration:**
- Immutable (frozen=True)

---

### DiscountItem

Discounted product with full type safety.

```python
from agents.discount_optimizer.domain.models import DiscountItem, Location
from decimal import Decimal
from datetime import date

item = DiscountItem(
    product_name="Organic Milk",
    store_name="Føtex",
    store_location=Location(latitude=55.6761, longitude=12.5683),
    original_price=Decimal("25.00"),
    discount_price=Decimal("18.75"),
    discount_percent=25.0,
    expiration_date=date(2025, 11, 20),
    is_organic=True,
    store_address="Nørrebrogade 20, Copenhagen",
    travel_distance_km=1.2,
    travel_time_minutes=15.0
)
```

**Fields:**
- `product_name` (str): Name of the product (1-200 chars)
- `store_name` (str): Name of the store (1-100 chars)
- `store_location` (Location): Geographic location of the store
- `original_price` (Decimal): Original price before discount (must be positive, 2 decimal places)
- `discount_price` (Decimal): Discounted price (must be less than original_price, 2 decimal places)
- `discount_percent` (float): Discount percentage (0-100)
- `expiration_date` (date): Date when the discount expires
- `is_organic` (bool): Whether the product is organic
- `store_address` (str): Physical address of the store (default: "")
- `travel_distance_km` (float): Distance to store in kilometers (default: 0.0)
- `travel_time_minutes` (float): Estimated travel time in minutes (default: 0.0)

**Validation:**
- `discount_price` must be less than `original_price`
- All prices must be positive
- Discount percent must be 0-100

---

### Purchase

Recommended purchase with meal association.

```python
from agents.discount_optimizer.domain.models import Purchase
from decimal import Decimal
from datetime import date

purchase = Purchase(
    product_name="Organic Milk",
    store_name="Føtex",
    purchase_day=date(2025, 11, 15),
    price=Decimal("18.75"),
    savings=Decimal("6.25"),
    meal_association="Breakfast Smoothie"
)
```

**Fields:**
- `product_name` (str): Name of the product to purchase
- `store_name` (str): Name of the store
- `purchase_day` (date): Recommended day to make the purchase
- `price` (Decimal): Price of the product (must be positive, 2 decimal places)
- `savings` (Decimal): Amount saved (must be non-negative, 2 decimal places)
- `meal_association` (str): Name of the meal this purchase is associated with

---

### ShoppingRecommendation

Complete shopping recommendation output.

```python
from agents.discount_optimizer.domain.models import ShoppingRecommendation
from decimal import Decimal

recommendation = ShoppingRecommendation(
    purchases=[],
    total_savings=Decimal("50.00"),
    time_savings=15.0,
    tips=["Shop early in the morning", "Bring reusable bags"],
    motivation_message="Great job planning ahead!",
    stores=[]
)
```

**Fields:**
- `purchases` (list[Purchase]): List of recommended purchases
- `total_savings` (Decimal): Total amount saved (must be non-negative, 2 decimal places)
- `time_savings` (float): Estimated time saved in minutes (must be non-negative)
- `tips` (list[str]): List of helpful shopping tips
- `motivation_message` (str): Motivational message for the user
- `stores` (list[dict]): List of stores with details

---

## Agent Input/Output Models

### ShoppingOptimizerInput

Main input model for shopping optimization.

```python
from agents.discount_optimizer.agents.shopping_optimizer_agent import ShoppingOptimizerInput

input_data = ShoppingOptimizerInput(
    address="Nørrebrogade 20, Copenhagen",
    meal_plan=[],  # Empty for AI suggestions
    timeframe="this week",
    maximize_savings=True,
    num_meals=5
)
```

**Fields:**
- `address` (str | None): User's address or location description (max 500 chars)
- `latitude` (float | None): Latitude in degrees (-90 to 90)
- `longitude` (float | None): Longitude in degrees (-180 to 180)
- `meal_plan` (list[str]): List of meal names (empty for AI suggestions, max 20 items)
- `timeframe` (str): Shopping timeframe description (default: "this week", max 100 chars)
- `maximize_savings` (bool): Prioritize maximum cost savings (default: True)
- `minimize_stores` (bool): Prioritize shopping at fewer stores (default: False)
- `prefer_organic` (bool): Prioritize organic products (default: False)
- `search_radius_km` (float | None): Search radius in kilometers (0-50)
- `num_meals` (int | None): Number of meals to suggest (1-10)
- `correlation_id` (str | None): Optional correlation ID for distributed tracing

**Validation:**
- Either `address` or both `latitude` and `longitude` must be provided
- Meal plan items are stripped of whitespace

---

### MealSuggestionInput

Input for meal suggestion agent.

```python
from agents.discount_optimizer.agents.meal_suggester_agent import MealSuggestionInput

input_data = MealSuggestionInput(
    available_products=["tortillas", "hakket oksekød", "ost"],
    num_meals=3,
    meal_types=["lunch", "dinner"]
)
```

**Fields:**
- `available_products` (list[str]): List of available product names
- `user_preferences` (str): User dietary preferences (default: "")
- `num_meals` (int): Number of meals to suggest (1-10, default: 3)
- `meal_types` (list[str]): Types of meals (default: ['breakfast', 'lunch', 'dinner'])
- `excluded_ingredients` (list[str]): Ingredients to exclude (default: [])
- `product_details` (list[dict] | None): Optional detailed product information

---

### MealSuggestionOutput

Output from meal suggestion agent.

```python
from agents.discount_optimizer.agents.meal_suggester_agent import MealSuggestionOutput

output = MealSuggestionOutput(
    suggested_meals=["Taco", "Pasta Carbonara", "Greek Salad"],
    reasoning="Selected meals that use available ingredients efficiently",
    urgency_notes="Use milk products within 2 days"
)
```

**Fields:**
- `suggested_meals` (list[str]): List of suggested meal names
- `reasoning` (str): Explanation of suggestions
- `urgency_notes` (str): Notes about product expiration urgency (default: "")

---

### IngredientMappingInput

Input for ingredient mapping agent.

```python
from agents.discount_optimizer.agents.ingredient_mapper_agent import IngredientMappingInput

input_data = IngredientMappingInput(
    meal_name="Taco",
    ingredients=["tortillas", "ground beef", "cheese"],
    available_products=[...],
    match_threshold=0.6,
    max_matches_per_ingredient=5
)
```

**Fields:**
- `meal_name` (str): Name of the meal
- `ingredients` (list[str]): List of required ingredients
- `available_products` (list[dict]): List of available products with details
- `match_threshold` (float): Minimum similarity score for matching (0.0-1.0, default: 0.6)
- `max_matches_per_ingredient` (int): Maximum matches per ingredient (default: 5)

---

### IngredientMappingOutput

Output from ingredient mapping agent.

```python
from agents.discount_optimizer.agents.ingredient_mapper_agent import IngredientMappingOutput

output = IngredientMappingOutput(
    meal_name="Taco",
    mappings=[...],
    total_ingredients=3,
    ingredients_with_matches=3,
    coverage_percent=100.0,
    unmapped_ingredients=[]
)
```

**Fields:**
- `meal_name` (str): Name of the meal
- `mappings` (list[IngredientMapping]): List of ingredient-to-product mappings
- `total_ingredients` (int): Total number of ingredients
- `ingredients_with_matches` (int): Number of ingredients with matches
- `coverage_percent` (float): Percentage of ingredients covered
- `unmapped_ingredients` (list[str]): Ingredients without matches

---

## Agents

### ShoppingOptimizerAgent

Root agent that orchestrates the complete shopping optimization pipeline.

```python
from agents.discount_optimizer.factory import create_production_agent

agent = create_production_agent()
recommendation = await agent.run(input_data)
```

**Methods:**
- `run(input_data: ShoppingOptimizerInput) -> ShoppingRecommendation`: Run the complete optimization pipeline

**Pipeline:**
1. Input validation (location, timeframe, preferences)
2. Discount matching (fetch and filter discounts)
3. Meal suggestion (AI-powered) OR use provided meal plan
4. Ingredient mapping (map meals to products)
5. Multi-criteria optimization (select best purchases)
6. Output formatting (tips and motivation)

---

### MealSuggesterAgent

Agent for AI-powered meal suggestions using Gemini.

```python
from agents.discount_optimizer.agents.meal_suggester_agent import MealSuggesterAgent

agent = MealSuggesterAgent(api_key="your-api-key")
result = await agent.run(input_data)
```

**Methods:**
- `run(input_data: MealSuggestionInput) -> MealSuggestionOutput`: Generate meal suggestions

**Features:**
- Uses Gemini 2.0 Flash for creative suggestions
- Considers product expiration dates
- Respects dietary preferences
- Provides reasoning for suggestions

---

### IngredientMapperAgent

Agent for mapping meals to available products using fuzzy matching.

```python
from agents.discount_optimizer.agents.ingredient_mapper_agent import IngredientMapperAgent

agent = IngredientMapperAgent(api_key="your-api-key")
result = await agent.run(input_data)
```

**Methods:**
- `run(input_data: IngredientMappingInput) -> IngredientMappingOutput`: Map ingredients to products

**Features:**
- Fuzzy string matching with configurable threshold
- Multiple matches per ingredient
- Coverage percentage calculation
- Tracks unmapped ingredients

---

### OutputFormatterAgent

Agent for formatting shopping recommendations with tips and motivation.

```python
from agents.discount_optimizer.agents.output_formatter_agent import OutputFormatterAgent

agent = OutputFormatterAgent(api_key="your-api-key")
result = await agent.run(input_data)
```

**Methods:**
- `run(input_data: FormattingInput) -> FormattingOutput`: Format recommendations

**Features:**
- Generates helpful shopping tips
- Creates motivational messages
- Formats store summaries
- Highlights urgent purchases

---

## Services

### InputValidationService

Service for validating user input.

```python
from agents.discount_optimizer.services.input_validation_service import InputValidationService

service = InputValidationService(geocoding_service=geocoding_service)
result = await service.run(input_data)
```

**Methods:**
- `run(input_data: ValidationInput) -> ValidationOutput`: Validate input data

**Validation:**
- Location (address or coordinates)
- Timeframe parsing
- Preference validation
- Search radius validation

---

### DiscountMatcherService

Service for fetching and filtering discounts.

```python
from agents.discount_optimizer.services.discount_matcher_service import DiscountMatcherService

service = DiscountMatcherService(
    discount_repository=discount_repository,
    cache_repository=cache_repository
)
result = await service.match_discounts(input_data)
```

**Methods:**
- `match_discounts(input_data: DiscountMatchingInput) -> DiscountMatchingOutput`: Fetch and filter discounts

**Features:**
- Caching with TTL
- Distance filtering
- Discount percentage filtering
- Organic product filtering
- Sorting by discount percentage

---

### MultiCriteriaOptimizerService

Service for optimizing purchases using multi-criteria scoring.

```python
from agents.discount_optimizer.services.multi_criteria_optimizer_service import MultiCriteriaOptimizerService

service = MultiCriteriaOptimizerService()
result = service.optimize(input_data)
```

**Methods:**
- `optimize(input_data: OptimizationInput) -> OptimizationOutput`: Optimize purchases

**Scoring Criteria:**
- Discount percentage
- Travel distance
- Store consolidation
- Product expiration urgency
- Organic preference

---

## Repositories

### SallingDiscountRepository

Repository for Salling Group API with connection pooling and retry logic.

```python
from agents.discount_optimizer.infrastructure.salling_repository import SallingDiscountRepository

repository = SallingDiscountRepository(api_key="your-api-key")
discounts = await repository.fetch_discounts(location, radius_km=5.0)
```

**Methods:**
- `fetch_discounts(location: Location, radius_km: float) -> list[DiscountItem]`: Fetch discounts
- `health_check() -> bool`: Check API health

**Features:**
- Automatic retry with exponential backoff (3 attempts)
- Connection pooling
- Timeout configuration
- Structured logging

---

### GoogleMapsRepository

Repository for Google Maps API with geocoding and distance calculation.

```python
from agents.discount_optimizer.infrastructure.google_maps_repository import GoogleMapsRepository

repository = GoogleMapsRepository(api_key="your-api-key")
location = await repository.geocode_address("Nørrebrogade 20, Copenhagen")
distance = await repository.calculate_distance(origin, destination)
```

**Methods:**
- `geocode_address(address: str) -> Location`: Convert address to coordinates
- `calculate_distance(origin: Location, destination: Location) -> float`: Calculate distance in km
- `find_nearby_stores(location: Location, radius_km: float) -> list[dict]`: Find nearby stores
- `health_check() -> bool`: Check API health

**Features:**
- Haversine formula for distance calculation
- Automatic retry with exponential backoff
- Connection pooling
- Timeout configuration

---

### InMemoryCacheRepository

In-memory cache repository with TTL support.

```python
from agents.discount_optimizer.infrastructure.cache_repository import InMemoryCacheRepository

repository = InMemoryCacheRepository()
await repository.set("key", b"value", ttl_seconds=3600)
value = await repository.get("key")
```

**Methods:**
- `get(key: str) -> bytes | None`: Get cached value
- `set(key: str, value: bytes, ttl_seconds: int) -> None`: Set cached value with TTL
- `delete(key: str) -> None`: Delete cached value
- `clear() -> None`: Clear all cached values
- `get_stats() -> dict`: Get cache statistics

**Features:**
- TTL-based expiration
- Thread-safe operations
- Cache statistics (hit rate, miss rate)
- Automatic cleanup of expired entries

---

## Configuration

### Settings

Application settings with environment variable validation.

```python
from agents.discount_optimizer.config import settings

# Access configuration
api_key = settings.google_api_key.get_secret_value()
temperature = settings.agent_temperature
cache_ttl = settings.cache_ttl_seconds

# Check environment
if settings.is_production():
    print("Running in production")

# Get agent configuration
agent_config = settings.get_agent_config()
```

**API Keys:**
- `google_api_key` (SecretStr): Google Gemini API key
- `salling_group_api_key` (SecretStr | None): Salling Group API key
- `google_maps_api_key` (SecretStr | None): Google Maps API key

**Environment:**
- `environment` (Literal['dev', 'staging', 'production']): Deployment environment
- `debug` (bool): Enable debug mode

**Agent Configuration:**
- `agent_model` (str): Gemini model name (default: 'gemini-2.0-flash-exp')
- `agent_temperature` (float): Temperature for responses (0.0-2.0, default: 0.7)
- `agent_max_tokens` (int): Maximum output tokens (default: 2000)
- `agent_top_p` (float): Nucleus sampling parameter (0.0-1.0, default: 0.95)
- `agent_top_k` (int): Top-k sampling parameter (1-100, default: 40)

**Performance:**
- `cache_ttl_seconds` (int): Cache TTL (default: 3600)
- `api_timeout_seconds` (int): API timeout (default: 30)
- `max_concurrent_requests` (int): Max concurrent requests (default: 10)
- `max_retries` (int): Max retry attempts (default: 3)

**Feature Flags:**
- `enable_ai_meal_suggestions` (bool): Enable AI suggestions (default: True)
- `enable_caching` (bool): Enable caching (default: True)
- `enable_metrics` (bool): Enable metrics (default: True)
- `enable_structured_logging` (bool): Enable structured logging (default: True)

**Logging:**
- `log_level` (Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']): Log level
- `log_format` (Literal['json', 'console', 'text']): Log format
- `log_file` (str | None): Log file path

**Business Logic:**
- `default_search_radius_km` (float): Default search radius (default: 5.0)
- `max_stores_per_recommendation` (int): Max stores (default: 3)
- `min_discount_percent` (float): Min discount percentage (default: 10.0)
- `max_travel_distance_km` (float): Max travel distance (default: 20.0)

**Methods:**
- `get_google_maps_key() -> str`: Get Google Maps API key
- `get_logging_level() -> int`: Get Python logging level
- `is_production() -> bool`: Check if production environment
- `is_development() -> bool`: Check if development environment
- `get_agent_config() -> dict`: Get agent generation configuration
- `validate_required_keys() -> None`: Validate required API keys

---

## Exceptions

### ShoppingOptimizerError

Base exception for all shopping optimizer errors.

```python
from agents.discount_optimizer.domain.exceptions import ShoppingOptimizerError

raise ShoppingOptimizerError("Something went wrong")
```

---

### ValidationError

Input validation failed.

```python
from agents.discount_optimizer.domain.exceptions import ValidationError

raise ValidationError("Invalid coordinates: latitude must be between -90 and 90")
```

**Use Cases:**
- Invalid coordinates
- Invalid dates
- Missing required fields
- Invalid preference combinations

---

### APIError

External API call failed.

```python
from agents.discount_optimizer.domain.exceptions import APIError

raise APIError("Salling API returned 500 Internal Server Error")
```

**Use Cases:**
- API timeout
- API rate limit exceeded
- API authentication failure
- API service unavailable

---

### AgentError

Agent execution failed.

```python
from agents.discount_optimizer.domain.exceptions import AgentError

raise AgentError("Meal suggestion agent failed to generate suggestions")
```

**Use Cases:**
- Agent timeout
- Agent model error
- Agent output parsing failure
- Agent internal error

---

## Factory

### AgentFactory

Factory for creating fully-wired agent instances with dependency injection.

```python
from agents.discount_optimizer.factory import AgentFactory

# Create factory
factory = AgentFactory()

# Create root agent
agent = factory.create_shopping_optimizer_agent()

# Create with custom configuration
from agents.discount_optimizer.config import Settings
custom_settings = Settings(agent_temperature=0.9)
factory = AgentFactory(config=custom_settings)
agent = factory.create_shopping_optimizer_agent()

# Create with mocks for testing
factory = AgentFactory(
    geocoding_service=mock_geocoding,
    discount_repository=mock_repository
)
agent = factory.create_shopping_optimizer_agent()
```

**Methods:**
- `create_shopping_optimizer_agent() -> ShoppingOptimizerAgent`: Create root agent
- `get_meal_suggester_agent() -> MealSuggesterAgent`: Get meal suggester
- `get_ingredient_mapper_agent() -> IngredientMapperAgent`: Get ingredient mapper
- `get_output_formatter_agent() -> OutputFormatterAgent`: Get output formatter
- `get_input_validation_service() -> InputValidationService`: Get input validator
- `get_discount_matcher_service() -> DiscountMatcherService`: Get discount matcher
- `get_multi_criteria_optimizer_service() -> MultiCriteriaOptimizerService`: Get optimizer
- `reset() -> None`: Reset all lazy-initialized instances

**Convenience Functions:**
- `create_production_agent() -> ShoppingOptimizerAgent`: Create production agent
- `create_test_agent(...) -> ShoppingOptimizerAgent`: Create test agent with mocks

# Migration Guide: Legacy to Google ADK Architecture

This guide helps you migrate from the legacy procedural implementation to the new Google ADK-based architecture with full type safety and dependency injection.

## Overview of Changes

### Before (Legacy)
- Procedural pipeline in single `optimize_shopping()` function
- Direct API calls without abstraction
- No type safety or validation
- Mixed concerns (business logic + API calls + formatting)
- No dependency injection
- Synchronous operations

### After (Modern ADK)
- Agent-based architecture with Google ADK
- Repository pattern for API abstraction
- 100% type coverage with Pydantic and mypy
- Clean separation of concerns (layered architecture)
- Full dependency injection
- Async/await throughout

## Migration Steps

### Step 1: Update Dependencies

Update your `requirements.txt` or install new dependencies:

```bash
pip install pydantic pydantic-settings google-genai tenacity structlog httpx
```

### Step 2: Migrate Data Models

**Before:**
```python
# Untyped dictionaries
user_input = {
    'latitude': 55.6761,
    'longitude': 12.5683,
    'meal_plan': ['Taco', 'Pasta']
}
```

**After:**
```python
from agents.discount_optimizer.agents.shopping_optimizer_agent import ShoppingOptimizerInput

# Typed Pydantic model with validation
user_input = ShoppingOptimizerInput(
    latitude=55.6761,
    longitude=12.5683,
    meal_plan=['Taco', 'Pasta'],
    timeframe='this week',
    maximize_savings=True
)
```

### Step 3: Migrate API Calls

**Before:**
```python
import requests

def fetch_discounts(lat, lon):
    response = requests.get(
        'https://api.sallinggroup.com/v1/food-waste/',
        headers={'Authorization': f'Bearer {api_key}'}
    )
    return response.json()
```

**After:**
```python
from agents.discount_optimizer.infrastructure.salling_repository import SallingDiscountRepository
from agents.discount_optimizer.domain.models import Location

# Repository with retry logic, connection pooling, and type safety
repository = SallingDiscountRepository(api_key=api_key)

location = Location(latitude=55.6761, longitude=12.5683)
discounts = await repository.fetch_discounts(location, radius_km=5.0)
# Returns: list[DiscountItem] with full validation
```

### Step 4: Migrate Agent Usage

**Before:**
```python
from agents.discount_optimizer.meal_suggester import MealSuggester

# Direct API call
suggester = MealSuggester()
meals = suggester.suggest_meals(products)
```

**After:**
```python
from agents.discount_optimizer.agents.meal_suggester_agent import (
    MealSuggesterAgent,
    MealSuggestionInput
)

# ADK agent with typed input/output
agent = MealSuggesterAgent(api_key=api_key)

input_data = MealSuggestionInput(
    available_products=['tortillas', 'hakket oksekød', 'ost'],
    num_meals=3
)

result = await agent.run(input_data)
# Returns: MealSuggestionOutput with validated fields
print(result.suggested_meals)  # Type-safe access
```

### Step 5: Use Factory for Dependency Injection

**Before:**
```python
# Manual instantiation with tight coupling
def optimize_shopping(user_input):
    validator = InputValidator()
    api_client = SallingAPIClient()
    meal_suggester = MealSuggester()
    # ... manually wire everything
```

**After:**
```python
from agents.discount_optimizer.factory import create_production_agent

# Factory handles all wiring
agent = create_production_agent()

# All dependencies injected automatically
recommendation = await agent.run(input_data)
```

### Step 6: Migrate Configuration

**Before:**
```python
import os

# Manual environment variable access
API_KEY = os.getenv('GOOGLE_API_KEY')
TEMPERATURE = float(os.getenv('TEMPERATURE', '0.7'))
```

**After:**
```python
from agents.discount_optimizer.config import settings

# Type-safe configuration with validation
api_key = settings.google_api_key.get_secret_value()
temperature = settings.agent_temperature  # Already validated as float
```

### Step 7: Migrate Error Handling

**Before:**
```python
try:
    result = fetch_discounts()
except Exception as e:
    print(f"Error: {e}")
```

**After:**
```python
from agents.discount_optimizer.domain.exceptions import (
    ValidationError,
    APIError,
    ShoppingOptimizerError
)

try:
    recommendation = await agent.run(input_data)
except ValidationError as e:
    # Handle input validation errors
    logger.error("Invalid input", error=str(e))
except APIError as e:
    # Handle external API failures
    logger.error("API call failed", error=str(e))
except ShoppingOptimizerError as e:
    # Handle general optimization errors
    logger.error("Optimization failed", error=str(e))
```

### Step 8: Migrate Tests

**Before:**
```python
def test_meal_suggester():
    suggester = MealSuggester()
    result = suggester.suggest_meals(['milk', 'eggs'])
    assert len(result) > 0
```

**After:**
```python
import pytest
from agents.discount_optimizer.agents.meal_suggester_agent import (
    MealSuggesterAgent,
    MealSuggestionInput,
    MealSuggestionOutput
)

@pytest.mark.asyncio
async def test_meal_suggester():
    agent = MealSuggesterAgent(api_key='test-key')
    
    input_data = MealSuggestionInput(
        available_products=['milk', 'eggs'],
        num_meals=2
    )
    
    result = await agent.run(input_data)
    
    # Type-safe assertions
    assert isinstance(result, MealSuggestionOutput)
    assert len(result.suggested_meals) == 2
    assert all(isinstance(meal, str) for meal in result.suggested_meals)
```

## Common Migration Patterns

### Pattern 1: Synchronous to Async

**Before:**
```python
def fetch_data():
    response = requests.get(url)
    return response.json()

result = fetch_data()
```

**After:**
```python
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

result = await fetch_data()
```

### Pattern 2: Dictionary to Pydantic Model

**Before:**
```python
discount = {
    'product_name': 'Milk',
    'price': 25.0,
    'discount_percent': 30
}

# No validation
if discount['price'] < 0:
    raise ValueError("Invalid price")
```

**After:**
```python
from agents.discount_optimizer.domain.models import DiscountItem
from decimal import Decimal

# Automatic validation
discount = DiscountItem(
    product_name='Milk',
    store_name='Føtex',
    store_location=Location(latitude=55.6761, longitude=12.5683),
    original_price=Decimal('35.71'),
    discount_price=Decimal('25.00'),
    discount_percent=30.0,
    expiration_date=date(2025, 11, 20),
    is_organic=False
)
# Raises ValidationError if any field is invalid
```

### Pattern 3: Manual Dependency Management to Factory

**Before:**
```python
class ShoppingOptimizer:
    def __init__(self):
        self.api_client = SallingAPIClient()
        self.meal_suggester = MealSuggester()
        # Hard-coded dependencies

optimizer = ShoppingOptimizer()
```

**After:**
```python
from agents.discount_optimizer.factory import AgentFactory

# Factory handles all dependencies
factory = AgentFactory()
optimizer = factory.create_shopping_optimizer_agent()

# For testing with mocks
factory = AgentFactory(
    discount_repository=mock_repository,
    geocoding_service=mock_geocoding
)
optimizer = factory.create_shopping_optimizer_agent()
```

## Type Checking Migration

### Enable Gradual Typing

The project uses a gradual typing strategy. New modules are strictly typed, while legacy modules can remain permissive during migration.

**mypy.ini configuration:**
```ini
[mypy]
python_version = 3.11
strict = False  # Global default: permissive

# Strict checking for refactored modules
[mypy-agents.discount_optimizer.domain.*]
strict = True

[mypy-agents.discount_optimizer.agents.*]
strict = True

[mypy-agents.discount_optimizer.infrastructure.*]
strict = True

[mypy-agents.discount_optimizer.services.*]
strict = True

# Ignore legacy modules during migration
[mypy-agents.discount_optimizer.legacy.*]
ignore_errors = True
```

### Run Type Checking

```bash
# Check all code
mypy agents/

# Check specific module
mypy agents/discount_optimizer/domain/

# Use project script
./scripts/type_check.sh
```

## Testing Migration

### Update Test Structure

**Before:**
```
tests/
├── test_meal_suggester.py
├── test_discount_matcher.py
└── test_integration.py
```

**After:**
```
tests/
├── agents/
│   └── test_shopping_optimizer_agent.py
├── services/
│   ├── test_discount_matcher_service.py
│   └── test_input_validation_service.py
├── integration/
│   └── test_agent_pipeline.py
└── conftest.py  # Shared fixtures
```

### Create Test Fixtures

```python
# tests/conftest.py
import pytest
from agents.discount_optimizer.factory import AgentFactory

@pytest.fixture
def agent_factory():
    """Factory for creating test agents."""
    return AgentFactory()

@pytest.fixture
async def shopping_optimizer_agent(agent_factory):
    """Fully-wired shopping optimizer agent."""
    return agent_factory.create_shopping_optimizer_agent()

@pytest.fixture
def sample_input():
    """Sample input data for testing."""
    from agents.discount_optimizer.agents.shopping_optimizer_agent import ShoppingOptimizerInput
    return ShoppingOptimizerInput(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=[],
        timeframe='this week',
        maximize_savings=True
    )
```

## Troubleshooting

### Issue: "Module not found" errors

**Solution:** Ensure you've installed all new dependencies:
```bash
pip install -r requirements.txt
```

### Issue: Type checking errors in legacy code

**Solution:** Add module to ignore list in `mypy.ini`:
```ini
[mypy-agents.discount_optimizer.legacy_module]
ignore_errors = True
```

### Issue: Async/await syntax errors

**Solution:** Ensure you're using Python 3.11+ and running async functions properly:
```python
import asyncio

async def main():
    result = await agent.run(input_data)
    return result

# Run async function
result = asyncio.run(main())
```

### Issue: Pydantic validation errors

**Solution:** Check the error message for specific field issues:
```python
from pydantic import ValidationError

try:
    model = DiscountItem(**data)
except ValidationError as e:
    print(e.json())  # Detailed error information
```

## Best Practices

1. **Migrate incrementally**: Start with data models, then infrastructure, then agents
2. **Write tests first**: Ensure existing functionality works before refactoring
3. **Use type hints**: Add type hints to all new code
4. **Validate early**: Use Pydantic models at system boundaries
5. **Inject dependencies**: Never instantiate dependencies directly in classes
6. **Handle errors gracefully**: Use typed exceptions and provide fallbacks
7. **Log with context**: Use structured logging with correlation IDs
8. **Test with mocks**: Use dependency injection to test with mocks

## Additional Resources

- [Type Checking Strategy](TYPE_CHECKING_STRATEGY.md)
- [Architecture Design](../.kiro/specs/google-adk-modernization/design.md)
- [Requirements Document](../.kiro/specs/google-adk-modernization/requirements.md)
- [Google ADK Documentation](https://ai.google.dev/gemini-api/docs/adk)
- [Pydantic Documentation](https://docs.pydantic.dev/)

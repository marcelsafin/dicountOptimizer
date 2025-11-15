# Shopping Optimizer - Food Waste Meal Planner

An intelligent AI agent that helps you save money and reduce food waste by finding discounted food waste products within 2km of your location and generating creative meal suggestions using Gemini 2.5 Pro.

## What It Does

The Shopping Optimizer fetches real-time food waste discounts from major Danish grocery chains (Netto, Føtex, Bilka, BR) through the Salling Group API, then uses Google's Gemini 2.5 Pro AI to suggest creative meals you can make with the available products. It's designed to:

- **Reduce food waste**: Focus on products that need to be sold quickly
- **Save money**: Find the best discounts (often 30-70% off)
- **Simplify shopping**: Get meal ideas based on what's actually available nearby
- **Support local**: Only shows stores within 2km (walking/biking distance)

## ⚠️ CRITICAL: Async Server Required

**This application MUST be run with Gunicorn + Uvicorn workers.** 

DO NOT use `python app.py` or `flask run` - these are blocking, single-threaded development servers that will destroy all async performance optimizations from Phase 2 (Requirements 8.2, 8.6).

See [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) for complete instructions.

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Get API Keys

#### Salling Group API (Required)

The Salling Group API provides real-time food waste data from Danish grocery stores.

1. Visit: https://developer.sallinggroup.com/
2. Click "Sign Up" and create an account
3. Go to "Applications" and create a new application
4. Copy your API key (Bearer token)
5. **Important**: This API only works for stores in Denmark

**API Details**:
- Endpoint used: `https://api.sallinggroup.com/v1/food-waste/`
- Rate limits: 10,000 requests/day (free tier)
- Coverage: Netto, Føtex, Bilka, BR stores in Denmark
- Documentation: https://developer.sallinggroup.com/api-reference#food-waste-api

#### Google Gemini API (Required)

Gemini 2.5 Pro generates creative meal suggestions based on available products.

1. Visit: https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

**API Details**:
- Model used: gemini-2.5-pro
- Free tier: 60 requests per minute
- Used for: AI meal generation and recipe suggestions
- Documentation: https://ai.google.dev/gemini-api/docs

#### Configure Environment Variables

Create or update the `.env` file in the project root:

```bash
SALLING_GROUP_API_KEY=your_salling_api_key_here
GOOGLE_API_KEY=your_gemini_api_key_here
```

**Security Note**: Never share your API keys publicly! The `.env` file is already in `.gitignore`.

### 3. Run the Application

**⚠️ IMPORTANT**: This application uses async/await throughout (Requirements 8.2, 8.6). You MUST use an ASGI server (Gunicorn + Uvicorn) to preserve async performance. Never use `python app.py` or `flask run` - these are blocking, single-threaded servers that will destroy all performance optimizations.

#### Local Development

```bash
# Install production server dependencies (if not already installed)
pip install gunicorn uvicorn[standard]

# Start with Gunicorn + Uvicorn worker (async-capable)
gunicorn app:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:3000 \
  --reload

# Or use the shorthand:
gunicorn app:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:3000 --reload
```

Open your browser at: **http://127.0.0.1:3000**

#### Production Deployment

```bash
# Production configuration with multiple workers
gunicorn app:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:$PORT \
  --timeout 120 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

**Why Gunicorn + Uvicorn?**
- **Gunicorn**: Process manager with multiple workers for load balancing
- **Uvicorn**: ASGI server that supports async/await natively
- **Together**: Enterprise-grade async performance with proper concurrency

**Performance Impact**:
- ❌ `python app.py`: Single-threaded, blocking I/O (~1 req/sec)
- ✅ Gunicorn + Uvicorn: Multi-worker, async I/O (~100+ req/sec)

## How to Use

### Web Interface

1. **Enter Your Location**:
   - Click "Use My Location" to auto-detect (requires browser permission)
   - Or manually enter latitude and longitude coordinates
   - Example: Copenhagen center is approximately 55.6761, 12.5683

2. **Search for Food Waste**:
   - Click "Find Meals" button
   - The system searches within a fixed 2km radius
   - Wait for results (typically 5-15 seconds)

3. **Review Meal Suggestions**:
   - See 3-5 AI-generated meal ideas
   - Each meal shows required products, stores, and savings
   - Products are grouped by store for easy shopping

4. **Check Savings & Tips**:
   - View total monetary savings in DKK
   - Get tips on products expiring soon
   - See which stores to visit

### Understanding the 2km Radius

The system uses a **fixed 2km search radius** for several reasons:

- **Walkable/Bikeable**: Encourages sustainable transportation
- **Fresh Products**: Food waste items need to be used quickly
- **Realistic Shopping**: Most people shop within their neighborhood
- **Better Results**: Focuses on truly nearby options

Distance is calculated using the Haversine formula for geographic accuracy.

### Food Waste Focus

This system specifically targets **food waste products** - items that stores need to sell quickly before expiration. Benefits include:

- **Higher Discounts**: Typically 30-70% off regular prices
- **Environmental Impact**: Helps reduce food waste
- **Quality Products**: Still fresh, just need to be used soon
- **Variety**: Changes daily based on what's available

**Important**: Plan to use these products within 1-3 days of purchase.

## System Architecture

### Architecture Overview

The Shopping Optimizer follows a modern, enterprise-grade architecture using **Google ADK (Agent Development Kit)** with comprehensive type safety, dependency injection, and clean separation of concerns. The system is built on four distinct layers:

```
┌─────────────────────────────────────────────────────────┐
│              Presentation Layer                          │
│  (Flask API, CLI, Web UI)                               │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Agent Layer (Google ADK)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ MealSuggester│  │IngredientMap │  │OutputFormatter│ │
│  │    Agent     │  │    Agent     │  │    Agent      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │     ShoppingOptimizerAgent (Root Agent)          │  │
│  │  Orchestrates all sub-agents with DI             │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Business Logic Layer                        │
│  (Services, Domain Models, Validation)                  │
│  - InputValidationService                               │
│  - DiscountMatcherService                               │
│  - MultiCriteriaOptimizerService                        │
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

The root `ShoppingOptimizerAgent` composes specialized sub-agents using **dependency injection**:

```
ShoppingOptimizerAgent (Root)
├── InputValidationService (validates user input)
├── DiscountMatcherService (fetches and filters discounts)
├── MealSuggesterAgent (AI meal suggestions via Gemini)
├── IngredientMapperAgent (maps meals to products)
├── MultiCriteriaOptimizerService (optimizes purchases)
└── OutputFormatterAgent (formats recommendations)
```

Each agent:
- Has a **single responsibility** (SOLID principles)
- Uses **typed tool functions** with Pydantic models
- Validates **inputs/outputs** automatically
- Can be **tested independently**
- Implements **retry and error handling**
- Supports **graceful fallbacks**

### High-Level Workflow

```
User Input (address or coordinates)
    ↓
Input Validation (location, timeframe, preferences)
    ↓
Discount Matching (fetch from Salling API, filter by distance)
    ↓
Meal Suggestion (AI-powered via Gemini OR use provided meal plan)
    ↓
Ingredient Mapping (map meals to available products)
    ↓
Multi-Criteria Optimization (select best purchases)
    ↓
Output Formatting (tips, motivation, store summary)
    ↓
Display Results to User
```

### Key Technologies

- **Backend**: Python 3.11+, Flask, Google ADK
- **Type Safety**: Pydantic, mypy strict mode, Protocol classes
- **AI**: Google Gemini 2.0 Flash for agent functionality
- **APIs**: Salling Group Food Waste API, Google Maps API
- **Architecture**: Dependency Injection, Repository Pattern, Factory Pattern
- **Async**: httpx with connection pooling, async/await throughout
- **Caching**: In-memory cache with TTL
- **Logging**: Structured logging with correlation IDs
- **Frontend**: Vanilla JavaScript, HTML5, CSS3

### Type Safety

The codebase achieves **100% type coverage** in all refactored modules using:

- **Pydantic models** for all data structures with validation
- **Protocol classes** for dependency injection interfaces
- **mypy strict mode** for static type checking
- **Gradual typing strategy** for legacy code migration

See [Type Checking Documentation](docs/TYPE_CHECKING_STRATEGY.md) for details.

### Configuration Management

All configuration is managed through **Pydantic Settings** with:

- Environment variable validation
- Type-safe access to all settings
- Secrets management (SecretStr for API keys)
- Feature flags for gradual rollout
- Environment-specific configuration (dev/staging/production)

See [Configuration Guide](#configuration) for details.

## Troubleshooting

### Common Issues

#### "No food waste products found"

**Possible Causes**:
- Location is outside Denmark (Salling API only covers Danish stores)
- No stores within 2km radius
- No food waste available at nearby stores today

**Solutions**:
- Try a different location in Denmark (e.g., Copenhagen, Aarhus, Odense)
- Check that coordinates are correct (latitude, longitude)
- Try again later - food waste inventory changes throughout the day

#### "API Error: 401 Unauthorized"

**Cause**: Invalid or missing Salling Group API key

**Solutions**:
1. Verify your API key is correct in `.env` file
2. Check that you copied the entire key (no extra spaces)
3. Ensure your Salling Group account is active
4. Generate a new API key if needed

#### "API Error: 429 Too Many Requests"

**Cause**: Exceeded Salling Group API rate limit (10,000 requests/day)

**Solutions**:
- Wait a few minutes before trying again
- The system caches responses for 24h to minimize API calls
- Check if you have other applications using the same API key

#### "Gemini API Error"

**Possible Causes**:
- Invalid Google API key
- Rate limit exceeded (60 requests/minute)
- Network connectivity issues

**Solutions**:
1. Verify your Google API key in `.env` file
2. Wait a minute if you've made many requests
3. Check your internet connection
4. Ensure Gemini API is enabled in your Google Cloud project

#### "Invalid coordinates"

**Cause**: Latitude or longitude values are out of valid range

**Solutions**:
- Latitude must be between -90 and 90
- Longitude must be between -180 and 180
- Use decimal format (e.g., 55.6761, not 55°40'34"N)
- Try using the "Use My Location" button instead

#### No results displayed after clicking "Find Meals"

**Solutions**:
1. Open browser console (F12) to check for JavaScript errors
2. Check terminal/console for Python errors
3. Verify both API keys are configured in `.env`
4. Restart the Flask server: `python app.py`
5. Clear browser cache and reload page

#### Geolocation not working

**Cause**: Browser doesn't have location permission

**Solutions**:
- Click the location icon in browser address bar
- Allow location access when prompted
- If blocked, go to browser settings and enable location for localhost
- Alternatively, manually enter coordinates

### API Status & Monitoring

**Check Salling Group API Status**:
- Visit: https://developer.sallinggroup.com/
- Check for service announcements
- Verify your API key is active in your account dashboard

**Check Gemini API Status**:
- Visit: https://status.cloud.google.com/
- Look for "Vertex AI" or "Generative AI" services

### Debug Mode

Enable detailed logging by modifying `app.py`:

```python
# Add at the top of app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show detailed API requests, responses, and processing steps in the terminal.

### Getting Help

If you encounter issues not covered here:

1. Check the terminal/console for error messages
2. Review the API documentation:
   - Salling Group: https://developer.sallinggroup.com/api-reference
   - Gemini: https://ai.google.dev/gemini-api/docs
3. Verify your `.env` file has both API keys configured
4. Try the demo scripts to test individual components:
   - `python demo.py` - Test basic workflow
   - `python demo_optimized_meals.py` - Test meal generation

## Testing

The project includes comprehensive tests:

```bash
# Run all tests
python -m pytest

# Test with real APIs (requires valid API keys)
python test_complete_workflow_real_apis.py

# Test individual components
python test_unit_core_components.py
python test_integration_mocked.py
```

## Project Structure

```
.
├── agents/
│   └── discount_optimizer/
│       ├── agents/                     # Google ADK Agents
│       │   ├── shopping_optimizer_agent.py    # Root orchestration agent
│       │   ├── meal_suggester_agent.py        # AI meal suggestions
│       │   ├── ingredient_mapper_agent.py     # Ingredient-to-product mapping
│       │   └── output_formatter_agent.py      # Output formatting
│       ├── services/                   # Business Logic Services
│       │   ├── input_validation_service.py    # Input validation
│       │   ├── discount_matcher_service.py    # Discount fetching/filtering
│       │   └── multi_criteria_optimizer_service.py  # Purchase optimization
│       ├── infrastructure/             # External API Repositories
│       │   ├── salling_repository.py          # Salling Group API client
│       │   ├── google_maps_repository.py      # Google Maps API client
│       │   └── cache_repository.py            # In-memory cache
│       ├── domain/                     # Domain Models & Protocols
│       │   ├── models.py                      # Pydantic data models
│       │   ├── protocols.py                   # Protocol interfaces
│       │   └── exceptions.py                  # Typed exceptions
│       ├── factory.py                  # Agent factory (DI)
│       ├── config.py                   # Configuration management
│       └── logging.py                  # Structured logging
├── templates/
│   └── index.html                      # Web UI template
├── static/
│   ├── css/styles.css                  # UI styling
│   └── js/app.js                       # Frontend logic
├── tests/                              # Comprehensive test suite
│   ├── agents/                         # Agent tests
│   ├── services/                       # Service tests
│   ├── integration/                    # Integration tests
│   └── observability/                  # Monitoring tests
├── docs/                               # Documentation
│   ├── API_REFERENCE.md                # Complete API reference
│   ├── MIGRATION_GUIDE.md              # Migration guide
│   ├── TYPE_CHECKING_STRATEGY.md       # Type checking approach
│   ├── TYPE_CHECKING_VALIDATION_REPORT.md  # Type coverage status
│   └── TYPE_CHECKING_QUICK_REFERENCE.md    # Quick reference
├── examples/                           # Usage examples
│   ├── agent_composition_example.py    # Agent composition patterns
│   └── factory_usage_example.py        # Factory usage
├── .kiro/specs/google-adk-modernization/  # Spec documentation
│   ├── requirements.md                 # Requirements (EARS format)
│   ├── design.md                       # Architecture design
│   └── tasks.md                        # Implementation tasks
├── app.py                              # Flask web server
├── requirements.txt                    # Python dependencies
├── mypy.ini                            # Type checking configuration
├── .env                                # API keys (not in git)
└── .env.example                        # Example configuration
```

### Key Directories

**`agents/discount_optimizer/agents/`**: Google ADK agents with single responsibilities
- Each agent is independently testable
- Uses typed tool functions with Pydantic models
- Implements retry and error handling

**`agents/discount_optimizer/services/`**: Business logic services
- Stateless services for specific tasks
- No external dependencies (injected via constructor)
- Pure business logic without I/O

**`agents/discount_optimizer/infrastructure/`**: External API clients
- Repository pattern for API abstraction
- Async/await with connection pooling
- Automatic retry with exponential backoff

**`agents/discount_optimizer/domain/`**: Core domain models
- Pydantic models with comprehensive validation
- Protocol interfaces for dependency injection
- Typed exception hierarchy

**`docs/`**: Comprehensive documentation
- API reference for all models and agents
- Migration guide from legacy code
- Type checking strategy and validation reports

**`examples/`**: Working code examples
- Agent composition patterns
- Factory usage
- Error handling
- Testing with mocks

## Documentation

### Complete Documentation Suite

- **[Quick Start Guide](docs/QUICK_START.md)**: Get up and running in 5 minutes
- **[API Reference](docs/API_REFERENCE.md)**: Complete API documentation for all models, agents, services, and repositories
- **[Architecture Guide](docs/ARCHITECTURE.md)**: Detailed architecture documentation with diagrams and design patterns
- **[Migration Guide](docs/MIGRATION_GUIDE.md)**: Step-by-step guide for migrating from legacy code to modern ADK architecture
- **[Type Checking Strategy](docs/TYPE_CHECKING_STRATEGY.md)**: Gradual typing approach and best practices
- **[Type Checking Validation Report](docs/TYPE_CHECKING_VALIDATION_REPORT.md)**: Current type coverage status
- **[Type Checking Quick Reference](docs/TYPE_CHECKING_QUICK_REFERENCE.md)**: Common type checking patterns

### Specification Documents

- **[Requirements](/.kiro/specs/google-adk-modernization/requirements.md)**: Detailed requirements in EARS format
- **[Design](/.kiro/specs/google-adk-modernization/design.md)**: Architecture design document
- **[Tasks](/.kiro/specs/google-adk-modernization/tasks.md)**: Implementation task list

### Code Examples

- **[Agent Composition Example](examples/agent_composition_example.py)**: Comprehensive examples of agent usage patterns
- **[Factory Usage Example](examples/factory_usage_example.py)**: Dependency injection and factory patterns

## Development

### Type Checking

This project uses strict type checking with mypy for all refactored modules. The codebase follows a gradual typing strategy:

- **Refactored modules**: 100% type coverage with strict mode
- **Legacy modules**: Permissive mode during migration

**Run type checks:**
```bash
./scripts/type_check.sh
```

**Type Coverage Status:**
- ✅ Domain layer: 100%
- ✅ Infrastructure layer: 100%
- ✅ Agent layer: 100%
- ✅ Services layer: 100%
- ✅ Configuration: 100%

## Agent Usage Examples

### Basic Usage with Factory

The simplest way to use the Shopping Optimizer is through the factory:

```python
from agents.discount_optimizer.factory import create_production_agent
from agents.discount_optimizer.agents.shopping_optimizer_agent import ShoppingOptimizerInput

# Create agent with all dependencies wired
agent = create_production_agent()

# Create input
input_data = ShoppingOptimizerInput(
    address="Nørrebrogade 20, Copenhagen",
    meal_plan=[],  # Empty for AI suggestions
    timeframe="this week",
    maximize_savings=True,
    num_meals=5
)

# Run optimization
recommendation = await agent.run(input_data)

# Access results
print(f"Total savings: {recommendation.total_savings} kr")
print(f"Stores to visit: {len(recommendation.stores)}")
for purchase in recommendation.purchases:
    print(f"- {purchase.product_name} at {purchase.store_name}: {purchase.price} kr")
```

### Using Coordinates Instead of Address

```python
input_data = ShoppingOptimizerInput(
    latitude=55.6761,
    longitude=12.5683,
    meal_plan=["Taco", "Pasta Carbonara", "Greek Salad"],
    timeframe="next 3 days",
    maximize_savings=True,
    minimize_stores=True
)

recommendation = await agent.run(input_data)
```

### Custom Configuration

```python
from agents.discount_optimizer.factory import AgentFactory
from agents.discount_optimizer.config import Settings

# Create custom settings
custom_settings = Settings(
    agent_temperature=0.9,  # More creative suggestions
    cache_ttl_seconds=7200,  # 2-hour cache
    max_stores_per_recommendation=2,  # Limit to 2 stores
    enable_ai_meal_suggestions=True
)

# Create factory with custom settings
factory = AgentFactory(config=custom_settings)
agent = factory.create_shopping_optimizer_agent()

# Use agent as normal
recommendation = await agent.run(input_data)
```

### Testing with Mocks

```python
from agents.discount_optimizer.factory import create_test_agent
from agents.discount_optimizer.domain.protocols import GeocodingService, DiscountRepository

# Create mock implementations
class MockGeocodingService:
    async def geocode_address(self, address: str):
        return Location(latitude=55.6761, longitude=12.5683)
    
    async def calculate_distance(self, origin, destination):
        return 1.5  # km

class MockDiscountRepository:
    async def fetch_discounts(self, location, radius_km):
        return [
            DiscountItem(
                product_name="Organic Milk",
                store_name="Føtex",
                # ... other fields
            )
        ]
    
    async def health_check(self):
        return True

# Create agent with mocks
agent = create_test_agent(
    geocoding_service=MockGeocodingService(),
    discount_repository=MockDiscountRepository()
)

# Test with mocked dependencies
recommendation = await agent.run(input_data)
```

### Error Handling

```python
from agents.discount_optimizer.domain.exceptions import (
    ValidationError,
    APIError,
    ShoppingOptimizerError
)

try:
    recommendation = await agent.run(input_data)
except ValidationError as e:
    print(f"Invalid input: {e}")
    # Handle validation errors (bad coordinates, invalid dates, etc.)
except APIError as e:
    print(f"API call failed: {e}")
    # Handle external API failures (Salling API, Google Maps, etc.)
except ShoppingOptimizerError as e:
    print(f"Optimization failed: {e}")
    # Handle general optimization errors
```

### Accessing Individual Agents

You can also use individual agents directly:

```python
from agents.discount_optimizer.agents.meal_suggester_agent import (
    MealSuggesterAgent,
    MealSuggestionInput
)

# Create meal suggester agent
meal_suggester = MealSuggesterAgent(api_key="your-api-key")

# Suggest meals
input_data = MealSuggestionInput(
    available_products=["tortillas", "hakket oksekød", "ost", "tomater"],
    num_meals=3,
    meal_types=["lunch", "dinner"]
)

result = await meal_suggester.run(input_data)
print(f"Suggested meals: {result.suggested_meals}")
print(f"Reasoning: {result.reasoning}")
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key_here
SALLING_GROUP_API_KEY=your_salling_api_key_here

# Optional - Environment
ENVIRONMENT=dev  # dev, staging, or production
DEBUG=false

# Optional - Agent Configuration
AGENT_MODEL=gemini-2.0-flash-exp
AGENT_TEMPERATURE=0.7
AGENT_MAX_TOKENS=2000

# Optional - Performance
CACHE_TTL_SECONDS=3600
API_TIMEOUT_SECONDS=30
MAX_CONCURRENT_REQUESTS=10

# Optional - Feature Flags
ENABLE_AI_MEAL_SUGGESTIONS=true
ENABLE_CACHING=true
ENABLE_METRICS=true

# Optional - Logging
LOG_LEVEL=INFO
LOG_FORMAT=console  # console, json, or text

# Optional - Business Logic
DEFAULT_SEARCH_RADIUS_KM=5.0
MAX_STORES_PER_RECOMMENDATION=3
MIN_DISCOUNT_PERCENT=10.0
```

### Configuration in Code

```python
from agents.discount_optimizer.config import settings

# Access configuration
print(f"Using model: {settings.agent_model}")
print(f"Cache TTL: {settings.cache_ttl_seconds} seconds")
print(f"Environment: {settings.environment}")

# Check feature flags
if settings.enable_ai_meal_suggestions:
    print("AI meal suggestions enabled")

# Get agent configuration
agent_config = settings.get_agent_config()
# Returns: {'temperature': 0.7, 'max_output_tokens': 2000, ...}

# Check environment
if settings.is_production():
    print("Running in production mode")
```

## Contributing

This project uses the ADK (Agent Development Kit) framework for agent orchestration. See `.kiro/specs/google-adk-modernization/` for detailed requirements, design, and implementation documentation.

All new code must pass strict type checking before merging. Run `./scripts/type_check.sh` to validate.

### Development Guidelines

1. **Type Safety**: All new code must have 100% type coverage with mypy strict mode
2. **Pydantic Models**: Use Pydantic for all data structures with validation
3. **Dependency Injection**: Inject all dependencies via constructors
4. **Async/Await**: Use async/await for all I/O operations
5. **Error Handling**: Use typed exceptions from `domain.exceptions`
6. **Logging**: Use structured logging with correlation IDs
7. **Testing**: Write tests alongside implementation
8. **Documentation**: Add docstrings with examples for all public methods

## License

This project is for educational and personal use. Ensure compliance with API terms of service:
- Salling Group API: https://developer.sallinggroup.com/terms
- Google Gemini API: https://ai.google.dev/gemini-api/terms

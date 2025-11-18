# Configuration Guide

## Environment Variables

All configuration is managed through environment variables. Create a `.env` file in the project root:

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

## Configuration in Code

The application uses `pydantic-settings` for type-safe configuration management.

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

## API Keys

### Salling Group API (Required)

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

### Google Gemini API (Required)

Gemini 2.5 Pro generates creative meal suggestions based on available products.

1. Visit: https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

**API Details**:
- Model used: gemini-2.5-pro
- Free tier: 60 requests per minute
- Used for: AI meal generation and recipe suggestions

### Redis Caching (Optional)

To enable production-grade caching with Redis:

1.  Set `ENABLE_CACHING=true` in `.env`
2.  Configure Redis URL:
    ```bash
    REDIS_URL=redis://localhost:6379/0
    # Or for password protected:
    REDIS_URL=redis://:password@localhost:6379/0
    ```


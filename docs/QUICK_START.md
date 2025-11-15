# Quick Start Guide

Get up and running with the Shopping Optimizer in 5 minutes.

## Prerequisites

- Python 3.11 or higher
- Google Gemini API key
- Salling Group API key (for Danish grocery data)

## Installation

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd shopping-optimizer

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key_here
SALLING_GROUP_API_KEY=your_salling_api_key_here

# Optional
ENVIRONMENT=dev
LOG_LEVEL=INFO
```

**Get API Keys:**
- **Google Gemini**: https://aistudio.google.com/app/apikey
- **Salling Group**: https://developer.sallinggroup.com/

### 3. Verify Installation

```bash
# Run type checking
./scripts/type_check.sh

# Run tests
python -m pytest

# Start the web server
python app.py
```

Open http://127.0.0.1:8000 in your browser.

## Basic Usage

### Option 1: Web Interface

1. Open http://127.0.0.1:8000
2. Click "Use My Location" or enter coordinates
3. Click "Find Meals"
4. View recommendations

### Option 2: Python API

```python
import asyncio
from agents.discount_optimizer.factory import create_production_agent
from agents.discount_optimizer.agents.shopping_optimizer_agent import ShoppingOptimizerInput

async def main():
    # Create agent
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
    
    # Display results
    print(f"Total savings: {recommendation.total_savings} kr")
    print(f"Stores to visit: {len(recommendation.stores)}")
    for purchase in recommendation.purchases:
        print(f"- {purchase.product_name} at {purchase.store_name}")

# Run
asyncio.run(main())
```

### Option 3: Command Line

```bash
# Run example script
python examples/agent_composition_example.py
```

## Common Tasks

### Run Tests

```bash
# All tests
python -m pytest

# Specific test file
python -m pytest tests/agents/test_shopping_optimizer_agent.py

# With coverage
python -m pytest --cov=agents/discount_optimizer
```

### Type Checking

```bash
# Check all code
./scripts/type_check.sh

# Check specific module
mypy agents/discount_optimizer/domain/
```

### View Logs

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python app.py

# View structured logs
python app.py 2>&1 | jq .
```

### Update Configuration

Edit `.env` file:

```bash
# Agent configuration
AGENT_MODEL=gemini-2.0-flash-exp
AGENT_TEMPERATURE=0.7
AGENT_MAX_TOKENS=2000

# Performance
CACHE_TTL_SECONDS=3600
API_TIMEOUT_SECONDS=30

# Feature flags
ENABLE_AI_MEAL_SUGGESTIONS=true
ENABLE_CACHING=true
```

## Next Steps

### Learn More

- **[API Reference](API_REFERENCE.md)**: Complete API documentation
- **[Architecture Guide](ARCHITECTURE.md)**: System architecture and design patterns
- **[Migration Guide](MIGRATION_GUIDE.md)**: Migrate from legacy code
- **[Examples](../examples/)**: Working code examples

### Explore the Code

```bash
# Domain models (Pydantic)
agents/discount_optimizer/domain/models.py

# Root agent (orchestration)
agents/discount_optimizer/agents/shopping_optimizer_agent.py

# Factory (dependency injection)
agents/discount_optimizer/factory.py

# Configuration
agents/discount_optimizer/config.py
```

### Customize

1. **Add a new agent**: Create in `agents/discount_optimizer/agents/`
2. **Add a new service**: Create in `agents/discount_optimizer/services/`
3. **Add a new repository**: Create in `agents/discount_optimizer/infrastructure/`
4. **Update configuration**: Edit `agents/discount_optimizer/config.py`

### Test Your Changes

```bash
# Run tests
python -m pytest

# Check types
./scripts/type_check.sh

# Run example
python examples/agent_composition_example.py
```

## Troubleshooting

### "No module named 'agents'"

**Solution**: Ensure you're in the project root and virtual environment is activated:
```bash
cd /path/to/shopping-optimizer
source .venv/bin/activate
```

### "GOOGLE_API_KEY is required"

**Solution**: Create `.env` file with your API key:
```bash
echo "GOOGLE_API_KEY=your-key-here" > .env
```

### "No food waste products found"

**Solution**: The Salling API only covers Danish stores. Try Copenhagen coordinates:
```python
latitude=55.6761
longitude=12.5683
```

### Type checking errors

**Solution**: Check mypy configuration in `mypy.ini`. Legacy modules may need:
```ini
[mypy-agents.discount_optimizer.legacy_module]
ignore_errors = True
```

### Import errors

**Solution**: Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

## Getting Help

- **Documentation**: Check [docs/](.) directory
- **Examples**: See [examples/](../examples/) directory
- **Issues**: Check existing issues or create a new one
- **Tests**: Look at test files for usage examples

## Development Workflow

1. **Create feature branch**: `git checkout -b feature/my-feature`
2. **Write code**: Follow type safety guidelines
3. **Add tests**: Write tests alongside implementation
4. **Check types**: Run `./scripts/type_check.sh`
5. **Run tests**: Run `python -m pytest`
6. **Commit**: Use descriptive commit messages
7. **Push**: `git push origin feature/my-feature`
8. **Create PR**: Submit pull request for review

## Best Practices

1. **Always use type hints**: Enable mypy strict mode for new code
2. **Use Pydantic models**: For all data structures
3. **Inject dependencies**: Never instantiate dependencies directly
4. **Write tests**: Test alongside implementation
5. **Use async/await**: For all I/O operations
6. **Log with context**: Use structured logging
7. **Handle errors**: Use typed exceptions
8. **Document code**: Add docstrings with examples

## Resources

- [Google ADK Documentation](https://ai.google.dev/gemini-api/docs/adk)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Async/Await Guide](https://docs.python.org/3/library/asyncio.html)

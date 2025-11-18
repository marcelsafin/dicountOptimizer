# Development Guide

## Local Installation

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

### 2. Run the Application

**⚠️ IMPORTANT**: This application uses async/await throughout. You MUST use an ASGI server (Gunicorn + Uvicorn) to preserve async performance.

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

## Type Checking

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

## Project Structure

```
.
├── agents/
│   └── discount_optimizer/
│       ├── agents/                     # Google ADK Agents
│       ├── services/                   # Business Logic Services
│       ├── infrastructure/             # External API Repositories
│       ├── domain/                     # Domain Models & Protocols
│       ├── factory.py                  # Agent factory (DI)
│       ├── config.py                   # Configuration management
│       └── logging.py                  # Structured logging
├── templates/
│   └── index.html                      # Web UI template
├── static/
│   ├── css/styles.css                  # UI styling
│   └── js/app.js                       # Frontend logic
├── tests/                              # Comprehensive test suite
├── docs/                               # Documentation
├── app.py                              # Flask web server
└── requirements.txt                    # Python dependencies
```

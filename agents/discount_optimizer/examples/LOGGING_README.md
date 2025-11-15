# Structured Logging Guide

This guide explains how to use the structured logging system in the Shopping Optimizer application.

## Overview

The logging system provides:

- **Structured Logging**: All logs are structured with key-value pairs for easy parsing and analysis
- **Correlation IDs**: Track requests across multiple agent calls and services
- **Request IDs**: Track individual HTTP requests
- **Agent Context**: Automatically include which agent is executing
- **Environment Context**: Automatically include deployment environment
- **Multiple Formats**: JSON for production, colorized console for development
- **Integration**: Works seamlessly with Python's standard logging

## Quick Start

### Basic Usage

```python
from agents.discount_optimizer.logging import get_logger

logger = get_logger(__name__)

# Simple log message
logger.info("user_logged_in", user_id=123, username="john")

# Log with multiple fields
logger.info(
    "api_call_completed",
    endpoint="/api/discounts",
    method="GET",
    status_code=200,
    duration_ms=123.45
)
```

### Using Correlation IDs

Correlation IDs help track a request across multiple services and agent calls:

```python
from agents.discount_optimizer.logging import get_logger, set_correlation_id

logger = get_logger(__name__)

# Set correlation ID for the entire request
correlation_id = set_correlation_id("req-abc-123")

logger.info("request_started")
logger.info("processing_step_1")
logger.info("processing_step_2")
logger.info("request_completed")

# All logs will include: correlation_id=req-abc-123
```

### Using LogContext Manager

The `LogContext` context manager automatically sets and clears context:

```python
from agents.discount_optimizer.logging import get_logger, LogContext

logger = get_logger(__name__)

with LogContext(
    correlation_id="req-xyz-789",
    request_id="http-001",
    agent="meal_suggester"
):
    logger.info("agent_started")
    logger.info("processing")
    logger.info("agent_completed")
    # All logs include correlation_id, request_id, and agent
```

### Nested Contexts

Contexts can be nested for sub-agent calls:

```python
from agents.discount_optimizer.logging import get_logger, LogContext

logger = get_logger(__name__)

# Main agent context
with LogContext(correlation_id="req-001", agent="shopping_optimizer"):
    logger.info("optimization_started")
    
    # Sub-agent context
    with LogContext(agent="meal_suggester"):
        logger.info("suggesting_meals")
    
    # Back to main agent context
    logger.info("optimization_completed")
```

### Async Functions

The logging system works seamlessly with async functions:

```python
from agents.discount_optimizer.logging import get_logger, LogContext

logger = get_logger(__name__)

async def process_request():
    with LogContext(correlation_id="async-001"):
        logger.info("async_started")
        await some_async_operation()
        logger.info("async_completed")
```

### Error Logging

Log errors with full context and tracebacks:

```python
from agents.discount_optimizer.logging import get_logger, LogContext

logger = get_logger(__name__)

with LogContext(correlation_id="error-001", agent="discount_matcher"):
    try:
        result = fetch_discounts()
    except Exception as e:
        logger.error(
            "api_error",
            error_type=type(e).__name__,
            error_message=str(e),
            api="salling",
            retry_count=0,
            exc_info=True  # Include full traceback
        )
```

### Performance Logging

Track performance metrics:

```python
import time
from agents.discount_optimizer.logging import get_logger, LogContext

logger = get_logger(__name__)

with LogContext(correlation_id="perf-001"):
    start_time = time.time()
    
    logger.info("operation_started", operation="optimize_shopping")
    
    # Do work...
    
    duration_ms = (time.time() - start_time) * 1000
    
    logger.info(
        "operation_completed",
        operation="optimize_shopping",
        duration_ms=duration_ms,
        items_processed=25,
        stores_checked=5
    )
```

## Configuration

Logging is configured via environment variables in `.env`:

```bash
# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log format (json, console, text)
# - json: Machine-readable JSON for production
# - console: Human-readable with colors for development
# - text: Plain key-value pairs
LOG_FORMAT=console

# Optional: Log to file
LOG_FILE=logs/app.log
LOG_MAX_BYTES=10485760  # 10 MB
LOG_BACKUP_COUNT=5

# Environment (affects log output)
ENVIRONMENT=dev  # dev, staging, production

# Enable/disable structured logging
ENABLE_STRUCTURED_LOGGING=true
```

## Log Formats

### Console Format (Development)

Colorized, human-readable output:

```
2025-11-14T23:49:19.657330+00:00 [info] user_action [__main__] 
    action=login user_id=12345 ip_address=192.168.1.1 success=True
```

### JSON Format (Production)

Machine-readable JSON for log aggregation:

```json
{
  "timestamp": "2025-11-14T23:49:19.657330+00:00",
  "level": "info",
  "event": "user_action",
  "logger": "__main__",
  "correlation_id": "req-abc-123",
  "agent": "meal_suggester",
  "environment": "production",
  "action": "login",
  "user_id": 12345,
  "ip_address": "192.168.1.1",
  "success": true
}
```

## Best Practices

### 1. Use Descriptive Event Names

```python
# Good
logger.info("user_login_successful", user_id=123)
logger.info("discount_fetch_completed", store_count=5)

# Avoid
logger.info("success")
logger.info("done")
```

### 2. Include Relevant Context

```python
# Good
logger.info(
    "api_call",
    endpoint="/api/discounts",
    method="GET",
    status_code=200,
    duration_ms=123.45,
    items_returned=25
)

# Avoid
logger.info("API call successful")
```

### 3. Use Correlation IDs for Request Tracing

Always set a correlation ID at the start of a request:

```python
with LogContext(correlation_id=generate_correlation_id()):
    # All logs in this context will share the correlation ID
    process_request()
```

### 4. Set Agent Context

When executing agents, set the agent context:

```python
with LogContext(agent="meal_suggester"):
    # All logs will include agent=meal_suggester
    result = agent.run(input_data)
```

### 5. Log Performance Metrics

Track timing for important operations:

```python
start = time.time()
result = expensive_operation()
duration_ms = (time.time() - start) * 1000

logger.info(
    "operation_completed",
    operation="expensive_operation",
    duration_ms=duration_ms,
    result_count=len(result)
)
```

### 6. Log Errors with Context

Always include error context and use `exc_info=True` for tracebacks:

```python
try:
    result = risky_operation()
except Exception as e:
    logger.error(
        "operation_failed",
        operation="risky_operation",
        error_type=type(e).__name__,
        error_message=str(e),
        exc_info=True
    )
```

## API Reference

### Functions

#### `get_logger(name: str | None = None) -> BoundLogger`

Get a structured logger instance.

**Parameters:**
- `name`: Logger name (typically `__name__`)

**Returns:**
- Configured structlog logger

#### `set_correlation_id(correlation_id: str | None = None) -> str`

Set correlation ID for the current context.

**Parameters:**
- `correlation_id`: Optional correlation ID. If None, generates a new one.

**Returns:**
- The correlation ID that was set

#### `get_correlation_id() -> str | None`

Get the current correlation ID.

#### `set_request_id(request_id: str | None = None) -> str`

Set request ID for the current context.

#### `get_request_id() -> str | None`

Get the current request ID.

#### `set_agent_context(agent_name: str) -> None`

Set the current agent context for logging.

#### `get_agent_context() -> str | None`

Get the current agent context.

#### `clear_context() -> None`

Clear all context variables.

#### `generate_correlation_id() -> str`

Generate a new correlation ID (UUID).

### Classes

#### `LogContext`

Context manager for setting logging context.

**Parameters:**
- `correlation_id`: Correlation ID for distributed tracing
- `request_id`: Request ID for HTTP request tracking
- `agent`: Agent name for agent execution tracking
- `**extra_context`: Additional context fields

**Example:**
```python
with LogContext(correlation_id="req-001", agent="meal_suggester"):
    logger.info("processing")
```

## Examples

See `agents/discount_optimizer/examples/logging_example.py` for complete examples:

```bash
PYTHONPATH=. python3 agents/discount_optimizer/examples/logging_example.py
```

## Integration with Existing Code

To integrate structured logging into existing code:

1. Import the logger:
   ```python
   from agents.discount_optimizer.logging import get_logger
   logger = get_logger(__name__)
   ```

2. Replace print statements with logger calls:
   ```python
   # Before
   print(f"Processing user {user_id}")
   
   # After
   logger.info("processing_user", user_id=user_id)
   ```

3. Add correlation IDs to request handlers:
   ```python
   @app.route('/optimize')
   def optimize():
       with LogContext(correlation_id=generate_correlation_id()):
           result = optimize_shopping(request.json)
           return jsonify(result)
   ```

4. Add agent context to agent execution:
   ```python
   with LogContext(agent="meal_suggester"):
       result = meal_suggester.run(input_data)
   ```

## Troubleshooting

### Logs not appearing

Check that `ENABLE_STRUCTURED_LOGGING=true` in your `.env` file.

### Wrong log level

Set `LOG_LEVEL` in `.env` to the desired level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

### Want JSON output

Set `LOG_FORMAT=json` in `.env` for production-ready JSON logs.

### Correlation IDs not showing

Make sure you're setting the correlation ID:
```python
with LogContext(correlation_id="your-id"):
    logger.info("message")
```

## Further Reading

- [structlog Documentation](https://www.structlog.org/)
- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [Distributed Tracing Best Practices](https://opentelemetry.io/docs/concepts/observability-primer/)

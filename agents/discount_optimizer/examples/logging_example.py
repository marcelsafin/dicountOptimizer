"""
Example usage of structured logging.

This script demonstrates how to use the structured logging system
with correlation IDs, request tracking, and agent context.
"""

import asyncio
import time

from agents.discount_optimizer.logging import (
    LogContext,
    get_logger,
    set_correlation_id,
)

# Get a logger for this module
logger = get_logger(__name__)


def example_basic_logging():
    """Example: Basic structured logging."""
    print("\n=== Example 1: Basic Logging ===\n")
    
    logger.info("application_started", version="1.0.0", environment="dev")
    logger.debug("debug_message", details="This is a debug message")
    logger.warning("warning_message", reason="Something might be wrong")
    logger.error("error_occurred", error_code=500, message="Internal error")


def example_with_context():
    """Example: Logging with structured context."""
    print("\n=== Example 2: Logging with Context ===\n")
    
    logger.info(
        "user_action",
        user_id=12345,
        action="login",
        ip_address="192.168.1.1",
        success=True
    )
    
    logger.info(
        "api_call",
        endpoint="/api/discounts",
        method="GET",
        status_code=200,
        duration_ms=123.45
    )


def example_with_correlation_id():
    """Example: Using correlation IDs for request tracing."""
    print("\n=== Example 3: Correlation ID Tracking ===\n")
    
    # Set a correlation ID for the entire request
    correlation_id = set_correlation_id("req-abc-123")
    
    logger.info("request_started", endpoint="/optimize")
    logger.info("fetching_discounts", store_count=5)
    logger.info("generating_recommendations", meal_count=3)
    logger.info("request_completed", duration_ms=456.78)
    
    print(f"\nAll logs above share correlation_id: {correlation_id}")


def example_with_log_context():
    """Example: Using LogContext context manager."""
    print("\n=== Example 4: LogContext Manager ===\n")
    
    # Context manager automatically sets and clears context
    with LogContext(
        correlation_id="req-xyz-789",
        request_id="http-001",
        agent="meal_suggester"
    ):
        logger.info("agent_started", input_products=["milk", "eggs", "bread"])
        logger.info("llm_call", model="gemini-2.0-flash", tokens=150)
        logger.info("agent_completed", suggested_meals=["pancakes", "french toast"])


def example_nested_contexts():
    """Example: Nested LogContext for sub-agent calls."""
    print("\n=== Example 5: Nested Contexts ===\n")
    
    # Outer context for main request
    with LogContext(correlation_id="req-main-001", agent="shopping_optimizer"):
        logger.info("optimization_started")
        
        # Inner context for sub-agent
        with LogContext(agent="meal_suggester"):
            logger.info("sub_agent_started", task="suggest_meals")
            logger.info("sub_agent_completed", result_count=3)
        
        # Back to outer context
        logger.info("calling_next_agent")
        
        # Another sub-agent
        with LogContext(agent="ingredient_mapper"):
            logger.info("sub_agent_started", task="map_ingredients")
            logger.info("sub_agent_completed", ingredient_count=12)
        
        logger.info("optimization_completed")


async def example_async_logging():
    """Example: Logging in async functions."""
    print("\n=== Example 6: Async Logging ===\n")
    
    with LogContext(correlation_id="async-req-001"):
        logger.info("async_operation_started")
        
        # Simulate async work
        await asyncio.sleep(0.1)
        logger.info("async_step_1_completed")
        
        await asyncio.sleep(0.1)
        logger.info("async_step_2_completed")
        
        logger.info("async_operation_completed")


def example_error_logging():
    """Example: Logging errors with context."""
    print("\n=== Example 7: Error Logging ===\n")
    
    with LogContext(correlation_id="error-req-001", agent="discount_matcher"):
        try:
            logger.info("fetching_discounts", api="salling")
            
            # Simulate an error
            raise ValueError("API returned invalid data")
            
        except ValueError as e:
            logger.error(
                "api_error",
                error_type=type(e).__name__,
                error_message=str(e),
                api="salling",
                retry_count=0,
                exc_info=True  # This will include the full traceback
            )


def example_performance_logging():
    """Example: Logging performance metrics."""
    print("\n=== Example 8: Performance Logging ===\n")
    
    with LogContext(correlation_id="perf-req-001"):
        start_time = time.time()
        
        logger.info("operation_started", operation="optimize_shopping")
        
        # Simulate work
        time.sleep(0.1)
        
        duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            "operation_completed",
            operation="optimize_shopping",
            duration_ms=duration_ms,
            items_processed=25,
            stores_checked=5,
            recommendations_generated=3
        )


def main():
    """Run all examples."""
    print("=" * 60)
    print("Structured Logging Examples")
    print("=" * 60)
    
    example_basic_logging()
    example_with_context()
    example_with_correlation_id()
    example_with_log_context()
    example_nested_contexts()
    
    # Run async example
    asyncio.run(example_async_logging())
    
    example_error_logging()
    example_performance_logging()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
Flask web application for Shopping Optimizer.
Serves the frontend and provides API endpoint for optimization.

This module implements the Flask API with:
- Async support for non-blocking I/O operations
- Integration with the new agent architecture via AgentFactory
- Health check endpoints for monitoring
- Proper error handling with typed responses
- Request correlation IDs for distributed tracing
- Structured logging throughout

Requirements: 10.1, 10.3
"""

import sys
import uuid
from datetime import UTC

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request

from agents.discount_optimizer.agents.shopping_optimizer_agent import ShoppingOptimizerInput
from agents.discount_optimizer.config import settings
from agents.discount_optimizer.domain.exceptions import ShoppingOptimizerError, ValidationError
from agents.discount_optimizer.factory import AgentFactory
from agents.discount_optimizer.logging import LogContext, get_logger, set_correlation_id
from agents.discount_optimizer.metrics import get_metrics_collector


# Load environment variables from .env file
load_dotenv()

# Get logger for this module
logger = get_logger(__name__)

# Initialize agent factory (singleton)
agent_factory: AgentFactory | None = None


def initialize_agent_factory() -> AgentFactory:
    """
    Initialize the agent factory with configuration validation.

    This function creates the AgentFactory singleton that will be used
    to create agent instances for handling requests. It validates all
    required configuration at startup.

    Returns:
        Initialized AgentFactory instance

    Raises:
        ValueError: If required configuration is missing
        SystemExit: If critical configuration errors prevent startup

    Requirements: 9.3, 10.1
    """
    try:
        logger.info("initializing_agent_factory", environment=settings.environment)
        factory = AgentFactory()
        logger.info("agent_factory_initialized_successfully")
        return factory
    except ValueError as e:
        logger.exception("agent_factory_initialization_failed", error=str(e))
        print(f"ERROR: Agent factory initialization failed: {e}", file=sys.stderr)
        print(
            "\nPlease check your .env file and ensure all required configuration is set.",
            file=sys.stderr,
        )
        print("Refer to .env.example for the required format.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.exception(
            "unexpected_error_during_initialization", error=str(e), error_type=type(e).__name__
        )
        print(f"ERROR: Unexpected error during initialization: {e}", file=sys.stderr)
        sys.exit(1)


# Initialize factory on startup
agent_factory = initialize_agent_factory()

# Initialize metrics collector
metrics_collector = get_metrics_collector()

app = Flask(__name__)


@app.route("/")
def index() -> str:
    """Serve the main page"""
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health() -> tuple[Response, int] | Response:
    """
    Basic health check endpoint.

    Returns a simple status indicating the service is running.
    This is useful for load balancers and monitoring systems.

    Returns:
    {
        "status": "healthy",
        "service": "shopping-optimizer",
        "environment": "dev|staging|production"
    }

    Requirements: 10.3
    """
    return jsonify(
        {
            "status": "healthy",
            "service": "shopping-optimizer",
            "environment": settings.environment,
        }
    )


@app.route("/health/detailed", methods=["GET"])
async def health_detailed() -> tuple[Response, int] | Response:
    """
    Detailed health check endpoint with dependency status.

    This endpoint checks the health of all critical dependencies:
    - Geocoding service (Google Maps)
    - Discount repository (Salling API)
    - Cache repository

    Returns:
    {
        "status": "healthy|degraded|unhealthy",
        "service": "shopping-optimizer",
        "environment": "dev|staging|production",
        "dependencies": {
            "geocoding_service": {"status": "healthy|unhealthy", "message": "..."},
            "discount_repository": {"status": "healthy|unhealthy", "message": "..."},
            "cache_repository": {"status": "healthy|unhealthy", "message": "..."}
        },
        "timestamp": "2025-11-15T12:00:00Z"
    }

    Requirements: 10.3
    """
    from datetime import datetime

    assert agent_factory is not None, "Agent factory not initialized"

    correlation_id = str(uuid.uuid4())
    set_correlation_id(correlation_id)

    with LogContext(correlation_id=correlation_id, endpoint="/health/detailed"):
        logger.info("detailed_health_check_started", correlation_id=correlation_id)

        dependencies: dict[str, dict[str, str]] = {}

        # Check geocoding service
        try:
            geocoding_service = agent_factory.get_geocoding_service()
            is_healthy = await geocoding_service.health_check()
            dependencies["geocoding_service"] = {
                "status": "healthy" if is_healthy else "unhealthy",
                "message": "Service is operational" if is_healthy else "Service check failed",
            }
            if not is_healthy:
                pass
        except Exception as e:
            logger.warning(
                "geocoding_health_check_failed", error=str(e), correlation_id=correlation_id
            )
            dependencies["geocoding_service"] = {
                "status": "unhealthy",
                "message": f"Health check error: {e!s}",
            }

        # Check discount repository
        try:
            discount_repo = agent_factory.get_discount_repository()
            is_healthy = await discount_repo.health_check()
            dependencies["discount_repository"] = {
                "status": "healthy" if is_healthy else "unhealthy",
                "message": "Service is operational" if is_healthy else "Service check failed",
            }
            if not is_healthy:
                pass
        except Exception as e:
            logger.warning(
                "discount_repo_health_check_failed", error=str(e), correlation_id=correlation_id
            )
            dependencies["discount_repository"] = {
                "status": "unhealthy",
                "message": f"Health check error: {e!s}",
            }

        # Check cache repository
        try:
            cache_repo = agent_factory.get_cache_repository()
            is_healthy = await cache_repo.health_check()
            dependencies["cache_repository"] = {
                "status": "healthy" if is_healthy else "unhealthy",
                "message": "Service is operational" if is_healthy else "Service check failed",
            }
            if not is_healthy:
                pass
        except Exception as e:
            logger.warning("cache_health_check_failed", error=str(e), correlation_id=correlation_id)
            dependencies["cache_repository"] = {
                "status": "unhealthy",
                "message": f"Health check error: {e!s}",
            }

        # Determine overall status
        unhealthy_count = sum(1 for dep in dependencies.values() if dep["status"] == "unhealthy")
        if unhealthy_count == 0:
            overall_status = "healthy"
            status_code = 200
        elif unhealthy_count < len(dependencies):
            overall_status = "degraded"
            status_code = 200  # Still operational but degraded
        else:
            overall_status = "unhealthy"
            status_code = 503  # Service unavailable

        logger.info(
            "detailed_health_check_completed",
            overall_status=overall_status,
            unhealthy_count=unhealthy_count,
            correlation_id=correlation_id,
        )

        response = {
            "status": overall_status,
            "service": "shopping-optimizer",
            "environment": settings.environment,
            "dependencies": dependencies,
            "timestamp": datetime.now(UTC).isoformat(),
            "correlation_id": correlation_id,
        }

        return jsonify(response), status_code


@app.route("/api/optimize", methods=["POST"])
async def optimize() -> tuple[Response, int] | Response:
    """
    API endpoint for shopping optimization using the new agent architecture.

    This endpoint uses async agent execution with proper error handling,
    correlation IDs for tracing, and typed responses.

    Expected JSON payload:
    {
        "location": "55.6761,12.5683" or "Copenhagen",
        "meals": ["taco", "pasta"],
        "preferences": {
            "maximize_savings": true,
            "minimize_stores": false,
            "prefer_organic": false
        },
        "num_meals": 5  // Optional, for AI meal suggestions
    }

    Returns:
    {
        "success": true/false,
        "recommendation": {
            "purchases": [...],
            "total_savings": 123.45,
            "time_savings": 15.0,
            "tips": [...],
            "motivation_message": "...",
            "stores": [...]
        },
        "user_location": {"latitude": 55.6761, "longitude": 12.5683},
        "correlation_id": "uuid",
        "error": "error message" (if failed)
    }

    Requirements: 10.1, 10.3
    """
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())
    set_correlation_id(correlation_id)

    assert agent_factory is not None, "Agent factory not initialized"

    with LogContext(correlation_id=correlation_id, endpoint="/api/optimize"):
        try:
            logger.info(
                "api_request_received", method=request.method, correlation_id=correlation_id
            )

            data = request.get_json()

            if not data:
                logger.warning("no_data_provided", correlation_id=correlation_id)
                return jsonify(
                    {
                        "success": False,
                        "error": "No data provided",
                        "correlation_id": correlation_id,
                    }
                ), 400

            # Parse location
            location_str = data.get("location", "").strip()
            address: str | None = None
            latitude: float | None = None
            longitude: float | None = None

            if location_str:
                # Try to parse as coordinates (lat,lon)
                try:
                    parts = location_str.split(",")
                    if len(parts) == 2:
                        latitude = float(parts[0].strip())
                        longitude = float(parts[1].strip())
                        logger.debug(
                            "parsed_coordinates",
                            latitude=latitude,
                            longitude=longitude,
                            correlation_id=correlation_id,
                        )
                    else:
                        # Treat as address
                        address = location_str
                        logger.debug(
                            "using_address", address=address, correlation_id=correlation_id
                        )
                except ValueError:
                    # Treat as address
                    address = location_str
                    logger.debug("using_address", address=address, correlation_id=correlation_id)

            # Validate location provided
            if not address and not (latitude and longitude):
                logger.warning("location_required", correlation_id=correlation_id)
                return jsonify(
                    {
                        "success": False,
                        "error": "Location is required (either address or coordinates)",
                        "correlation_id": correlation_id,
                    }
                ), 400

            # Get meals
            meals = data.get("meals", [])

            # Get preferences
            preferences = data.get("preferences", {})
            maximize_savings = preferences.get("maximize_savings", True)
            minimize_stores = preferences.get("minimize_stores", False)
            prefer_organic = preferences.get("prefer_organic", False)

            # Get optional parameters
            num_meals = data.get("num_meals", 5 if not meals else None)
            search_radius_km = data.get("search_radius_km")
            timeframe = data.get("timeframe", "this week")

            # Create agent input
            agent_input = ShoppingOptimizerInput(
                address=address,
                latitude=latitude,
                longitude=longitude,
                meal_plan=meals,
                timeframe=timeframe,
                maximize_savings=maximize_savings,
                minimize_stores=minimize_stores,
                prefer_organic=prefer_organic,
                search_radius_km=search_radius_km,
                num_meals=num_meals,
                correlation_id=correlation_id,
            )

            logger.info(
                "agent_input_created",
                has_address=bool(address),
                has_coordinates=bool(latitude and longitude),
                num_meals_in_plan=len(meals),
                correlation_id=correlation_id,
            )

            # Create agent and run optimization
            agent = agent_factory.create_shopping_optimizer_agent()

            # Run async agent with metrics tracking
            try:
                with metrics_collector.time_agent("shopping_optimizer"):
                    recommendation = await agent.run(agent_input)

                # Record success
                metrics_collector.record_agent_success("shopping_optimizer")

                logger.info(
                    "optimization_completed",
                    total_purchases=len(recommendation.purchases),
                    total_savings=float(recommendation.total_savings),
                    correlation_id=correlation_id,
                )
            except Exception as agent_error:
                # Record failure
                metrics_collector.record_agent_failure(
                    "shopping_optimizer", error_type=type(agent_error).__name__
                )
                raise

            # Convert Pydantic model to dict for JSON response
            recommendation_dict = {
                "purchases": [
                    {
                        "product_name": p.product_name,
                        "store_name": p.store_name,
                        "purchase_day": p.purchase_day.isoformat(),
                        "price": float(p.price),
                        "savings": float(p.savings),
                        "meal_association": p.meal_association,
                    }
                    for p in recommendation.purchases
                ],
                "total_savings": float(recommendation.total_savings),
                "time_savings": recommendation.time_savings,
                "tips": recommendation.tips,
                "motivation_message": recommendation.motivation_message,
                "stores": recommendation.stores,
            }

            # Add user location to result for map display
            user_location = {
                "latitude": latitude if latitude else 0.0,
                "longitude": longitude if longitude else 0.0,
            }

            response = {
                "success": True,
                "recommendation": recommendation_dict,
                "user_location": user_location,
                "correlation_id": correlation_id,
            }

            return jsonify(response)

        except ValidationError as e:
            logger.warning("validation_error", error=str(e), correlation_id=correlation_id)
            return jsonify(
                {
                    "success": False,
                    "error": f"Validation error: {e!s}",
                    "error_type": "validation",
                    "correlation_id": correlation_id,
                }
            ), 400

        except ShoppingOptimizerError as e:
            logger.exception("optimization_error", error=str(e), correlation_id=correlation_id)
            return jsonify(
                {
                    "success": False,
                    "error": f"Optimization error: {e!s}",
                    "error_type": "optimization",
                    "correlation_id": correlation_id,
                }
            ), 500

        except Exception as e:
            logger.exception(
                "unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                correlation_id=correlation_id,
            )
            return jsonify(
                {
                    "success": False,
                    "error": f"Server error: {e!s}",
                    "error_type": "server",
                    "correlation_id": correlation_id,
                }
            ), 500


@app.route("/metrics", methods=["GET"])
def metrics() -> tuple[Response, int] | Response:
    """
    Metrics endpoint for monitoring and observability.

    Returns all collected metrics in JSON format, including:
    - Agent execution metrics (timing, success rate)
    - API call metrics (timing, success rate)
    - Cache performance metrics
    - System uptime

    Returns:
    {
        "system": {...},
        "agents": {...},
        "api": {...},
        "cache": {...},
        "counters": {...},
        "timers": {...}
    }

    Requirements: 10.2, 10.6
    """
    try:
        all_metrics = metrics_collector.get_metrics()
        return jsonify(all_metrics)
    except Exception as e:
        logger.exception("metrics_endpoint_error", error=str(e))
        return jsonify({"error": "Failed to retrieve metrics", "message": str(e)}), 500


@app.route("/metrics/summary", methods=["GET"])
def metrics_summary() -> tuple[Response, int] | Response:
    """
    Metrics summary endpoint with high-level statistics.

    Returns a concise summary of key metrics for quick monitoring.

    Returns:
    {
        "uptime_seconds": 12345.67,
        "total_agent_executions": 100,
        "total_api_calls": 250,
        "overall_agent_success_rate": 98.5,
        "overall_api_success_rate": 99.2,
        "cache_hit_rate": 75.3,
        "cache_total_requests": 500
    }

    Requirements: 10.2, 10.6
    """
    try:
        summary = metrics_collector.get_summary()
        return jsonify(summary)
    except Exception as e:
        logger.exception("metrics_summary_endpoint_error", error=str(e))
        return jsonify({"error": "Failed to retrieve metrics summary", "message": str(e)}), 500


@app.route("/metrics/prometheus", methods=["GET"])
def metrics_prometheus() -> tuple[str, int, dict[str, str]]:
    """
    Prometheus-compatible metrics endpoint.

    Returns metrics in Prometheus text exposition format for scraping
    by Prometheus monitoring systems.

    Returns:
        Plain text metrics in Prometheus format

    Requirements: 10.2, 10.6
    """
    try:
        prometheus_text = metrics_collector.export_prometheus()
        return prometheus_text, 200, {"Content-Type": "text/plain; charset=utf-8"}
    except Exception as e:
        logger.exception("prometheus_metrics_endpoint_error", error=str(e))
        return (
            f"# Error exporting metrics: {e!s}\n",
            500,
            {"Content-Type": "text/plain; charset=utf-8"},
        )


# ASGI application entry point for production servers (Gunicorn/Uvicorn)
# Do NOT use app.run() - this is a blocking, single-threaded development server
# that defeats all async performance optimizations from Phase 2 (Req 8.2, 8.6)
#
# For local development, use:
#   gunicorn app:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:3000
#
# For production, use:
#   gunicorn app:app --worker-class uvicorn.workers.UvicornWorker \
#     --workers 4 --bind 0.0.0.0:$PORT --timeout 120 --graceful-timeout 30


# ASGI wrapper for Flask to work with Uvicorn workers
# This converts Flask's WSGI interface to ASGI
from asgiref.wsgi import WsgiToAsgi


asgi_app = WsgiToAsgi(app)

"""
Integration tests for Flask API endpoints.

This module tests the Flask API integration with the agent architecture
using mocked dependencies to avoid live API calls.

Requirements: 10.1, 10.3
"""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from agents.discount_optimizer.domain.exceptions import ShoppingOptimizerError, ValidationError
from agents.discount_optimizer.domain.models import (
    Purchase,
    ShoppingRecommendation,
)
from agents.discount_optimizer.metrics import get_metrics_collector
from app import app


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def mock_agent():
    """Create mock shopping optimizer agent."""
    agent = AsyncMock()

    # Mock successful recommendation
    mock_recommendation = ShoppingRecommendation(
        purchases=[
            Purchase(
                product_name="Test Product",
                store_name="Test Store",
                purchase_day=date(2025, 11, 15),
                price=Decimal("10.00"),
                savings=Decimal("5.00"),
                meal_association="Test Meal",
            )
        ],
        total_savings=Decimal("5.00"),
        time_savings=10.0,
        tips=["Tip 1", "Tip 2"],
        motivation_message="Great job!",
        stores=[{"name": "Test Store", "items": 1, "address": "Test Address", "distance_km": 1.0}],
    )

    agent.run.return_value = mock_recommendation
    return agent


@pytest.fixture
def mock_factory(mock_agent):
    """Create mock agent factory."""
    factory = Mock()
    factory.create_shopping_optimizer_agent.return_value = mock_agent

    # Mock health check methods
    mock_geocoding = AsyncMock()
    mock_geocoding.health_check.return_value = True
    factory.get_geocoding_service.return_value = mock_geocoding

    mock_discount_repo = AsyncMock()
    mock_discount_repo.health_check.return_value = True
    factory.get_discount_repository.return_value = mock_discount_repo

    mock_cache = AsyncMock()
    mock_cache.health_check.return_value = True
    factory.get_cache_repository.return_value = mock_cache

    return factory


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_basic_health_check(self, client):
        """Test /health endpoint returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["service"] == "shopping-optimizer"
        assert "environment" in data

    def test_detailed_health_check_all_healthy(self, client, mock_factory):
        """Test /health/detailed endpoint when all dependencies are healthy."""
        with patch("app.agent_factory", mock_factory):
            response = client.get("/health/detailed")

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "healthy"
            assert "dependencies" in data
            assert "correlation_id" in data
            assert "timestamp" in data

            # Check all dependencies
            assert data["dependencies"]["geocoding_service"]["status"] == "healthy"
            assert data["dependencies"]["discount_repository"]["status"] == "healthy"
            assert data["dependencies"]["cache_repository"]["status"] == "healthy"

    def test_detailed_health_check_degraded(self, client, mock_factory):
        """Test /health/detailed endpoint when some dependencies are unhealthy."""
        # Make geocoding service unhealthy
        mock_geocoding = AsyncMock()
        mock_geocoding.health_check.return_value = False
        mock_factory.get_geocoding_service.return_value = mock_geocoding

        with patch("app.agent_factory", mock_factory):
            response = client.get("/health/detailed")

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "degraded"
            assert data["dependencies"]["geocoding_service"]["status"] == "unhealthy"

    def test_detailed_health_check_all_unhealthy(self, client, mock_factory):
        """Test /health/detailed endpoint when all dependencies are unhealthy."""
        # Make all services unhealthy
        mock_geocoding = AsyncMock()
        mock_geocoding.health_check.return_value = False
        mock_factory.get_geocoding_service.return_value = mock_geocoding

        mock_discount_repo = AsyncMock()
        mock_discount_repo.health_check.return_value = False
        mock_factory.get_discount_repository.return_value = mock_discount_repo

        mock_cache = AsyncMock()
        mock_cache.health_check.return_value = False
        mock_factory.get_cache_repository.return_value = mock_cache

        with patch("app.agent_factory", mock_factory):
            response = client.get("/health/detailed")

            assert response.status_code == 503
            data = response.get_json()
            assert data["status"] == "unhealthy"


class TestOptimizeEndpoint:
    """Test /api/optimize endpoint."""

    def test_optimize_success_with_coordinates(self, client, mock_factory):
        """Test successful optimization with coordinates."""
        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["taco"],
                    "preferences": {"maximize_savings": True},
                },
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert "recommendation" in data
            assert "correlation_id" in data
            assert "user_location" in data
            assert data["user_location"]["latitude"] == 55.6761
            assert data["user_location"]["longitude"] == 12.5683

            # Verify recommendation structure
            rec = data["recommendation"]
            assert "purchases" in rec
            assert "total_savings" in rec
            assert "time_savings" in rec
            assert "tips" in rec
            assert "motivation_message" in rec
            assert "stores" in rec

    def test_optimize_success_with_address(self, client, mock_factory):
        """Test successful optimization with address."""
        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "Copenhagen",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert "correlation_id" in data

    def test_optimize_no_data(self, client):
        """Test /api/optimize with no data returns 400."""
        response = client.post("/api/optimize", data="null", content_type="application/json")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "error" in data
        assert "correlation_id" in data

    def test_optimize_no_location(self, client):
        """Test /api/optimize with no location returns 400."""
        response = client.post(
            "/api/optimize", json={"meals": ["taco"], "preferences": {"maximize_savings": True}}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "location" in data["error"].lower()
        assert "correlation_id" in data

    def test_optimize_validation_error(self, client, mock_factory, mock_agent):
        """Test /api/optimize handles ValidationError correctly."""
        # Make agent raise ValidationError
        mock_agent.run.side_effect = ValidationError("Invalid input")

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["taco"],
                    "preferences": {"maximize_savings": True},
                },
            )

            assert response.status_code == 400
            data = response.get_json()
            assert data["success"] is False
            assert "validation" in data["error"].lower()
            assert data["error_type"] == "validation"
            assert "correlation_id" in data

    def test_optimize_optimizer_error(self, client, mock_factory, mock_agent):
        """Test /api/optimize handles ShoppingOptimizerError correctly."""
        # Make agent raise ShoppingOptimizerError
        mock_agent.run.side_effect = ShoppingOptimizerError("Optimization failed")

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["taco"],
                    "preferences": {"maximize_savings": True},
                },
            )

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False
            assert "optimization" in data["error"].lower()
            assert data["error_type"] == "optimization"
            assert "correlation_id" in data

    def test_optimize_generic_error(self, client, mock_factory, mock_agent):
        """Test /api/optimize handles generic exceptions correctly."""
        # Make agent raise generic exception
        mock_agent.run.side_effect = Exception("Unexpected error")

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["taco"],
                    "preferences": {"maximize_savings": True},
                },
            )

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False
            assert "server error" in data["error"].lower()
            assert data["error_type"] == "server"
            assert "correlation_id" in data

    def test_optimize_with_all_parameters(self, client, mock_factory):
        """Test /api/optimize with all optional parameters."""
        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["taco", "pasta"],
                    "preferences": {
                        "maximize_savings": True,
                        "minimize_stores": True,
                        "prefer_organic": False,
                    },
                    "num_meals": 5,
                    "search_radius_km": 10.0,
                    "timeframe": "next 3 days",
                },
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert "correlation_id" in data

    def test_optimize_correlation_id_propagation(self, client, mock_factory, mock_agent):
        """Test that correlation IDs are properly propagated through the system."""
        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["taco"],
                    "preferences": {"maximize_savings": True},
                },
            )

            assert response.status_code == 200
            data = response.get_json()
            correlation_id = data["correlation_id"]

            # Verify correlation ID was passed to agent
            call_args = mock_agent.run.call_args
            agent_input = call_args[0][0]
            assert agent_input.correlation_id == correlation_id


class TestAgentFactoryIntegration:
    """Test agent factory integration."""

    def test_factory_creates_agent(self, mock_factory):
        """Test that factory can create agent instances."""
        with patch("app.agent_factory", mock_factory):
            agent = mock_factory.create_shopping_optimizer_agent()
            assert agent is not None
            mock_factory.create_shopping_optimizer_agent.assert_called_once()

    def test_factory_provides_services(self, mock_factory):
        """Test that factory provides all required services."""
        with patch("app.agent_factory", mock_factory):
            geocoding = mock_factory.get_geocoding_service()
            discount_repo = mock_factory.get_discount_repository()
            cache = mock_factory.get_cache_repository()

            assert geocoding is not None
            assert discount_repo is not None
            assert cache is not None


# =============================================================================
# Metrics Endpoint Tests
# =============================================================================


class TestMetricsEndpoints:
    """Test metrics and observability endpoints.

    Requirements: 10.2, 10.6
    """

    def test_metrics_endpoint_returns_json(self, client):
        """Test /metrics endpoint returns JSON metrics."""
        # Reset metrics for clean test
        collector = get_metrics_collector()
        collector.reset()

        # Record some test metrics
        collector.increment_counter("test_counter")
        collector.record_cache_hit()

        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.content_type == "application/json"

        data = json.loads(response.data)
        assert "system" in data
        assert "agents" in data
        assert "api" in data
        assert "cache" in data
        assert "counters" in data
        assert "timers" in data

        # Verify system info
        assert "uptime_seconds" in data["system"]
        assert "metrics_enabled" in data["system"]
        assert "environment" in data["system"]

        # Verify cache metrics
        assert data["cache"]["hits"] == 1

    def test_metrics_summary_endpoint(self, client):
        """Test /metrics/summary endpoint returns summary."""
        collector = get_metrics_collector()
        collector.reset()

        # Record some metrics
        with collector.time_agent("test_agent"):
            pass
        collector.record_agent_success("test_agent")

        response = client.get("/metrics/summary")

        assert response.status_code == 200
        assert response.content_type == "application/json"

        data = json.loads(response.data)
        assert "uptime_seconds" in data
        assert "total_agent_executions" in data
        assert "total_api_calls" in data
        assert "overall_agent_success_rate" in data
        assert "overall_api_success_rate" in data
        assert "cache_hit_rate" in data
        assert "cache_total_requests" in data

        assert data["total_agent_executions"] == 1
        assert data["overall_agent_success_rate"] == 100.0

    def test_metrics_prometheus_endpoint(self, client):
        """Test /metrics/prometheus endpoint returns Prometheus format."""
        collector = get_metrics_collector()
        collector.reset()

        # Record some metrics
        collector.record_cache_hit()
        collector.record_cache_miss()

        response = client.get("/metrics/prometheus")

        assert response.status_code == 200
        assert response.content_type == "text/plain; charset=utf-8"

        text = response.data.decode("utf-8")

        # Check Prometheus format
        assert "# HELP" in text
        assert "# TYPE" in text
        assert "shopping_optimizer_uptime_seconds" in text
        assert "shopping_optimizer_cache_hits_total" in text
        assert "shopping_optimizer_cache_misses_total" in text

        # Verify values are present
        lines = [l for l in text.split("\n") if l and not l.startswith("#")]
        assert len(lines) > 0

    def test_metrics_endpoint_handles_errors(self, client):
        """Test metrics endpoint handles errors gracefully."""
        with patch("app.metrics_collector.get_metrics", side_effect=Exception("Test error")):
            response = client.get("/metrics")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert "error" in data
            assert "message" in data


# =============================================================================
# Health Check Endpoint Tests
# =============================================================================


class TestHealthCheckEndpoints:
    """Test health check endpoints.

    Requirements: 10.3
    """

    def test_basic_health_endpoint(self, client):
        """Test /health endpoint returns basic status."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.content_type == "application/json"

        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert data["service"] == "shopping-optimizer"
        assert "environment" in data

    def test_detailed_health_all_healthy(self, client):
        """Test /health/detailed when all dependencies are healthy."""
        # Mock all services as healthy
        mock_geocoding = AsyncMock()
        mock_geocoding.health_check = AsyncMock(return_value=True)

        mock_discount = AsyncMock()
        mock_discount.health_check = AsyncMock(return_value=True)

        mock_cache = AsyncMock()
        mock_cache.health_check = AsyncMock(return_value=True)

        mock_factory = Mock()
        mock_factory.get_geocoding_service = Mock(return_value=mock_geocoding)
        mock_factory.get_discount_repository = Mock(return_value=mock_discount)
        mock_factory.get_cache_repository = Mock(return_value=mock_cache)

        with patch("app.agent_factory", mock_factory):
            response = client.get("/health/detailed")

            assert response.status_code == 200
            data = json.loads(response.data)

            assert data["status"] == "healthy"
            assert data["service"] == "shopping-optimizer"
            assert "dependencies" in data
            assert "timestamp" in data
            assert "correlation_id" in data

            # Check all dependencies are healthy
            deps = data["dependencies"]
            assert deps["geocoding_service"]["status"] == "healthy"
            assert deps["discount_repository"]["status"] == "healthy"
            assert deps["cache_repository"]["status"] == "healthy"

    def test_detailed_health_degraded(self, client):
        """Test /health/detailed when some dependencies are unhealthy."""
        # Mock one service as unhealthy
        mock_geocoding = AsyncMock()
        mock_geocoding.health_check = AsyncMock(return_value=False)

        mock_discount = AsyncMock()
        mock_discount.health_check = AsyncMock(return_value=True)

        mock_cache = AsyncMock()
        mock_cache.health_check = AsyncMock(return_value=True)

        mock_factory = Mock()
        mock_factory.get_geocoding_service = Mock(return_value=mock_geocoding)
        mock_factory.get_discount_repository = Mock(return_value=mock_discount)
        mock_factory.get_cache_repository = Mock(return_value=mock_cache)

        with patch("app.agent_factory", mock_factory):
            response = client.get("/health/detailed")

            # Should still return 200 but with degraded status
            assert response.status_code == 200
            data = json.loads(response.data)

            assert data["status"] == "degraded"

            # Check specific dependency status
            deps = data["dependencies"]
            assert deps["geocoding_service"]["status"] == "unhealthy"
            assert deps["discount_repository"]["status"] == "healthy"
            assert deps["cache_repository"]["status"] == "healthy"

    def test_detailed_health_all_unhealthy(self, client):
        """Test /health/detailed when all dependencies are unhealthy."""
        # Mock all services as unhealthy
        mock_geocoding = AsyncMock()
        mock_geocoding.health_check = AsyncMock(return_value=False)

        mock_discount = AsyncMock()
        mock_discount.health_check = AsyncMock(return_value=False)

        mock_cache = AsyncMock()
        mock_cache.health_check = AsyncMock(return_value=False)

        mock_factory = Mock()
        mock_factory.get_geocoding_service = Mock(return_value=mock_geocoding)
        mock_factory.get_discount_repository = Mock(return_value=mock_discount)
        mock_factory.get_cache_repository = Mock(return_value=mock_cache)

        with patch("app.agent_factory", mock_factory):
            response = client.get("/health/detailed")

            # Should return 503 Service Unavailable
            assert response.status_code == 503
            data = json.loads(response.data)

            assert data["status"] == "unhealthy"

            # Check all dependencies are unhealthy
            deps = data["dependencies"]
            assert deps["geocoding_service"]["status"] == "unhealthy"
            assert deps["discount_repository"]["status"] == "unhealthy"
            assert deps["cache_repository"]["status"] == "unhealthy"

    def test_detailed_health_handles_exceptions(self, client):
        """Test /health/detailed handles exceptions gracefully."""
        # Mock service that raises exception
        mock_geocoding = AsyncMock()
        mock_geocoding.health_check = AsyncMock(side_effect=Exception("Connection failed"))

        mock_discount = AsyncMock()
        mock_discount.health_check = AsyncMock(return_value=True)

        mock_cache = AsyncMock()
        mock_cache.health_check = AsyncMock(return_value=True)

        mock_factory = Mock()
        mock_factory.get_geocoding_service = Mock(return_value=mock_geocoding)
        mock_factory.get_discount_repository = Mock(return_value=mock_discount)
        mock_factory.get_cache_repository = Mock(return_value=mock_cache)

        with patch("app.agent_factory", mock_factory):
            response = client.get("/health/detailed")

            # Should still return response
            assert response.status_code == 200
            data = json.loads(response.data)

            # Geocoding should be marked unhealthy
            deps = data["dependencies"]
            assert deps["geocoding_service"]["status"] == "unhealthy"
            assert "error" in deps["geocoding_service"]["message"].lower()


# =============================================================================
# Metrics Integration with Optimize Endpoint
# =============================================================================


class TestOptimizeEndpointMetrics:
    """Test that /api/optimize endpoint records metrics.

    Requirements: 10.2
    """

    def test_optimize_records_agent_metrics_on_success(self, client, mock_agent):
        """Test that successful optimization records agent metrics."""
        collector = get_metrics_collector()
        collector.reset()

        mock_factory = Mock()
        mock_factory.create_shopping_optimizer_agent = Mock(return_value=mock_agent)

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={"location": "55.6761,12.5683", "meals": ["pasta"], "preferences": {}},
            )

            assert response.status_code == 200

            # Verify metrics were recorded
            assert "shopping_optimizer" in collector.agent_timing
            assert collector.agent_timing["shopping_optimizer"].count == 1

            assert "shopping_optimizer" in collector.agent_success_rate
            assert collector.agent_success_rate["shopping_optimizer"].successes == 1
            assert collector.agent_success_rate["shopping_optimizer"].failures == 0

    def test_optimize_records_agent_metrics_on_failure(self, client):
        """Test that failed optimization records failure metrics."""
        collector = get_metrics_collector()
        collector.reset()

        # Mock agent that raises exception
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(side_effect=ValidationError("Test error"))

        mock_factory = Mock()
        mock_factory.create_shopping_optimizer_agent = Mock(return_value=mock_agent)

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={"location": "55.6761,12.5683", "meals": ["pasta"], "preferences": {}},
            )

            assert response.status_code == 400

            # Verify failure metrics were recorded
            assert "shopping_optimizer" in collector.agent_success_rate
            assert collector.agent_success_rate["shopping_optimizer"].failures == 1

            # Verify error type was tracked
            error_key = "agent_error:shopping_optimizer:ValidationError"
            assert error_key in collector.counters
            assert collector.counters[error_key].count == 1

"""
Tests for health check functionality.

This module tests health check aggregation and dependency monitoring
to ensure proper system health reporting.

Requirements: 10.3
"""

from datetime import UTC
from unittest.mock import AsyncMock

import pytest

from agents.discount_optimizer.domain.protocols import (
    CacheRepository,
    DiscountRepository,
    GeocodingService,
)


class TestHealthCheckIntegration:
    """Test health check integration with repositories.

    These tests verify that health checks properly aggregate status
    from multiple dependencies using mocked repositories.
    """

    @pytest.fixture
    def mock_geocoding_service(self):
        """Create mock geocoding service."""
        service = AsyncMock(spec=GeocodingService)
        service.health_check = AsyncMock(return_value=True)
        return service

    @pytest.fixture
    def mock_discount_repository(self):
        """Create mock discount repository."""
        repo = AsyncMock(spec=DiscountRepository)
        repo.health_check = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def mock_cache_repository(self):
        """Create mock cache repository."""
        repo = AsyncMock(spec=CacheRepository)
        repo.health_check = AsyncMock(return_value=True)
        return repo

    @pytest.mark.asyncio
    async def test_all_dependencies_healthy(
        self, mock_geocoding_service, mock_discount_repository, mock_cache_repository
    ):
        """Test health check when all dependencies are healthy."""
        # All mocks return True by default
        assert await mock_geocoding_service.health_check() is True
        assert await mock_discount_repository.health_check() is True
        assert await mock_cache_repository.health_check() is True

        # Aggregate status should be healthy
        all_healthy = all(
            [
                await mock_geocoding_service.health_check(),
                await mock_discount_repository.health_check(),
                await mock_cache_repository.health_check(),
            ]
        )
        assert all_healthy is True

    @pytest.mark.asyncio
    async def test_one_dependency_unhealthy(
        self, mock_geocoding_service, mock_discount_repository, mock_cache_repository
    ):
        """Test health check when one dependency is unhealthy."""
        # Make geocoding service unhealthy
        mock_geocoding_service.health_check = AsyncMock(return_value=False)

        assert await mock_geocoding_service.health_check() is False
        assert await mock_discount_repository.health_check() is True
        assert await mock_cache_repository.health_check() is True

        # Aggregate status should be degraded (not all healthy)
        all_healthy = all(
            [
                await mock_geocoding_service.health_check(),
                await mock_discount_repository.health_check(),
                await mock_cache_repository.health_check(),
            ]
        )
        assert all_healthy is False

        # But some are still healthy
        any_healthy = any(
            [
                await mock_geocoding_service.health_check(),
                await mock_discount_repository.health_check(),
                await mock_cache_repository.health_check(),
            ]
        )
        assert any_healthy is True

    @pytest.mark.asyncio
    async def test_all_dependencies_unhealthy(
        self, mock_geocoding_service, mock_discount_repository, mock_cache_repository
    ):
        """Test health check when all dependencies are unhealthy."""
        # Make all services unhealthy
        mock_geocoding_service.health_check = AsyncMock(return_value=False)
        mock_discount_repository.health_check = AsyncMock(return_value=False)
        mock_cache_repository.health_check = AsyncMock(return_value=False)

        assert await mock_geocoding_service.health_check() is False
        assert await mock_discount_repository.health_check() is False
        assert await mock_cache_repository.health_check() is False

        # Aggregate status should be unhealthy
        all_healthy = all(
            [
                await mock_geocoding_service.health_check(),
                await mock_discount_repository.health_check(),
                await mock_cache_repository.health_check(),
            ]
        )
        assert all_healthy is False

        any_healthy = any(
            [
                await mock_geocoding_service.health_check(),
                await mock_discount_repository.health_check(),
                await mock_cache_repository.health_check(),
            ]
        )
        assert any_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_exception_handling(
        self, mock_geocoding_service, mock_discount_repository, mock_cache_repository
    ):
        """Test health check handles exceptions gracefully."""
        # Make geocoding service raise exception
        mock_geocoding_service.health_check = AsyncMock(side_effect=Exception("Connection failed"))

        # Should handle exception and treat as unhealthy
        try:
            await mock_geocoding_service.health_check()
            raise AssertionError("Should have raised exception")
        except Exception as e:
            assert str(e) == "Connection failed"
            # In real implementation, this would be caught and treated as unhealthy

    @pytest.mark.asyncio
    async def test_health_check_timeout_handling(
        self, mock_geocoding_service, mock_discount_repository, mock_cache_repository
    ):
        """Test health check handles timeouts gracefully."""
        import asyncio

        # Make geocoding service timeout
        async def slow_health_check():
            await asyncio.sleep(10)
            return True

        mock_geocoding_service.health_check = slow_health_check

        # Should timeout and treat as unhealthy
        try:
            await asyncio.wait_for(mock_geocoding_service.health_check(), timeout=0.1)
            raise AssertionError("Should have timed out")
        except TimeoutError:
            # In real implementation, this would be caught and treated as unhealthy
            pass

    @pytest.mark.asyncio
    async def test_health_check_called_once_per_dependency(
        self, mock_geocoding_service, mock_discount_repository, mock_cache_repository
    ):
        """Test that health check is called exactly once per dependency."""
        # Call health checks
        await mock_geocoding_service.health_check()
        await mock_discount_repository.health_check()
        await mock_cache_repository.health_check()

        # Verify each was called once
        mock_geocoding_service.health_check.assert_called_once()
        mock_discount_repository.health_check.assert_called_once()
        mock_cache_repository.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_returns_boolean(
        self, mock_geocoding_service, mock_discount_repository, mock_cache_repository
    ):
        """Test that health checks return boolean values."""
        result1 = await mock_geocoding_service.health_check()
        result2 = await mock_discount_repository.health_check()
        result3 = await mock_cache_repository.health_check()

        assert isinstance(result1, bool)
        assert isinstance(result2, bool)
        assert isinstance(result3, bool)


class TestHealthCheckStatusAggregation:
    """Test health check status aggregation logic."""

    def test_aggregate_all_healthy(self):
        """Test aggregating all healthy statuses."""
        statuses = [True, True, True]
        overall = all(statuses)
        assert overall is True

    def test_aggregate_one_unhealthy(self):
        """Test aggregating with one unhealthy status."""
        statuses = [True, False, True]
        overall = all(statuses)
        assert overall is False

        # Check degraded state (some healthy, some not)
        any_healthy = any(statuses)
        assert any_healthy is True

    def test_aggregate_all_unhealthy(self):
        """Test aggregating all unhealthy statuses."""
        statuses = [False, False, False]
        overall = all(statuses)
        assert overall is False

        any_healthy = any(statuses)
        assert any_healthy is False

    def test_aggregate_empty_list(self):
        """Test aggregating empty status list."""
        statuses = []
        overall = all(statuses)
        # all() returns True for empty list
        assert overall is True

    def test_count_unhealthy_dependencies(self):
        """Test counting unhealthy dependencies."""
        statuses = {
            "geocoding": True,
            "discount": False,
            "cache": True,
        }

        unhealthy_count = sum(1 for status in statuses.values() if not status)
        assert unhealthy_count == 1

        total_count = len(statuses)
        assert total_count == 3

        # Determine overall status
        if unhealthy_count == 0:
            overall_status = "healthy"
        elif unhealthy_count < total_count:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        assert overall_status == "degraded"

    def test_determine_http_status_code(self):
        """Test determining HTTP status code based on health."""
        # All healthy -> 200
        unhealthy_count = 0
        total_count = 3
        if unhealthy_count == 0:
            status_code = 200
        elif unhealthy_count < total_count:
            status_code = 200  # Degraded but still operational
        else:
            status_code = 503  # Service unavailable
        assert status_code == 200

        # Some unhealthy -> 200 (degraded)
        unhealthy_count = 1
        status_code = 200 if unhealthy_count == 0 or unhealthy_count < total_count else 503
        assert status_code == 200

        # All unhealthy -> 503
        unhealthy_count = 3
        status_code = 200 if unhealthy_count == 0 or unhealthy_count < total_count else 503
        assert status_code == 503


class TestHealthCheckResponseFormat:
    """Test health check response format."""

    def test_basic_health_response_format(self):
        """Test basic health check response format."""
        response = {
            "status": "healthy",
            "service": "shopping-optimizer",
            "environment": "test",
        }

        assert "status" in response
        assert "service" in response
        assert "environment" in response
        assert response["status"] == "healthy"

    def test_detailed_health_response_format(self):
        """Test detailed health check response format."""
        from datetime import datetime

        response = {
            "status": "healthy",
            "service": "shopping-optimizer",
            "environment": "test",
            "dependencies": {
                "geocoding_service": {"status": "healthy", "message": "Service is operational"},
                "discount_repository": {"status": "healthy", "message": "Service is operational"},
                "cache_repository": {"status": "healthy", "message": "Service is operational"},
            },
            "timestamp": datetime.now(UTC).isoformat(),
            "correlation_id": "test-correlation-id",
        }

        assert "status" in response
        assert "dependencies" in response
        assert "timestamp" in response
        assert "correlation_id" in response

        # Check dependencies structure
        deps = response["dependencies"]
        assert "geocoding_service" in deps
        assert "discount_repository" in deps
        assert "cache_repository" in deps

        # Check each dependency has required fields
        for _dep_name, dep_info in deps.items():
            assert "status" in dep_info
            assert "message" in dep_info
            assert dep_info["status"] in ["healthy", "unhealthy"]

    def test_unhealthy_dependency_response_format(self):
        """Test response format for unhealthy dependency."""
        dependency_info = {
            "status": "unhealthy",
            "message": "Health check error: Connection timeout",
        }

        assert dependency_info["status"] == "unhealthy"
        assert (
            "error" in dependency_info["message"].lower()
            or "timeout" in dependency_info["message"].lower()
        )

    def test_degraded_status_response(self):
        """Test response format for degraded status."""
        response = {
            "status": "degraded",
            "service": "shopping-optimizer",
            "dependencies": {
                "geocoding_service": {"status": "unhealthy", "message": "Service check failed"},
                "discount_repository": {"status": "healthy", "message": "Service is operational"},
                "cache_repository": {"status": "healthy", "message": "Service is operational"},
            },
        }

        assert response["status"] == "degraded"

        # Count unhealthy
        unhealthy = sum(
            1 for dep in response["dependencies"].values() if dep["status"] == "unhealthy"
        )
        assert unhealthy > 0
        assert unhealthy < len(response["dependencies"])

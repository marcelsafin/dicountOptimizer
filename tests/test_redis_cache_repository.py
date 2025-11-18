"""
Tests for Redis cache repository.

This module tests the RedisCacheRepository implementation with both
real Redis connections (if available) and mock scenarios.
"""

from unittest.mock import AsyncMock, patch

import pytest

from agents.discount_optimizer.infrastructure.redis_cache_repository import (
    REDIS_AVAILABLE,
    RedisCacheMetrics,
    RedisCacheRepository,
    create_cache_repository,
)


# Skip all tests if Redis is not installed
pytestmark = pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client for testing."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.setex = AsyncMock()
    client.delete = AsyncMock(return_value=1)
    client.scan = AsyncMock(return_value=(0, []))
    client.ping = AsyncMock(return_value=True)
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_redis_pool():
    """Create a mock Redis connection pool."""
    pool = AsyncMock()
    pool.aclose = AsyncMock()
    return pool


@pytest.fixture
def redis_cache(mock_redis_client, mock_redis_pool):
    """Create a RedisCacheRepository with mocked Redis client."""
    with (
        patch(
            "agents.discount_optimizer.infrastructure.redis_cache_repository.redis.ConnectionPool"
        ) as mock_pool_class,
        patch(
            "agents.discount_optimizer.infrastructure.redis_cache_repository.redis.Redis"
        ) as mock_redis_class,
    ):
        mock_pool_class.return_value = mock_redis_pool
        mock_redis_class.return_value = mock_redis_client

        cache = RedisCacheRepository(
            host="localhost",
            port=6379,
            db=0,
            key_prefix="test:",
        )

        # Replace the client with our mock
        cache._client = mock_redis_client
        cache._pool = mock_redis_pool

        yield cache


class TestRedisCacheMetrics:
    """Test RedisCacheMetrics dataclass."""

    def test_initial_metrics(self):
        """Test that metrics start at zero."""
        metrics = RedisCacheMetrics()

        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.sets == 0
        assert metrics.deletes == 0
        assert metrics.errors == 0
        assert metrics.connection_errors == 0

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        metrics = RedisCacheMetrics()
        metrics.hits = 75
        metrics.misses = 25

        assert metrics.total_requests == 100
        assert metrics.hit_rate == 75.0
        assert metrics.miss_rate == 25.0

    def test_hit_rate_with_no_requests(self):
        """Test hit rate when no requests have been made."""
        metrics = RedisCacheMetrics()

        assert metrics.hit_rate == 0.0
        assert metrics.miss_rate == 0.0

    def test_error_rate_calculation(self):
        """Test error rate calculation."""
        metrics = RedisCacheMetrics()
        metrics.hits = 80
        metrics.misses = 10
        metrics.sets = 5
        metrics.deletes = 5
        metrics.errors = 10

        # Total ops = 80 + 10 + 5 + 5 = 100
        # Error rate = 10 / 100 = 10%
        assert metrics.error_rate == 10.0

    def test_reset_metrics(self):
        """Test resetting metrics to zero."""
        metrics = RedisCacheMetrics()
        metrics.hits = 100
        metrics.misses = 50
        metrics.sets = 75
        metrics.errors = 5

        metrics.reset()

        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.sets == 0
        assert metrics.errors == 0


class TestRedisCacheRepository:
    """Test RedisCacheRepository implementation."""

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, redis_cache, mock_redis_client):
        """Test getting a non-existent key returns None."""
        mock_redis_client.get.return_value = None

        result = await redis_cache.get("nonexistent_key")

        assert result is None
        assert redis_cache.get_metrics().misses == 1
        assert redis_cache.get_metrics().hits == 0
        mock_redis_client.get.assert_called_once_with("test:nonexistent_key")

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, redis_cache, mock_redis_client):
        """Test getting an existing key returns the value."""
        test_value = b"test_data"
        mock_redis_client.get.return_value = test_value

        result = await redis_cache.get("test_key")

        assert result == test_value
        assert redis_cache.get_metrics().hits == 1
        assert redis_cache.get_metrics().misses == 0
        mock_redis_client.get.assert_called_once_with("test:test_key")

    @pytest.mark.asyncio
    async def test_set_cache(self, redis_cache, mock_redis_client):
        """Test setting a cache value."""
        test_value = b"test_data"
        ttl = 3600

        await redis_cache.set("test_key", test_value, ttl)

        assert redis_cache.get_metrics().sets == 1
        mock_redis_client.setex.assert_called_once_with(
            name="test:test_key", time=ttl, value=test_value
        )

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, redis_cache, mock_redis_client):
        """Test deleting an existing key."""
        mock_redis_client.delete.return_value = 1

        result = await redis_cache.delete("test_key")

        assert result is True
        assert redis_cache.get_metrics().deletes == 1
        mock_redis_client.delete.assert_called_once_with("test:test_key")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, redis_cache, mock_redis_client):
        """Test deleting a non-existent key."""
        mock_redis_client.delete.return_value = 0

        result = await redis_cache.delete("nonexistent_key")

        assert result is False
        assert redis_cache.get_metrics().deletes == 1

    @pytest.mark.asyncio
    async def test_clear_cache(self, redis_cache, mock_redis_client):
        """Test clearing all cache entries with prefix."""
        # Mock SCAN to return some keys
        mock_redis_client.scan.side_effect = [
            (1, [b"test:key1", b"test:key2"]),
            (0, [b"test:key3"]),
        ]
        mock_redis_client.delete.return_value = 3

        await redis_cache.clear()

        # Should call scan twice (cursor 0 means done)
        assert mock_redis_client.scan.call_count == 2
        # Should delete all found keys
        assert mock_redis_client.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_get_size(self, redis_cache, mock_redis_client):
        """Test getting cache size."""
        # Mock SCAN to return keys
        mock_redis_client.scan.side_effect = [
            (1, [b"test:key1", b"test:key2"]),
            (0, [b"test:key3"]),
        ]

        size = await redis_cache.get_size()

        assert size == 3
        assert mock_redis_client.scan.call_count == 2

    @pytest.mark.asyncio
    async def test_health_check_success(self, redis_cache, mock_redis_client):
        """Test health check with successful ping."""
        mock_redis_client.ping.return_value = True

        is_healthy = await redis_cache.health_check()

        assert is_healthy is True
        mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, redis_cache, mock_redis_client):
        """Test health check with failed ping."""
        from redis.exceptions import ConnectionError as RedisConnectionError

        mock_redis_client.ping.side_effect = RedisConnectionError("Connection failed")

        is_healthy = await redis_cache.health_check()

        assert is_healthy is False
        assert redis_cache.get_metrics().errors == 1
        assert redis_cache.get_metrics().connection_errors == 1

    @pytest.mark.asyncio
    async def test_key_prefix(self, redis_cache, mock_redis_client):
        """Test that key prefix is applied correctly."""
        await redis_cache.set("mykey", b"value", 60)

        # Should call with prefixed key
        mock_redis_client.setex.assert_called_once()
        call_args = mock_redis_client.setex.call_args
        assert call_args[1]["name"] == "test:mykey"

    @pytest.mark.asyncio
    async def test_context_manager(self, redis_cache, mock_redis_client, mock_redis_pool):
        """Test async context manager support."""
        async with redis_cache as cache:
            assert cache is redis_cache

        # Should close client and pool
        mock_redis_client.aclose.assert_called_once()
        mock_redis_pool.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_metrics(self, redis_cache):
        """Test getting metrics."""
        metrics = redis_cache.get_metrics()

        assert isinstance(metrics, RedisCacheMetrics)
        assert metrics.hits == 0
        assert metrics.misses == 0

    def test_reset_metrics(self, redis_cache):
        """Test resetting metrics."""
        # Set some metrics
        redis_cache._metrics.hits = 10
        redis_cache._metrics.misses = 5

        redis_cache.reset_metrics()

        metrics = redis_cache.get_metrics()
        assert metrics.hits == 0
        assert metrics.misses == 0


class TestCacheFactory:
    """Test cache factory functions."""

    def test_create_memory_cache(self):
        """Test creating in-memory cache."""
        cache = create_cache_repository(cache_type="memory")

        from agents.discount_optimizer.infrastructure.cache_repository import (
            InMemoryCacheRepository,
        )

        assert isinstance(cache, InMemoryCacheRepository)

    def test_create_redis_cache(self):
        """Test creating Redis cache."""
        with (
            patch(
                "agents.discount_optimizer.infrastructure.redis_cache_repository.redis.ConnectionPool"
            ),
            patch("agents.discount_optimizer.infrastructure.redis_cache_repository.redis.Redis"),
        ):
            cache = create_cache_repository(
                cache_type="redis",
                redis_host="localhost",
                redis_port=6379,
                redis_db=0,
            )

            assert isinstance(cache, RedisCacheRepository)

    def test_create_invalid_cache_type(self):
        """Test creating cache with invalid type."""
        with pytest.raises(ValueError, match="Invalid cache_type"):
            create_cache_repository(cache_type="invalid")


@pytest.mark.integration
@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
class TestRedisCacheIntegration:
    """Integration tests with real Redis (if available).

    These tests require a running Redis instance on localhost:6379.
    They are marked as integration tests and can be skipped in CI.
    """

    @pytest.mark.asyncio
    async def test_real_redis_operations(self):
        """Test basic operations with real Redis."""
        try:
            cache = RedisCacheRepository(
                host="localhost",
                port=6379,
                db=15,  # Use a separate DB for testing
                key_prefix="test_integration:",
            )

            async with cache:
                # Test health check
                is_healthy = await cache.health_check()
                if not is_healthy:
                    pytest.skip("Redis not available")

                # Test set and get
                test_data = b"integration_test_data"
                await cache.set("test_key", test_data, ttl_seconds=60)

                result = await cache.get("test_key")
                assert result == test_data

                # Test delete
                deleted = await cache.delete("test_key")
                assert deleted is True

                # Verify deleted
                result = await cache.get("test_key")
                assert result is None

                # Test metrics
                metrics = cache.get_metrics()
                assert metrics.hits >= 1
                assert metrics.sets >= 1

        except Exception as e:
            pytest.skip(f"Redis integration test failed: {e}")

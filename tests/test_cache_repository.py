"""Unit tests for InMemoryCacheRepository with TTL and metrics.

This test suite verifies the cache repository implementation including:
- Basic get/set operations
- TTL expiration
- Cache metrics (hit rate, miss rate)
- Key generation utilities
- Health checks
"""

import asyncio
from typing import Any

import pytest
import pytest_asyncio

from agents.discount_optimizer.domain.models import Location
from agents.discount_optimizer.domain.protocols import CacheRepository
from agents.discount_optimizer.infrastructure.cache_repository import (
    InMemoryCacheRepository,
    deserialize_from_cache,
    generate_cache_key,
    generate_cache_key_from_dict,
    get_cache,
    serialize_for_cache,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def cache() -> InMemoryCacheRepository:
    """Fixture providing a fresh cache instance for each test."""
    cache_instance = InMemoryCacheRepository()
    # Start cleanup task in async context
    cache_instance._start_cleanup_task()
    yield cache_instance
    await cache_instance.close()


@pytest.fixture
def test_data() -> dict[str, Any]:
    """Fixture providing test data for caching."""
    return {
        "products": ["milk", "bread", "eggs"],
        "prices": [25.0, 15.0, 30.0],
        "store": "Netto",
    }


# ============================================================================
# Test: Cache Initialization
# ============================================================================


def test_cache_initialization():
    """Test that cache initializes correctly."""
    cache = InMemoryCacheRepository()

    assert cache._cache == {}
    assert cache._metrics.hits == 0
    assert cache._metrics.misses == 0
    assert cache._metrics.sets == 0
    assert cache._lock is not None


def test_cache_implements_protocol():
    """Test that cache correctly implements CacheRepository protocol."""
    cache = InMemoryCacheRepository()

    # Runtime check using @runtime_checkable protocol
    assert isinstance(cache, CacheRepository)


# ============================================================================
# Test: Basic Get/Set Operations
# ============================================================================


@pytest.mark.asyncio
async def test_set_and_get_success(cache: InMemoryCacheRepository):
    """Test basic set and get operations."""
    key = "test_key"
    value = b"test_value"
    ttl = 60

    # Set value
    await cache.set(key, value, ttl_seconds=ttl)

    # Get value
    result = await cache.get(key)

    assert result == value
    assert cache._metrics.sets == 1
    assert cache._metrics.hits == 1
    assert cache._metrics.misses == 0


@pytest.mark.asyncio
async def test_get_nonexistent_key(cache: InMemoryCacheRepository):
    """Test getting a key that doesn't exist."""
    result = await cache.get("nonexistent_key")

    assert result is None
    assert cache._metrics.misses == 1
    assert cache._metrics.hits == 0


@pytest.mark.asyncio
async def test_set_overwrites_existing_key(cache: InMemoryCacheRepository):
    """Test that setting an existing key overwrites the value."""
    key = "test_key"

    # Set initial value
    await cache.set(key, b"value1", ttl_seconds=60)

    # Overwrite with new value
    await cache.set(key, b"value2", ttl_seconds=60)

    # Get should return new value
    result = await cache.get(key)

    assert result == b"value2"
    assert cache._metrics.sets == 2


@pytest.mark.asyncio
async def test_set_multiple_keys(cache: InMemoryCacheRepository):
    """Test setting multiple different keys."""
    await cache.set("key1", b"value1", ttl_seconds=60)
    await cache.set("key2", b"value2", ttl_seconds=60)
    await cache.set("key3", b"value3", ttl_seconds=60)

    assert await cache.get("key1") == b"value1"
    assert await cache.get("key2") == b"value2"
    assert await cache.get("key3") == b"value3"

    size = await cache.get_size()
    assert size == 3


# ============================================================================
# Test: TTL Expiration
# ============================================================================


@pytest.mark.asyncio
async def test_get_expired_key_returns_none(cache: InMemoryCacheRepository):
    """Test that expired keys return None and are removed."""
    key = "test_key"
    value = b"test_value"

    # Set with very short TTL
    await cache.set(key, value, ttl_seconds=1)

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Get should return None
    result = await cache.get(key)

    assert result is None
    assert cache._metrics.misses == 1
    assert cache._metrics.evictions == 1


@pytest.mark.asyncio
async def test_ttl_not_expired_returns_value(cache: InMemoryCacheRepository):
    """Test that non-expired keys return their values."""
    key = "test_key"
    value = b"test_value"

    # Set with longer TTL
    await cache.set(key, value, ttl_seconds=10)

    # Get immediately
    result = await cache.get(key)

    assert result == value
    assert cache._metrics.hits == 1


@pytest.mark.asyncio
async def test_different_ttls_for_different_keys(cache: InMemoryCacheRepository):
    """Test that different keys can have different TTLs."""
    # Set key1 with short TTL
    await cache.set("key1", b"value1", ttl_seconds=1)

    # Set key2 with long TTL
    await cache.set("key2", b"value2", ttl_seconds=10)

    # Wait for key1 to expire
    await asyncio.sleep(1.1)

    # key1 should be expired, key2 should still exist
    assert await cache.get("key1") is None
    assert await cache.get("key2") == b"value2"


# ============================================================================
# Test: Cache Metrics
# ============================================================================


@pytest.mark.asyncio
async def test_metrics_hit_rate_calculation(cache: InMemoryCacheRepository):
    """Test that hit rate is calculated correctly."""
    # Set some values
    await cache.set("key1", b"value1", ttl_seconds=60)
    await cache.set("key2", b"value2", ttl_seconds=60)

    # 2 hits
    await cache.get("key1")
    await cache.get("key2")

    # 1 miss
    await cache.get("key3")

    metrics = cache.get_metrics()

    assert metrics.hits == 2
    assert metrics.misses == 1
    assert metrics.total_requests == 3
    assert metrics.hit_rate == pytest.approx(66.67, rel=0.01)
    assert metrics.miss_rate == pytest.approx(33.33, rel=0.01)


@pytest.mark.asyncio
async def test_metrics_with_no_requests(cache: InMemoryCacheRepository):
    """Test metrics when no requests have been made."""
    metrics = cache.get_metrics()

    assert metrics.hits == 0
    assert metrics.misses == 0
    assert metrics.total_requests == 0
    assert metrics.hit_rate == 0.0
    assert metrics.miss_rate == 0.0


@pytest.mark.asyncio
async def test_metrics_reset(cache: InMemoryCacheRepository):
    """Test that metrics can be reset."""
    # Generate some metrics
    await cache.set("key1", b"value1", ttl_seconds=60)
    await cache.get("key1")
    await cache.get("key2")

    # Reset metrics
    cache.reset_metrics()

    metrics = cache.get_metrics()
    assert metrics.hits == 0
    assert metrics.misses == 0
    assert metrics.sets == 0
    assert metrics.evictions == 0


@pytest.mark.asyncio
async def test_metrics_eviction_count(cache: InMemoryCacheRepository):
    """Test that evictions are counted correctly."""
    # Set with short TTL
    await cache.set("key1", b"value1", ttl_seconds=1)

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Access expired key (triggers eviction)
    await cache.get("key1")

    metrics = cache.get_metrics()
    assert metrics.evictions == 1


# ============================================================================
# Test: Delete and Clear Operations
# ============================================================================


@pytest.mark.asyncio
async def test_delete_existing_key(cache: InMemoryCacheRepository):
    """Test deleting an existing key."""
    await cache.set("key1", b"value1", ttl_seconds=60)

    deleted = await cache.delete("key1")

    assert deleted is True
    assert await cache.get("key1") is None


@pytest.mark.asyncio
async def test_delete_nonexistent_key(cache: InMemoryCacheRepository):
    """Test deleting a key that doesn't exist."""
    deleted = await cache.delete("nonexistent")

    assert deleted is False


@pytest.mark.asyncio
async def test_clear_removes_all_entries(cache: InMemoryCacheRepository):
    """Test that clear removes all cached entries."""
    # Add multiple entries
    await cache.set("key1", b"value1", ttl_seconds=60)
    await cache.set("key2", b"value2", ttl_seconds=60)
    await cache.set("key3", b"value3", ttl_seconds=60)

    # Clear cache
    await cache.clear()

    # All keys should be gone
    assert await cache.get("key1") is None
    assert await cache.get("key2") is None
    assert await cache.get("key3") is None

    size = await cache.get_size()
    assert size == 0


@pytest.mark.asyncio
async def test_clear_preserves_metrics(cache: InMemoryCacheRepository):
    """Test that clear preserves metrics."""
    # Generate some metrics
    await cache.set("key1", b"value1", ttl_seconds=60)
    await cache.get("key1")

    # Clear cache
    await cache.clear()

    # Metrics should still be there
    metrics = cache.get_metrics()
    assert metrics.hits == 1
    assert metrics.sets == 1


# ============================================================================
# Test: Health Check
# ============================================================================


@pytest.mark.asyncio
async def test_health_check_success(cache: InMemoryCacheRepository):
    """Test successful health check."""
    is_healthy = await cache.health_check()

    assert is_healthy is True


# ============================================================================
# Test: Context Manager
# ============================================================================


@pytest.mark.asyncio
async def test_context_manager_cleanup():
    """Test that context manager properly cleans up resources."""
    cache = InMemoryCacheRepository()

    async with cache:
        await cache.set("key1", b"value1", ttl_seconds=60)
        assert await cache.get("key1") == b"value1"

    # After exiting, cache should be cleared
    size = await cache.get_size()
    assert size == 0


# ============================================================================
# Test: Background Cleanup Task
# ============================================================================


@pytest.mark.asyncio
async def test_background_cleanup_removes_expired_entries(cache: InMemoryCacheRepository):
    """Test that background cleanup task removes expired entries."""
    # Set entries with short TTL
    await cache.set("key1", b"value1", ttl_seconds=1)
    await cache.set("key2", b"value2", ttl_seconds=1)

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Manually trigger cleanup
    await cache._cleanup_expired()

    # Entries should be removed
    size = await cache.get_size()
    assert size == 0

    metrics = cache.get_metrics()
    assert metrics.evictions == 2


# ============================================================================
# Test: Key Generation Utilities
# ============================================================================


def test_generate_cache_key_basic():
    """Test basic cache key generation."""
    key = generate_cache_key("arg1", "arg2", "arg3")

    assert isinstance(key, str)
    assert len(key) == 16  # SHA256 hash truncated to 16 chars


def test_generate_cache_key_with_prefix():
    """Test cache key generation with prefix."""
    key = generate_cache_key("arg1", "arg2", prefix="discount:")

    assert key.startswith("discount:")
    assert len(key) == len("discount:") + 16


def test_generate_cache_key_deterministic():
    """Test that same inputs produce same key."""
    key1 = generate_cache_key("arg1", "arg2", "arg3")
    key2 = generate_cache_key("arg1", "arg2", "arg3")

    assert key1 == key2


def test_generate_cache_key_different_inputs():
    """Test that different inputs produce different keys."""
    key1 = generate_cache_key("arg1", "arg2")
    key2 = generate_cache_key("arg1", "arg3")

    assert key1 != key2


def test_generate_cache_key_with_complex_objects():
    """Test cache key generation with complex objects."""
    location = Location(latitude=55.6761, longitude=12.5683)
    key = generate_cache_key(location, 5.0, prefix="discount:")

    assert isinstance(key, str)
    assert key.startswith("discount:")


def test_generate_cache_key_from_dict():
    """Test cache key generation from dictionary."""
    data = {"latitude": 55.6761, "longitude": 12.5683, "radius": 5.0}
    key = generate_cache_key_from_dict(data, prefix="discount:")

    assert isinstance(key, str)
    assert key.startswith("discount:")


def test_generate_cache_key_from_dict_order_independent():
    """Test that dictionary key order doesn't affect cache key."""
    data1 = {"a": 1, "b": 2, "c": 3}
    data2 = {"c": 3, "a": 1, "b": 2}

    key1 = generate_cache_key_from_dict(data1)
    key2 = generate_cache_key_from_dict(data2)

    assert key1 == key2


# ============================================================================
# Test: Serialization Utilities
# ============================================================================


def test_serialize_and_deserialize_simple_data(test_data: dict[str, Any]):
    """Test serialization and deserialization of simple data."""
    serialized = serialize_for_cache(test_data)
    deserialized = deserialize_from_cache(serialized)

    assert deserialized == test_data


def test_serialize_and_deserialize_pydantic_model():
    """Test serialization and deserialization of Pydantic models."""
    location = Location(latitude=55.6761, longitude=12.5683)

    serialized = serialize_for_cache(location)
    deserialized = deserialize_from_cache(serialized)

    assert isinstance(deserialized, Location)
    assert deserialized.latitude == location.latitude
    assert deserialized.longitude == location.longitude


@pytest.mark.asyncio
async def test_cache_with_serialized_pydantic_model(cache: InMemoryCacheRepository):
    """Test caching Pydantic models using serialization utilities."""
    location = Location(latitude=55.6761, longitude=12.5683)
    key = "location:copenhagen"

    # Serialize and cache
    serialized = serialize_for_cache(location)
    await cache.set(key, serialized, ttl_seconds=60)

    # Retrieve and deserialize
    cached_data = await cache.get(key)
    assert cached_data is not None

    deserialized = deserialize_from_cache(cached_data)
    assert isinstance(deserialized, Location)
    assert deserialized.latitude == location.latitude


# ============================================================================
# Test: Global Cache Instance
# ============================================================================


def test_get_cache_returns_singleton():
    """Test that get_cache returns the same instance."""
    cache1 = get_cache()
    cache2 = get_cache()

    assert cache1 is cache2


# ============================================================================
# Test: Cache Size
# ============================================================================


@pytest.mark.asyncio
async def test_get_size(cache: InMemoryCacheRepository):
    """Test getting cache size."""
    assert await cache.get_size() == 0

    await cache.set("key1", b"value1", ttl_seconds=60)
    assert await cache.get_size() == 1

    await cache.set("key2", b"value2", ttl_seconds=60)
    assert await cache.get_size() == 2

    await cache.delete("key1")
    assert await cache.get_size() == 1

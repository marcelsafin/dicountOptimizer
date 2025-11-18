"""In-memory cache repository with TTL support and metrics.

This module implements the CacheRepository protocol with an in-memory cache
that supports time-to-live (TTL) expiration and tracks cache performance metrics.
"""

import asyncio
import contextlib
import hashlib
import pickle
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

import structlog

from agents.discount_optimizer.config import settings
from agents.discount_optimizer.metrics import get_metrics_collector


logger = structlog.get_logger(__name__)
metrics_collector = get_metrics_collector()


class CacheEntry(TypedDict):
    """Type definition for cache entry structure."""

    value: bytes
    expires_at: datetime


@dataclass
class CacheMetrics:
    """Cache performance metrics.

    Tracks cache hit rate, miss rate, and other performance indicators
    to help optimize caching strategy.

    Attributes:
        hits: Number of successful cache retrievals
        misses: Number of cache misses (key not found or expired)
        sets: Number of cache writes
        evictions: Number of entries removed due to expiration
        total_requests: Total number of get requests
    """

    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0

    @property
    def total_requests(self) -> int:
        """Total number of cache get requests."""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a percentage (0-100).

        Returns:
            Hit rate percentage, or 0.0 if no requests have been made
        """
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100.0

    @property
    def miss_rate(self) -> float:
        """Cache miss rate as a percentage (0-100).

        Returns:
            Miss rate percentage, or 0.0 if no requests have been made
        """
        if self.total_requests == 0:
            return 0.0
        return (self.misses / self.total_requests) * 100.0

    def reset(self) -> None:
        """Reset all metrics to zero."""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.evictions = 0


class InMemoryCacheRepository:
    """In-memory cache repository with TTL support and metrics.

    This implementation provides a simple, thread-safe in-memory cache with:
    - Time-to-live (TTL) expiration for cache entries
    - Automatic cleanup of expired entries
    - Performance metrics (hit rate, miss rate)
    - Key generation utilities for complex objects
    - Async interface for consistency with other repositories

    The cache uses pickle for serialization, allowing storage of any
    Python object. For production use with distributed systems, consider
    using Redis or Memcached instead.

    Example:
        >>> cache = InMemoryCacheRepository()
        >>> await cache.set("user:123", b"user_data", ttl_seconds=300)
        >>> data = await cache.get("user:123")
        >>> metrics = cache.get_metrics()
        >>> print(f"Hit rate: {metrics.hit_rate:.1f}%")
    """

    def __init__(self) -> None:
        """Initialize the in-memory cache repository."""
        self._cache: dict[str, CacheEntry] = {}
        self._metrics = CacheMetrics()
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task[None] | None = None

        logger.info(
            "cache_repository_initialized",
            caching_enabled=settings.enable_caching,
            default_ttl=settings.cache_ttl_seconds,
        )

    def _start_cleanup_task(self) -> None:
        """Start background task for periodic cleanup of expired entries.

        Only starts if caching is enabled and there's a running event loop.
        """
        if not settings.enable_caching:
            return

        try:
            # Only create task if there's a running event loop
            asyncio.get_running_loop()
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
                logger.debug("cache_cleanup_task_started")
        except RuntimeError:
            # No event loop running, skip cleanup task
            # This is normal during synchronous initialization
            logger.debug("cache_cleanup_task_skipped_no_event_loop")

    async def _cleanup_loop(self) -> None:
        """Background loop that periodically removes expired cache entries.

        Runs every 60 seconds to clean up expired entries and prevent
        unbounded memory growth.
        """
        while True:
            try:
                await asyncio.sleep(60)  # Run cleanup every minute
                await self._cleanup_expired()
            except asyncio.CancelledError:
                logger.info("cache_cleanup_task_cancelled")
                break
            except Exception as e:
                logger.exception(
                    "cache_cleanup_error",
                    error=str(e),
                    error_type=type(e).__name__,
                )

    async def _cleanup_expired(self) -> None:
        """Remove all expired entries from the cache.

        This method is called periodically by the cleanup task and can also
        be called manually to force cleanup.
        """
        async with self._lock:
            now = datetime.now(UTC)
            expired_keys = [key for key, entry in self._cache.items() if entry["expires_at"] <= now]

            for key in expired_keys:
                del self._cache[key]
                self._metrics.evictions += 1

            if expired_keys:
                logger.debug(
                    "cache_cleanup_completed",
                    evicted_count=len(expired_keys),
                    remaining_count=len(self._cache),
                )

    async def get(self, key: str) -> bytes | None:
        """Get cached value by key.

        Retrieves the cached value if it exists and hasn't expired.
        Automatically removes expired entries on access.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value as bytes if found and not expired, None otherwise

        Example:
            >>> data = await cache.get("discount:copenhagen:5km")
            >>> if data:
            ...     discounts = pickle.loads(data)
        """
        if not settings.enable_caching:
            self._metrics.misses += 1
            return None

        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._metrics.misses += 1
                metrics_collector.record_cache_miss()
                logger.debug("cache_miss", key=key)
                return None

            # Check if entry has expired
            now = datetime.now(UTC)
            if entry["expires_at"] <= now:
                # Entry expired, remove it
                del self._cache[key]
                self._metrics.misses += 1
                self._metrics.evictions += 1
                metrics_collector.record_cache_miss()
                metrics_collector.record_cache_eviction()
                logger.debug("cache_expired", key=key)
                return None

            # Cache hit
            self._metrics.hits += 1
            metrics_collector.record_cache_hit()
            logger.debug(
                "cache_hit",
                key=key,
                expires_in_seconds=(entry["expires_at"] - now).total_seconds(),
            )
            return entry["value"]

    async def set(self, key: str, value: bytes, ttl_seconds: int) -> None:
        """Set cached value with TTL.

        Stores a value in the cache with the specified time-to-live.
        If the key already exists, it will be overwritten with the new
        value and TTL.

        Args:
            key: Cache key to set
            value: Value to cache as bytes
            ttl_seconds: Time-to-live in seconds (cache expiration time)

        Example:
            >>> import pickle
            >>> data = {"discounts": [...]}
            >>> await cache.set("discount:copenhagen:5km", pickle.dumps(data), ttl_seconds=3600)
        """
        if not settings.enable_caching:
            return

        async with self._lock:
            expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)

            self._cache[key] = CacheEntry(
                value=value,
                expires_at=expires_at,
            )

            self._metrics.sets += 1
            metrics_collector.record_cache_set()

            logger.debug(
                "cache_set",
                key=key,
                ttl_seconds=ttl_seconds,
                value_size_bytes=len(value),
                cache_size=len(self._cache),
            )

    async def delete(self, key: str) -> bool:
        """Delete a cache entry by key.

        Args:
            key: Cache key to delete

        Returns:
            True if the key was found and deleted, False otherwise

        Example:
            >>> deleted = await cache.delete("discount:copenhagen:5km")
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug("cache_delete", key=key)
                return True
            return False

    async def clear(self) -> None:
        """Clear all entries from the cache.

        This method removes all cached data and resets the cache to an
        empty state. Metrics are preserved.

        Example:
            >>> await cache.clear()
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info("cache_cleared", entries_removed=count)

    def get_metrics(self) -> CacheMetrics:
        """Get current cache performance metrics.

        Returns:
            CacheMetrics object with hit rate, miss rate, and other stats

        Example:
            >>> metrics = cache.get_metrics()
            >>> print(f"Hit rate: {metrics.hit_rate:.1f}%")
            >>> print(f"Total requests: {metrics.total_requests}")
        """
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset cache metrics to zero.

        Useful for testing or when starting a new monitoring period.

        Example:
            >>> cache.reset_metrics()
        """
        self._metrics.reset()
        logger.info("cache_metrics_reset")

    async def get_size(self) -> int:
        """Get the current number of entries in the cache.

        Returns:
            Number of cached entries (including expired but not yet cleaned)

        Example:
            >>> size = await cache.get_size()
            >>> print(f"Cache contains {size} entries")
        """
        async with self._lock:
            return len(self._cache)

    async def health_check(self) -> bool:
        """Check if the cache is healthy and operational.

        Performs a simple read/write test to verify cache functionality.

        Returns:
            True if the cache is operational, False otherwise

        Example:
            >>> is_healthy = await cache.health_check()
        """
        try:
            test_key = "__health_check__"
            test_value = b"test"

            # Test write
            await self.set(test_key, test_value, ttl_seconds=1)

            # Test read
            result = await self.get(test_key)

            # Cleanup
            await self.delete(test_key)

            is_healthy = result == test_value

            logger.debug("cache_health_check", is_healthy=is_healthy)
            return is_healthy

        except Exception as e:
            logger.exception(
                "cache_health_check_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def close(self) -> None:
        """Close the cache and cleanup resources.

        Cancels the background cleanup task and clears all cached data.
        Should be called when shutting down the application.

        Example:
            >>> await cache.close()
        """
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task

        # Clear cache
        await self.clear()

        logger.info("cache_repository_closed")

    async def __aenter__(self) -> "InMemoryCacheRepository":
        """Enter async context manager.

        Starts the cleanup task when entering async context.

        Returns:
            Self for use in async with statement
        """
        # Start cleanup task now that we're in an async context
        self._start_cleanup_task()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager and cleanup resources.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        await self.close()


# =============================================================================
# Cache Key Generation Utilities
# =============================================================================


def generate_cache_key(*args: Any, prefix: str = "") -> str:
    """Generate a deterministic cache key from arguments.

    Creates a cache key by hashing the string representation of all arguments.
    This ensures consistent keys for the same inputs while handling complex
    objects.

    Args:
        *args: Variable arguments to include in the key
        prefix: Optional prefix for the key (e.g., "discount:", "geocode:")

    Returns:
        Cache key as a string

    Example:
        >>> key = generate_cache_key(55.6761, 12.5683, 5.0, prefix="discount:")
        >>> # Returns: "discount:a1b2c3d4..."

        >>> from agents.discount_optimizer.domain.models import Location
        >>> location = Location(latitude=55.6761, longitude=12.5683)
        >>> key = generate_cache_key(location, 5.0, prefix="discount:")
    """
    # Convert all arguments to strings and concatenate
    key_parts = [str(arg) for arg in args]
    key_string = ":".join(key_parts)

    # Hash the key string for consistent length
    key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

    # Add prefix if provided
    if prefix:
        return f"{prefix}{key_hash}"
    return key_hash


def generate_cache_key_from_dict(data: dict[str, Any], prefix: str = "") -> str:
    """Generate a deterministic cache key from a dictionary.

    Creates a cache key by sorting dictionary keys and hashing the result.
    This ensures consistent keys regardless of dictionary insertion order.

    Args:
        data: Dictionary to generate key from
        prefix: Optional prefix for the key

    Returns:
        Cache key as a string

    Example:
        >>> key = generate_cache_key_from_dict(
        ...     {"latitude": 55.6761, "longitude": 12.5683, "radius": 5.0}, prefix="discount:"
        ... )
    """
    # Sort keys for consistent ordering
    sorted_items = sorted(data.items())
    key_string = ":".join(f"{k}={v}" for k, v in sorted_items)

    # Hash the key string
    key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

    # Add prefix if provided
    if prefix:
        return f"{prefix}{key_hash}"
    return key_hash


def serialize_for_cache(obj: Any) -> bytes:
    """Serialize a Python object for caching.

    Uses pickle to serialize objects to bytes. This allows caching of
    complex Python objects including Pydantic models.

    Args:
        obj: Object to serialize

    Returns:
        Serialized object as bytes

    Example:
        >>> from agents.discount_optimizer.domain.models import Location
        >>> location = Location(latitude=55.6761, longitude=12.5683)
        >>> data = serialize_for_cache(location)
        >>> await cache.set("location:copenhagen", data, ttl_seconds=3600)
    """
    return pickle.dumps(obj)


def deserialize_from_cache(data: bytes) -> Any:
    """Deserialize a Python object from cache.

    Uses pickle to deserialize bytes back to Python objects.

    Args:
        data: Serialized data from cache

    Returns:
        Deserialized Python object

    Example:
        >>> data = await cache.get("location:copenhagen")
        >>> if data:
        ...     location = deserialize_from_cache(data)
    """
    return pickle.loads(data)


# =============================================================================
# Global Cache Instance
# =============================================================================

# Global cache instance for use across the application
# This ensures a single cache is shared by all components
_global_cache: InMemoryCacheRepository | None = None


def get_cache() -> InMemoryCacheRepository:
    """Get the global cache instance.

    Creates the cache on first access (lazy initialization).
    This function is provided for dependency injection.

    Returns:
        Global InMemoryCacheRepository instance

    Example:
        >>> cache = get_cache()
        >>> await cache.set("key", b"value", ttl_seconds=300)
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = InMemoryCacheRepository()
    return _global_cache


async def close_global_cache() -> None:
    """Close the global cache instance.

    Should be called during application shutdown to cleanup resources.

    Example:
        >>> await close_global_cache()
    """
    global _global_cache
    if _global_cache is not None:
        await _global_cache.close()
        _global_cache = None

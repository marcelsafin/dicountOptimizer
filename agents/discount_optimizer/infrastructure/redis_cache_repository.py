"""Redis cache repository with connection pooling and distributed cache support.

This module implements the CacheRepository protocol using Redis as the backend,
enabling multi-instance deployments with shared cache across all instances.
"""

import asyncio
import pickle
from typing import Any
from dataclasses import dataclass
import structlog

try:
    import redis.asyncio as redis
    from redis.asyncio.connection import ConnectionPool
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore
    RedisError = Exception  # type: ignore
    RedisConnectionError = Exception  # type: ignore

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from ..domain.protocols import CacheRepository
from ..config import settings
from ..metrics import get_metrics_collector

logger = structlog.get_logger(__name__)
metrics_collector = get_metrics_collector()


@dataclass
class RedisCacheMetrics:
    """Redis cache performance metrics.
    
    Tracks cache hit rate, miss rate, and other performance indicators
    for distributed cache monitoring.
    
    Attributes:
        hits: Number of successful cache retrievals
        misses: Number of cache misses (key not found or expired)
        sets: Number of cache writes
        deletes: Number of cache deletions
        errors: Number of Redis operation errors
        connection_errors: Number of connection failures
    """
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    connection_errors: int = 0
    
    @property
    def total_requests(self) -> int:
        """Total number of cache get requests."""
        return self.hits + self.misses
    
    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a percentage (0-100)."""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100.0
    
    @property
    def miss_rate(self) -> float:
        """Cache miss rate as a percentage (0-100)."""
        if self.total_requests == 0:
            return 0.0
        return (self.misses / self.total_requests) * 100.0
    
    @property
    def error_rate(self) -> float:
        """Error rate as a percentage of total operations."""
        total_ops = self.total_requests + self.sets + self.deletes
        if total_ops == 0:
            return 0.0
        return (self.errors / total_ops) * 100.0
    
    def reset(self) -> None:
        """Reset all metrics to zero."""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.connection_errors = 0


class RedisCacheRepository:
    """Redis cache repository with connection pooling and retry logic.
    
    This implementation provides a distributed cache using Redis with:
    - Async Redis client with connection pooling
    - Automatic retry with exponential backoff
    - Health check monitoring
    - Performance metrics (hit rate, miss rate, error rate)
    - Graceful degradation on connection failures
    - TTL support for cache expiration
    
    The cache uses pickle for serialization, allowing storage of any
    Python object. Redis provides persistence and multi-instance support.
    
    Example:
        >>> cache = RedisCacheRepository(
        ...     host="localhost",
        ...     port=6379,
        ...     db=0
        ... )
        >>> async with cache:
        ...     await cache.set("user:123", b"user_data", ttl_seconds=300)
        ...     data = await cache.get("user:123")
        ...     metrics = cache.get_metrics()
        ...     print(f"Hit rate: {metrics.hit_rate:.1f}%")
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        max_connections: int = 10,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        key_prefix: str = "shopping_optimizer:",
    ) -> None:
        """Initialize the Redis cache repository.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number (0-15)
            password: Redis password (None for no auth)
            max_connections: Maximum connections in the pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Connection timeout in seconds
            key_prefix: Prefix for all cache keys (namespace isolation)
        
        Raises:
            ImportError: If redis package is not installed
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis package is required for RedisCacheRepository. "
                "Install it with: pip install redis>=5.0.0"
            )
        
        self.host = host
        self.port = port
        self.db = db
        self.key_prefix = key_prefix
        self._metrics = RedisCacheMetrics()
        
        # Create connection pool
        self._pool: ConnectionPool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            decode_responses=False,  # We handle bytes directly
        )
        
        # Create Redis client
        self._client: redis.Redis = redis.Redis(connection_pool=self._pool)
        
        logger.info(
            "redis_cache_repository_initialized",
            host=host,
            port=port,
            db=db,
            max_connections=max_connections,
            key_prefix=key_prefix,
            caching_enabled=settings.enable_caching,
        )
    
    def _prefixed_key(self, key: str) -> str:
        """Add prefix to cache key for namespace isolation.
        
        Args:
            key: Original cache key
        
        Returns:
            Prefixed cache key
        """
        return f"{self.key_prefix}{key}"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((RedisConnectionError, RedisError)),
    )
    async def get(self, key: str) -> bytes | None:
        """Get cached value by key with automatic retry.
        
        Retrieves the cached value if it exists. Redis handles TTL expiration
        automatically, so expired keys will return None.
        
        Args:
            key: Cache key to retrieve
        
        Returns:
            Cached value as bytes if found, None otherwise
        
        Example:
            >>> data = await cache.get("discount:copenhagen:5km")
            >>> if data:
            ...     discounts = pickle.loads(data)
        """
        if not settings.enable_caching:
            self._metrics.misses += 1
            return None
        
        try:
            prefixed_key = self._prefixed_key(key)
            value = await self._client.get(prefixed_key)
            
            if value is None:
                self._metrics.misses += 1
                metrics_collector.record_cache_miss()
                logger.debug("redis_cache_miss", key=key)
                return None
            
            # Cache hit
            self._metrics.hits += 1
            metrics_collector.record_cache_hit()
            logger.debug(
                "redis_cache_hit",
                key=key,
                value_size_bytes=len(value),
            )
            # Redis returns bytes, ensure type safety
            return bytes(value) if value is not None else None
            
        except (RedisConnectionError, RedisError) as e:
            self._metrics.errors += 1
            if isinstance(e, RedisConnectionError):
                self._metrics.connection_errors += 1
            
            logger.error(
                "redis_cache_get_error",
                key=key,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Return None on error (graceful degradation)
            return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((RedisConnectionError, RedisError)),
    )
    async def set(self, key: str, value: bytes, ttl_seconds: int) -> None:
        """Set cached value with TTL and automatic retry.
        
        Stores a value in Redis with the specified time-to-live.
        Redis will automatically expire the key after TTL seconds.
        
        Args:
            key: Cache key to set
            value: Value to cache as bytes
            ttl_seconds: Time-to-live in seconds (cache expiration time)
        
        Example:
            >>> import pickle
            >>> data = {"discounts": [...]}
            >>> await cache.set(
            ...     "discount:copenhagen:5km",
            ...     pickle.dumps(data),
            ...     ttl_seconds=3600
            ... )
        """
        if not settings.enable_caching:
            return
        
        try:
            prefixed_key = self._prefixed_key(key)
            await self._client.setex(
                name=prefixed_key,
                time=ttl_seconds,
                value=value,
            )
            
            self._metrics.sets += 1
            metrics_collector.record_cache_set()
            
            logger.debug(
                "redis_cache_set",
                key=key,
                ttl_seconds=ttl_seconds,
                value_size_bytes=len(value),
            )
            
        except (RedisConnectionError, RedisError) as e:
            self._metrics.errors += 1
            if isinstance(e, RedisConnectionError):
                self._metrics.connection_errors += 1
            
            logger.error(
                "redis_cache_set_error",
                key=key,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Fail silently on cache write errors (graceful degradation)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((RedisConnectionError, RedisError)),
    )
    async def delete(self, key: str) -> bool:
        """Delete a cache entry by key with automatic retry.
        
        Args:
            key: Cache key to delete
        
        Returns:
            True if the key was found and deleted, False otherwise
        
        Example:
            >>> deleted = await cache.delete("discount:copenhagen:5km")
        """
        try:
            prefixed_key = self._prefixed_key(key)
            result = await self._client.delete(prefixed_key)
            
            self._metrics.deletes += 1
            
            deleted: bool = bool(result > 0)
            logger.debug("redis_cache_delete", key=key, deleted=deleted)
            return deleted
            
        except (RedisConnectionError, RedisError) as e:
            self._metrics.errors += 1
            if isinstance(e, RedisConnectionError):
                self._metrics.connection_errors += 1
            
            logger.error(
                "redis_cache_delete_error",
                key=key,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
    
    async def clear(self) -> None:
        """Clear all entries with the configured prefix from Redis.
        
        This method removes all cached data with the key prefix.
        Use with caution in production environments.
        
        Example:
            >>> await cache.clear()
        """
        try:
            # Use SCAN to find all keys with our prefix
            pattern = f"{self.key_prefix}*"
            cursor = 0
            deleted_count = 0
            
            while True:
                cursor, keys = await self._client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                
                if keys:
                    deleted = await self._client.delete(*keys)
                    deleted_count += deleted
                
                if cursor == 0:
                    break
            
            logger.info(
                "redis_cache_cleared",
                entries_removed=deleted_count,
                key_prefix=self.key_prefix,
            )
            
        except (RedisConnectionError, RedisError) as e:
            self._metrics.errors += 1
            if isinstance(e, RedisConnectionError):
                self._metrics.connection_errors += 1
            
            logger.error(
                "redis_cache_clear_error",
                error=str(e),
                error_type=type(e).__name__,
            )
    
    def get_metrics(self) -> RedisCacheMetrics:
        """Get current cache performance metrics.
        
        Returns:
            RedisCacheMetrics object with hit rate, miss rate, and error stats
        
        Example:
            >>> metrics = cache.get_metrics()
            >>> print(f"Hit rate: {metrics.hit_rate:.1f}%")
            >>> print(f"Error rate: {metrics.error_rate:.1f}%")
        """
        return self._metrics
    
    def reset_metrics(self) -> None:
        """Reset cache metrics to zero.
        
        Useful for testing or when starting a new monitoring period.
        
        Example:
            >>> cache.reset_metrics()
        """
        self._metrics.reset()
        logger.info("redis_cache_metrics_reset")
    
    async def get_size(self) -> int:
        """Get the current number of entries with our prefix in Redis.
        
        Returns:
            Number of cached entries with the configured prefix
        
        Example:
            >>> size = await cache.get_size()
            >>> print(f"Cache contains {size} entries")
        """
        try:
            pattern = f"{self.key_prefix}*"
            cursor = 0
            count = 0
            
            while True:
                cursor, keys = await self._client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                count += len(keys)
                
                if cursor == 0:
                    break
            
            return count
            
        except (RedisConnectionError, RedisError) as e:
            self._metrics.errors += 1
            if isinstance(e, RedisConnectionError):
                self._metrics.connection_errors += 1
            
            logger.error(
                "redis_cache_get_size_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return 0
    
    async def health_check(self) -> bool:
        """Check if Redis is healthy and operational.
        
        Performs a PING command to verify Redis connectivity.
        
        Returns:
            True if Redis is operational, False otherwise
        
        Example:
            >>> is_healthy = await cache.health_check()
        """
        try:
            # Use PING command to check connectivity
            ping_result = await self._client.ping()  # type: ignore[misc]
            
            is_healthy: bool = bool(ping_result is True)
            
            logger.debug("redis_cache_health_check", is_healthy=is_healthy)
            return is_healthy
            
        except (RedisConnectionError, RedisError) as e:
            self._metrics.errors += 1
            if isinstance(e, RedisConnectionError):
                self._metrics.connection_errors += 1
            
            logger.error(
                "redis_cache_health_check_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
    
    async def close(self) -> None:
        """Close Redis connection and cleanup resources.
        
        Should be called when shutting down the application.
        
        Example:
            >>> await cache.close()
        """
        try:
            await self._client.aclose()
            await self._pool.aclose()
            logger.info("redis_cache_repository_closed")
            
        except Exception as e:
            logger.error(
                "redis_cache_close_error",
                error=str(e),
                error_type=type(e).__name__,
            )
    
    async def __aenter__(self) -> "RedisCacheRepository":
        """Enter async context manager.
        
        Returns:
            Self for use in async with statement
        """
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
# Cache Factory
# =============================================================================

def create_cache_repository(
    cache_type: str = "memory",
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_db: int = 0,
    redis_password: str | None = None,
) -> CacheRepository:
    """Factory function to create cache repository based on configuration.
    
    This function allows switching between in-memory and Redis cache
    implementations based on configuration or environment.
    
    Args:
        cache_type: Type of cache ("memory" or "redis")
        redis_host: Redis server hostname (for redis type)
        redis_port: Redis server port (for redis type)
        redis_db: Redis database number (for redis type)
        redis_password: Redis password (for redis type)
    
    Returns:
        CacheRepository implementation (InMemoryCacheRepository or RedisCacheRepository)
    
    Raises:
        ValueError: If cache_type is invalid
        ImportError: If redis is selected but not installed
    
    Example:
        >>> # Use in-memory cache for development
        >>> cache = create_cache_repository(cache_type="memory")
        
        >>> # Use Redis for production
        >>> cache = create_cache_repository(
        ...     cache_type="redis",
        ...     redis_host="redis.example.com",
        ...     redis_port=6379,
        ...     redis_password="secret"
        ... )
    """
    if cache_type == "memory":
        from .cache_repository import InMemoryCacheRepository
        logger.info("creating_in_memory_cache_repository")
        return InMemoryCacheRepository()
    
    elif cache_type == "redis":
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis package is required for Redis cache. "
                "Install it with: pip install redis>=5.0.0"
            )
        
        logger.info(
            "creating_redis_cache_repository",
            host=redis_host,
            port=redis_port,
            db=redis_db,
        )
        return RedisCacheRepository(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
        )
    
    else:
        raise ValueError(
            f"Invalid cache_type: {cache_type}. "
            "Must be 'memory' or 'redis'"
        )


# =============================================================================
# Global Cache Instance
# =============================================================================

_global_cache: CacheRepository | None = None


def get_cache(
    cache_type: str | None = None,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_db: int = 0,
    redis_password: str | None = None,
) -> CacheRepository:
    """Get the global cache instance with lazy initialization.
    
    Creates the cache on first access. The cache type can be configured
    via the cache_type parameter or environment variable.
    
    Args:
        cache_type: Type of cache ("memory" or "redis", None = auto-detect from env)
        redis_host: Redis server hostname (for redis type)
        redis_port: Redis server port (for redis type)
        redis_db: Redis database number (for redis type)
        redis_password: Redis password (for redis type)
    
    Returns:
        Global CacheRepository instance
    
    Example:
        >>> # Auto-detect from environment
        >>> cache = get_cache()
        
        >>> # Explicitly use Redis
        >>> cache = get_cache(cache_type="redis", redis_host="localhost")
    """
    global _global_cache
    
    if _global_cache is None:
        # Auto-detect cache type from environment if not specified
        if cache_type is None:
            import os
            cache_type = os.getenv("CACHE_TYPE", "memory").lower()
        
        _global_cache = create_cache_repository(
            cache_type=cache_type,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            redis_password=redis_password,
        )
    
    return _global_cache


async def close_global_cache() -> None:
    """Close the global cache instance.
    
    Should be called during application shutdown to cleanup resources.
    
    Example:
        >>> await close_global_cache()
    """
    global _global_cache
    if _global_cache is not None:
        if hasattr(_global_cache, 'close'):
            await _global_cache.close()
        _global_cache = None

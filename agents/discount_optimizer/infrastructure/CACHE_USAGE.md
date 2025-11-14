# Cache Repository Usage Guide

## Overview

The `InMemoryCacheRepository` provides a type-safe, async caching layer with TTL support and performance metrics. It implements the `CacheRepository` protocol for dependency injection.

## Basic Usage

### Simple Get/Set Operations

```python
from agents.discount_optimizer.infrastructure import get_cache

# Get the global cache instance
cache = get_cache()

# Set a value with TTL
await cache.set("my_key", b"my_value", ttl_seconds=3600)

# Get a value
value = await cache.get("my_key")
if value:
    print(f"Found: {value}")
else:
    print("Cache miss")
```

### Using Context Manager

```python
from agents.discount_optimizer.infrastructure import InMemoryCacheRepository

async with InMemoryCacheRepository() as cache:
    await cache.set("key", b"value", ttl_seconds=300)
    result = await cache.get("key")
    # Cache automatically cleaned up on exit
```

## Caching Complex Objects

### Using Serialization Utilities

```python
from agents.discount_optimizer.infrastructure import (
    serialize_for_cache,
    deserialize_from_cache,
    get_cache,
)
from agents.discount_optimizer.domain.models import Location

cache = get_cache()

# Cache a Pydantic model
location = Location(latitude=55.6761, longitude=12.5683)
serialized = serialize_for_cache(location)
await cache.set("location:copenhagen", serialized, ttl_seconds=3600)

# Retrieve and deserialize
cached_data = await cache.get("location:copenhagen")
if cached_data:
    location = deserialize_from_cache(cached_data)
    print(f"Lat: {location.latitude}, Lon: {location.longitude}")
```

## Cache Key Generation

### Simple Key Generation

```python
from agents.discount_optimizer.infrastructure import generate_cache_key

# Generate deterministic key from arguments
key = generate_cache_key(55.6761, 12.5683, 5.0, prefix="discount:")
# Returns: "discount:a1b2c3d4e5f6g7h8"
```

### Dictionary-Based Key Generation

```python
from agents.discount_optimizer.infrastructure import generate_cache_key_from_dict

# Generate key from dictionary (order-independent)
params = {
    "latitude": 55.6761,
    "longitude": 12.5683,
    "radius": 5.0,
}
key = generate_cache_key_from_dict(params, prefix="discount:")
```

## Cache Metrics

### Monitoring Cache Performance

```python
cache = get_cache()

# Perform some operations
await cache.set("key1", b"value1", ttl_seconds=60)
await cache.get("key1")  # Hit
await cache.get("key2")  # Miss

# Get metrics
metrics = cache.get_metrics()
print(f"Hit rate: {metrics.hit_rate:.1f}%")
print(f"Miss rate: {metrics.miss_rate:.1f}%")
print(f"Total requests: {metrics.total_requests}")
print(f"Cache sets: {metrics.sets}")
print(f"Evictions: {metrics.evictions}")

# Reset metrics
cache.reset_metrics()
```

## Example: Caching API Responses

```python
from agents.discount_optimizer.infrastructure import (
    get_cache,
    generate_cache_key,
    serialize_for_cache,
    deserialize_from_cache,
)
from agents.discount_optimizer.domain.models import Location

async def fetch_discounts_with_cache(
    location: Location,
    radius_km: float,
    discount_repo,
) -> list[DiscountItem]:
    """Fetch discounts with caching."""
    cache = get_cache()
    
    # Generate cache key
    cache_key = generate_cache_key(
        location.latitude,
        location.longitude,
        radius_km,
        prefix="discount:",
    )
    
    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        return deserialize_from_cache(cached_data)
    
    # Cache miss - fetch from API
    discounts = await discount_repo.fetch_discounts(location, radius_km)
    
    # Store in cache
    serialized = serialize_for_cache(discounts)
    await cache.set(cache_key, serialized, ttl_seconds=3600)
    
    return discounts
```

## Configuration

Cache behavior is controlled by settings in `config.py`:

```python
# Enable/disable caching
enable_caching: bool = True

# Default TTL for cached items
cache_ttl_seconds: int = 3600  # 1 hour
```

## Health Checks

```python
cache = get_cache()

# Check if cache is operational
is_healthy = await cache.health_check()
if not is_healthy:
    print("Cache is not operational!")
```

## Cleanup

```python
from agents.discount_optimizer.infrastructure import close_global_cache

# Close global cache on application shutdown
await close_global_cache()
```

## Background Cleanup

The cache automatically runs a background task that removes expired entries every 60 seconds. This prevents unbounded memory growth.

The cleanup task starts automatically when:
- Using the cache in an async context manager
- Calling `_start_cleanup_task()` manually in an async context

## Thread Safety

All cache operations are protected by an async lock (`asyncio.Lock`), making the cache safe for concurrent access from multiple async tasks.

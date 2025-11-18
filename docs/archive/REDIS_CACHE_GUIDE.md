# Redis Cache Guide

## Overview

The Shopping Optimizer supports two cache backends:
- **In-Memory Cache**: Single-instance deployment (default)
- **Redis Cache**: Multi-instance deployment with distributed cache

This guide explains how to configure and deploy Redis cache for production environments.

## When to Use Redis Cache

Use Redis cache when:
- Running multiple application instances (horizontal scaling)
- Deploying to cloud platforms (Google Cloud Run, AWS ECS, etc.)
- Need cache persistence across restarts
- Want to share cache across different services
- Need cache monitoring and management tools

Use in-memory cache when:
- Running a single application instance
- Development or testing environments
- Minimal infrastructure requirements
- No need for cache persistence

## Configuration

### Environment Variables

Add these variables to your `.env` file:

```bash
# Cache backend type
CACHE_TYPE=redis

# Redis connection settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_redis_password

# Redis connection pool settings
REDIS_MAX_CONNECTIONS=10
REDIS_SOCKET_TIMEOUT=5.0
REDIS_SOCKET_CONNECT_TIMEOUT=5.0

# Cache key prefix (namespace isolation)
REDIS_KEY_PREFIX=shopping_optimizer:
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_TYPE` | `memory` | Cache backend: `memory` or `redis` |
| `REDIS_HOST` | `localhost` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_DB` | `0` | Redis database number (0-15) |
| `REDIS_PASSWORD` | None | Redis password (optional) |
| `REDIS_MAX_CONNECTIONS` | `10` | Maximum connections in pool |
| `REDIS_SOCKET_TIMEOUT` | `5.0` | Socket timeout in seconds |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | `5.0` | Connection timeout in seconds |
| `REDIS_KEY_PREFIX` | `shopping_optimizer:` | Prefix for all cache keys |

## Local Development with Redis

### Using Docker

The easiest way to run Redis locally is with Docker:

```bash
# Start Redis container
docker run -d \
  --name redis-cache \
  -p 6379:6379 \
  redis:7-alpine

# Verify Redis is running
docker exec redis-cache redis-cli ping
# Should return: PONG
```

### Using Docker Compose

Add Redis to your `docker-compose.yml`:

```yaml
services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - CACHE_TYPE=redis
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes

volumes:
  redis-data:
```

### Using Homebrew (macOS)

```bash
# Install Redis
brew install redis

# Start Redis service
brew services start redis

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

## Production Deployment

### Google Cloud Memorystore (Redis)

1. **Create Redis instance:**

```bash
gcloud redis instances create shopping-optimizer-cache \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0 \
  --tier=basic
```

2. **Get connection details:**

```bash
gcloud redis instances describe shopping-optimizer-cache \
  --region=us-central1 \
  --format="get(host,port)"
```

3. **Configure Cloud Run:**

```bash
gcloud run deploy shopping-optimizer \
  --image gcr.io/PROJECT_ID/shopping-optimizer \
  --set-env-vars CACHE_TYPE=redis \
  --set-env-vars REDIS_HOST=REDIS_IP \
  --set-env-vars REDIS_PORT=6379 \
  --vpc-connector=CONNECTOR_NAME
```

### AWS ElastiCache (Redis)

1. **Create Redis cluster:**

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id shopping-optimizer-cache \
  --engine redis \
  --cache-node-type cache.t3.micro \
  --num-cache-nodes 1 \
  --engine-version 7.0
```

2. **Get endpoint:**

```bash
aws elasticache describe-cache-clusters \
  --cache-cluster-id shopping-optimizer-cache \
  --show-cache-node-info
```

3. **Configure environment:**

```bash
export CACHE_TYPE=redis
export REDIS_HOST=your-cluster.cache.amazonaws.com
export REDIS_PORT=6379
```

### Redis Cloud

1. Sign up at [Redis Cloud](https://redis.com/try-free/)
2. Create a new database
3. Copy connection details
4. Configure environment variables:

```bash
CACHE_TYPE=redis
REDIS_HOST=redis-12345.c123.us-east-1-1.ec2.cloud.redislabs.com
REDIS_PORT=12345
REDIS_PASSWORD=your_password
```

## Monitoring and Health Checks

### Health Check Endpoint

The application provides a detailed health check that includes Redis status:

```bash
curl http://localhost:3000/health/detailed
```

Response:
```json
{
  "status": "healthy",
  "dependencies": {
    "cache_repository": {
      "status": "healthy",
      "message": "Service is operational"
    }
  }
}
```

### Cache Metrics

View cache performance metrics:

```bash
curl http://localhost:3000/metrics
```

Key metrics:
- `cache_hit_rate`: Percentage of cache hits
- `cache_miss_rate`: Percentage of cache misses
- `cache_error_rate`: Percentage of cache errors
- `cache_connection_errors`: Number of connection failures

### Redis CLI Monitoring

Connect to Redis and monitor operations:

```bash
# Connect to Redis
redis-cli -h REDIS_HOST -p REDIS_PORT

# Monitor all commands
MONITOR

# View cache keys
KEYS shopping_optimizer:*

# Get cache statistics
INFO stats

# Check memory usage
INFO memory
```

## Troubleshooting

### Connection Errors

**Problem:** Application can't connect to Redis

**Solutions:**
1. Verify Redis is running: `redis-cli ping`
2. Check firewall rules allow port 6379
3. Verify `REDIS_HOST` and `REDIS_PORT` are correct
4. Check VPC/network connectivity in cloud environments
5. Verify Redis password if authentication is enabled

### High Memory Usage

**Problem:** Redis consuming too much memory

**Solutions:**
1. Reduce `CACHE_TTL_SECONDS` to expire entries faster
2. Set Redis maxmemory policy:
   ```bash
   redis-cli CONFIG SET maxmemory 256mb
   redis-cli CONFIG SET maxmemory-policy allkeys-lru
   ```
3. Monitor cache size: `redis-cli INFO memory`
4. Clear cache if needed: `redis-cli FLUSHDB`

### Performance Issues

**Problem:** Slow cache operations

**Solutions:**
1. Increase `REDIS_MAX_CONNECTIONS` for higher concurrency
2. Use Redis cluster for horizontal scaling
3. Enable Redis persistence only if needed (AOF/RDB)
4. Monitor slow queries: `redis-cli SLOWLOG GET 10`
5. Check network latency between app and Redis

### Graceful Degradation

The application is designed to handle Redis failures gracefully:
- Cache misses return `None` instead of raising errors
- Failed cache writes are logged but don't block requests
- Automatic retry with exponential backoff (3 attempts)
- Health checks report degraded status but keep serving requests

## Cache Key Structure

All cache keys use the configured prefix for namespace isolation:

```
shopping_optimizer:discount:55.6761:12.5683:5.0
shopping_optimizer:geocode:Copenhagen
shopping_optimizer:stores:55.6761:12.5683:20.0
```

This allows:
- Multiple applications to share the same Redis instance
- Easy cache clearing by prefix
- Clear identification of cache entries

## Best Practices

1. **Use Redis in production**: Always use Redis for multi-instance deployments
2. **Set appropriate TTL**: Balance freshness vs cache hit rate (default: 1 hour)
3. **Monitor metrics**: Track hit rate, error rate, and connection health
4. **Use connection pooling**: Default pool size (10) works for most cases
5. **Enable persistence**: Use AOF or RDB for cache persistence if needed
6. **Secure Redis**: Always use password authentication in production
7. **Network isolation**: Deploy Redis in private network/VPC
8. **Regular backups**: Backup Redis data for disaster recovery
9. **Capacity planning**: Monitor memory usage and scale as needed
10. **Test failover**: Verify application handles Redis failures gracefully

## Migration from In-Memory to Redis

To migrate from in-memory cache to Redis:

1. **Deploy Redis instance** (see Production Deployment section)

2. **Update environment variables:**
   ```bash
   CACHE_TYPE=redis
   REDIS_HOST=your-redis-host
   REDIS_PORT=6379
   ```

3. **Deploy application** with new configuration

4. **Verify health check:**
   ```bash
   curl http://your-app/health/detailed
   ```

5. **Monitor metrics** for cache performance

6. **No code changes required** - the factory automatically creates the correct cache implementation

## Performance Comparison

| Metric | In-Memory | Redis (Local) | Redis (Cloud) |
|--------|-----------|---------------|---------------|
| Latency | <1ms | 1-2ms | 5-10ms |
| Throughput | Very High | High | Medium |
| Scalability | Single instance | Multi-instance | Multi-instance |
| Persistence | No | Optional | Yes |
| Cost | Free | Infrastructure | Service fee |

## Support

For issues or questions:
- Check application logs for detailed error messages
- Review Redis logs: `redis-cli MONITOR`
- Verify configuration with health check endpoint
- Check metrics for performance indicators
- Consult Redis documentation: https://redis.io/docs/

## References

- [Redis Documentation](https://redis.io/docs/)
- [Google Cloud Memorystore](https://cloud.google.com/memorystore/docs/redis)
- [AWS ElastiCache](https://docs.aws.amazon.com/elasticache/)
- [Redis Cloud](https://redis.com/redis-enterprise-cloud/overview/)
- [redis-py Documentation](https://redis-py.readthedocs.io/)

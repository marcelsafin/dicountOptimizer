# Docker Deployment Guide

This guide covers deploying the Shopping Optimizer using Docker and Docker Compose for both local development and production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Docker Image Details](#docker-image-details)
- [Local Development with Docker Compose](#local-development-with-docker-compose)
- [Production Deployment](#production-deployment)
- [Configuration](#configuration)
- [Health Checks](#health-checks)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)

## Prerequisites

- Docker 20.10+ installed
- Docker Compose 2.0+ installed
- `.env` file configured with required API keys (see `.env.example`)

### Verify Installation

```bash
docker --version
docker-compose --version
```

## Quick Start

### 1. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
# Required: GOOGLE_API_KEY
# Optional: SALLING_API_KEY, GOOGLE_MAPS_API_KEY
nano .env
```

### 2. Start Services

```bash
# Start all services (app + Redis)
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 3. Access Application

- **Web UI**: http://localhost:3000
- **Health Check**: http://localhost:3000/health
- **Detailed Health**: http://localhost:3000/health/detailed
- **Redis**: localhost:6379

### 4. Stop Services

```bash
# Stop services (preserves data)
docker-compose down

# Stop and remove volumes (clears Redis data)
docker-compose down -v
```

## Docker Image Details

### Multi-Stage Build

The Dockerfile uses a multi-stage build to optimize image size:

1. **Builder Stage**: Installs build dependencies and Python packages
2. **Runtime Stage**: Copies only runtime dependencies and application code

**Benefits:**
- Smaller image size (~200MB vs ~1GB)
- Faster deployment and startup
- Improved security (no build tools in production)

### Image Layers

```
python:3.11-slim (base)
├── Runtime dependencies (curl)
├── Python packages (from builder)
├── Application code
└── Non-root user (appuser)
```

### Build the Image

```bash
# Build image
docker build -t shopping-optimizer:latest .

# Build with custom tag
docker build -t shopping-optimizer:v1.0.0 .

# Build with build args
docker build --build-arg PYTHON_VERSION=3.11 -t shopping-optimizer .
```

### Inspect Image

```bash
# Check image size
docker images shopping-optimizer

# Inspect image layers
docker history shopping-optimizer:latest

# Scan for vulnerabilities
docker scan shopping-optimizer:latest
```

## Local Development with Docker Compose

### Architecture

```
┌─────────────────────────────────────┐
│   Docker Compose Network            │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │     App      │  │    Redis    │ │
│  │  Port: 3000  │──│  Port: 6379 │ │
│  └──────────────┘  └─────────────┘ │
│         │                           │
└─────────┼───────────────────────────┘
          │
    Host Machine
    localhost:3000
```

### Services

#### App Service

- **Image**: Built from local Dockerfile
- **Port**: 3000 (mapped to host)
- **Volumes**: Code mounted for hot reload
- **Environment**: Development mode
- **Workers**: 2 (configurable via WORKERS env var)

#### Redis Service

- **Image**: redis:7-alpine
- **Port**: 6379 (mapped to host)
- **Persistence**: Volume-backed (redis-data)
- **Memory**: 256MB max with LRU eviction
- **Health Check**: redis-cli ping

### Development Workflow

```bash
# 1. Start services
docker-compose up -d

# 2. Make code changes (auto-reloads)
# Edit files in agents/, templates/, static/, or app.py

# 3. View logs
docker-compose logs -f app

# 4. Restart app only (if needed)
docker-compose restart app

# 5. Access Redis CLI
docker-compose exec redis redis-cli

# 6. Check Redis data
docker-compose exec redis redis-cli KEYS "*"

# 7. Stop services
docker-compose down
```

### Hot Reload

Code changes are automatically detected because volumes are mounted:

```yaml
volumes:
  - ./agents:/app/agents
  - ./templates:/app/templates
  - ./static:/app/static
  - ./app.py:/app/app.py
```

**Note**: Changes to `requirements.txt` require rebuilding:

```bash
docker-compose build app
docker-compose up -d
```

## Production Deployment

### Standalone Docker

For production without Docker Compose:

```bash
# 1. Build production image
docker build -t shopping-optimizer:prod .

# 2. Run Redis (if not using external Redis)
docker run -d \
  --name redis \
  --restart unless-stopped \
  -v redis-data:/data \
  redis:7-alpine redis-server --appendonly yes

# 3. Run application
docker run -d \
  --name shopping-optimizer \
  --restart unless-stopped \
  -p 3000:3000 \
  --env-file .env \
  -e REDIS_URL=redis://redis:6379/0 \
  -e ENVIRONMENT=production \
  -e LOG_LEVEL=INFO \
  -e WORKERS=4 \
  --link redis:redis \
  shopping-optimizer:prod
```

### Docker Compose Production

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    restart: always
    networks:
      - app-network

  app:
    image: shopping-optimizer:prod
    ports:
      - "3000:3000"
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
      - WORKERS=4
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env.production
    depends_on:
      - redis
    restart: always
    networks:
      - app-network

volumes:
  redis-data:

networks:
  app-network:
```

Deploy:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Cloud Deployment

#### Google Cloud Run

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for Cloud Run deployment.

#### AWS ECS

```bash
# 1. Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag shopping-optimizer:latest <account>.dkr.ecr.us-east-1.amazonaws.com/shopping-optimizer:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/shopping-optimizer:latest

# 2. Create ECS task definition and service
# Use AWS Console or CLI
```

#### Azure Container Instances

```bash
# 1. Push to ACR
az acr login --name <registry-name>
docker tag shopping-optimizer:latest <registry-name>.azurecr.io/shopping-optimizer:latest
docker push <registry-name>.azurecr.io/shopping-optimizer:latest

# 2. Deploy to ACI
az container create \
  --resource-group <resource-group> \
  --name shopping-optimizer \
  --image <registry-name>.azurecr.io/shopping-optimizer:latest \
  --ports 3000 \
  --environment-variables ENVIRONMENT=production
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | 3000 | HTTP port to listen on |
| `WORKERS` | No | 4 | Number of Gunicorn workers |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ENVIRONMENT` | No | dev | Environment (dev, staging, production) |
| `GOOGLE_API_KEY` | Yes | - | Google Gemini API key |
| `SALLING_API_KEY` | No | - | Salling Group API key |
| `REDIS_URL` | No | - | Redis connection URL |
| `CACHE_TTL_SECONDS` | No | 3600 | Cache TTL in seconds |
| `ENABLE_AI_MEAL_SUGGESTIONS` | No | true | Enable AI meal suggestions |
| `ENABLE_CACHING` | No | true | Enable caching |
| `ENABLE_METRICS` | No | true | Enable metrics collection |

### Worker Configuration

Calculate optimal workers:

```
workers = (2 * CPU_cores) + 1
```

Examples:
- 2 cores → 5 workers
- 4 cores → 9 workers
- 8 cores → 17 workers

Set via environment variable:

```bash
docker run -e WORKERS=8 shopping-optimizer
```

### Memory Configuration

Recommended memory allocation:

- **Development**: 512MB minimum
- **Production**: 1GB minimum (2GB recommended)
- **Redis**: 256MB-512MB

Docker resource limits:

```bash
docker run --memory=1g --memory-swap=1g shopping-optimizer
```

## Health Checks

### Built-in Health Checks

The Docker image includes health checks:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-3000}/health || exit 1
```

### Health Endpoints

#### Basic Health Check

```bash
curl http://localhost:3000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-16T12:00:00Z"
}
```

#### Detailed Health Check

```bash
curl http://localhost:3000/health/detailed
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-16T12:00:00Z",
  "dependencies": {
    "geocoding_service": {
      "status": "healthy",
      "response_time_ms": 45
    },
    "discount_repository": {
      "status": "healthy",
      "response_time_ms": 120
    },
    "cache_repository": {
      "status": "healthy",
      "response_time_ms": 5
    }
  }
}
```

### Monitor Health

```bash
# Check container health status
docker ps

# View health check logs
docker inspect --format='{{json .State.Health}}' shopping-optimizer-app | jq

# Continuous monitoring
watch -n 5 'curl -s http://localhost:3000/health | jq'
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs app

# Common issues:
# 1. Missing .env file
# 2. Invalid API keys
# 3. Port 3000 already in use
```

### Port Already in Use

```bash
# Find process using port 3000
lsof -i :3000

# Kill process
kill -9 <PID>

# Or use different port
docker-compose up -d -e PORT=3001
```

### Redis Connection Failed

```bash
# Check Redis is running
docker-compose ps redis

# Check Redis health
docker-compose exec redis redis-cli ping

# View Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

### Out of Memory

```bash
# Check container memory usage
docker stats

# Increase memory limit
docker run --memory=2g shopping-optimizer

# Or in docker-compose.yml:
services:
  app:
    mem_limit: 2g
```

### Slow Performance

```bash
# Check resource usage
docker stats shopping-optimizer-app

# Increase workers
docker-compose up -d -e WORKERS=8

# Check Redis cache hit rate
docker-compose exec redis redis-cli INFO stats | grep hit_rate
```

### Build Failures

```bash
# Clear build cache
docker-compose build --no-cache app

# Check disk space
df -h

# Prune unused images
docker system prune -a
```

## Performance Tuning

### Optimize Build Time

```bash
# Use BuildKit for faster builds
DOCKER_BUILDKIT=1 docker build -t shopping-optimizer .

# Use build cache
docker build --cache-from shopping-optimizer:latest -t shopping-optimizer .
```

### Optimize Runtime

1. **Worker Tuning**: Adjust `WORKERS` based on CPU cores
2. **Connection Pooling**: Configured in application (httpx)
3. **Redis Caching**: Enable with `ENABLE_CACHING=true`
4. **Memory Limits**: Set appropriate limits to prevent OOM

### Monitoring

```bash
# Real-time stats
docker stats shopping-optimizer-app

# Export metrics (if Prometheus enabled)
curl http://localhost:3000/metrics
```

### Logging

```bash
# View logs
docker-compose logs -f app

# Filter logs
docker-compose logs app | grep ERROR

# Export logs
docker-compose logs app > app.log
```

## Best Practices

### Security

1. **Never commit `.env` files** with real API keys
2. **Use secrets management** in production (AWS Secrets Manager, etc.)
3. **Run as non-root user** (already configured)
4. **Scan images** for vulnerabilities regularly
5. **Keep base images updated**

### Production Checklist

- [ ] Use production-ready `.env` file
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure appropriate `WORKERS` count
- [ ] Set memory limits
- [ ] Enable health checks
- [ ] Configure log aggregation
- [ ] Set up monitoring and alerts
- [ ] Use external Redis (not in-container)
- [ ] Configure auto-restart policies
- [ ] Set up backup for Redis data
- [ ] Use HTTPS/TLS termination (load balancer)
- [ ] Configure rate limiting

### Maintenance

```bash
# Update base image
docker pull python:3.11-slim
docker-compose build --no-cache

# Clean up
docker system prune -a --volumes

# Backup Redis data
docker-compose exec redis redis-cli SAVE
docker cp shopping-optimizer-redis:/data/dump.rdb ./backup/

# Restore Redis data
docker cp ./backup/dump.rdb shopping-optimizer-redis:/data/
docker-compose restart redis
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [Architecture Documentation](./ARCHITECTURE.md)
- [API Reference](./API_REFERENCE.md)

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Review health checks: `curl http://localhost:3000/health/detailed`
3. Check GitHub issues
4. Contact support team

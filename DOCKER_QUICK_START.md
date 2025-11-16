# Docker Quick Start Guide

Get the Shopping Optimizer running with Docker in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- API keys ready (Google Gemini required)

## Steps

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 2. Start Services

```bash
docker-compose up -d
```

This starts:
- Shopping Optimizer app on port 3000
- Redis cache on port 6379

### 3. Verify

```bash
# Check services are running
docker-compose ps

# Check health
curl http://localhost:3000/health

# View logs
docker-compose logs -f app
```

### 4. Use the App

Open http://localhost:3000 in your browser.

### 5. Stop Services

```bash
docker-compose down
```

## Common Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Restart app
docker-compose restart app

# Stop services
docker-compose down

# Stop and remove data
docker-compose down -v

# Rebuild after code changes
docker-compose build app
docker-compose up -d
```

## Troubleshooting

### Port 3000 in use?

```bash
# Use different port
PORT=3001 docker-compose up -d
```

### Container won't start?

```bash
# Check logs
docker-compose logs app

# Common fixes:
# - Verify .env file exists
# - Check API keys are valid
# - Ensure port 3000 is available
```

### Need to reset everything?

```bash
docker-compose down -v
docker-compose up -d
```

## Next Steps

- Read full documentation: [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md)
- Configure production: [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)
- Learn the architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Production Deployment

For production, see [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md) for:
- Cloud deployment (Google Cloud Run, AWS, Azure)
- Performance tuning
- Security best practices
- Monitoring and logging

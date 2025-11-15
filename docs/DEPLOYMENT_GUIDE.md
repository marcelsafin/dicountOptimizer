# Deployment Guide - Shopping Optimizer

## Overview

This guide covers deploying the Shopping Optimizer to production environments. The application is designed for cloud-native deployment with async/await performance optimizations (Requirements 8.2, 8.6).

## ⚠️ Critical: ASGI Server Required

**DO NOT** use `python app.py` or `flask run` in any environment. These are blocking, single-threaded servers that will:
- Destroy all async performance optimizations
- Limit throughput to ~1 request/second
- Block the event loop during I/O operations
- Waste all the work from Phase 2 (Tasks 8-14)

**ALWAYS** use Gunicorn with Uvicorn workers for async support.

## Local Development

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start with Gunicorn + Uvicorn (async-capable)
gunicorn app:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:3000 \
  --reload
```

Access at: http://localhost:3000

### With Docker Compose (Recommended)

Includes Redis for testing production cache:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

## Production Deployment

### Option 1: Google Cloud Run (Recommended)

Cloud Run is ideal for this application because:
- Automatic scaling based on traffic
- Pay-per-use pricing
- Built-in load balancing
- Managed SSL certificates
- Integrated with Google Secret Manager

#### Prerequisites

```bash
# Install Google Cloud SDK
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

#### Build and Deploy

```bash
# Build container image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/shopping-optimizer

# Deploy to Cloud Run
gcloud run deploy shopping-optimizer \
  --image gcr.io/YOUR_PROJECT_ID/shopping-optimizer \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 2 \
  --timeout 120 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars ENVIRONMENT=production \
  --set-secrets GOOGLE_API_KEY=google-api-key:latest,SALLING_GROUP_API_KEY=salling-api-key:latest
```

#### Configure Secrets

```bash
# Create secrets in Secret Manager
echo -n "your-google-api-key" | gcloud secrets create google-api-key --data-file=-
echo -n "your-salling-api-key" | gcloud secrets create salling-api-key --data-file=-

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding google-api-key \
  --member=serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor

gcloud secrets add-iam-policy-binding salling-api-key \
  --member=serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

### Option 2: Docker on Any Platform

#### Build Image

```bash
# Build production image
docker build -t shopping-optimizer:latest .

# Test locally
docker run -p 3000:3000 --env-file .env shopping-optimizer:latest
```

#### Push to Registry

```bash
# Tag for your registry
docker tag shopping-optimizer:latest YOUR_REGISTRY/shopping-optimizer:latest

# Push
docker push YOUR_REGISTRY/shopping-optimizer:latest
```

#### Deploy to Kubernetes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shopping-optimizer
spec:
  replicas: 3
  selector:
    matchLabels:
      app: shopping-optimizer
  template:
    metadata:
      labels:
        app: shopping-optimizer
    spec:
      containers:
      - name: app
        image: YOUR_REGISTRY/shopping-optimizer:latest
        ports:
        - containerPort: 3000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: PORT
          value: "3000"
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        envFrom:
        - secretRef:
            name: shopping-optimizer-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: shopping-optimizer
spec:
  selector:
    app: shopping-optimizer
  ports:
  - port: 80
    targetPort: 3000
  type: LoadBalancer
```

### Option 3: Traditional VPS/VM

#### Using systemd

Create `/etc/systemd/system/shopping-optimizer.service`:

```ini
[Unit]
Description=Shopping Optimizer Service
After=network.target

[Service]
Type=notify
User=appuser
Group=appuser
WorkingDirectory=/opt/shopping-optimizer
Environment="PATH=/opt/shopping-optimizer/.venv/bin"
EnvironmentFile=/opt/shopping-optimizer/.env
ExecStart=/opt/shopping-optimizer/.venv/bin/gunicorn app:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:3000 \
  --timeout 120 \
  --graceful-timeout 30 \
  --access-logfile /var/log/shopping-optimizer/access.log \
  --error-logfile /var/log/shopping-optimizer/error.log \
  --log-level info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable shopping-optimizer
sudo systemctl start shopping-optimizer
sudo systemctl status shopping-optimizer
```

## Production Configuration

### Environment Variables

Required in production:

```bash
# Environment
ENVIRONMENT=production
DEBUG=false

# API Keys (use Secret Manager in production)
GOOGLE_API_KEY=your_key_here
SALLING_GROUP_API_KEY=your_key_here

# Redis (Task 25 - when implemented)
REDIS_URL=redis://redis-host:6379/0

# Performance
CACHE_TTL_SECONDS=3600
API_TIMEOUT_SECONDS=30
MAX_CONCURRENT_REQUESTS=10

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Feature Flags
ENABLE_AI_MEAL_SUGGESTIONS=true
ENABLE_CACHING=true
ENABLE_METRICS=true
```

### Gunicorn Configuration

Recommended production settings:

```bash
gunicorn app:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers $(( 2 * $(nproc) + 1 )) \  # 2 * CPU cores + 1
  --bind 0.0.0.0:$PORT \
  --timeout 120 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  --worker-tmp-dir /dev/shm  # Use RAM for worker heartbeat
```

**Worker Count**: Formula is `(2 * CPU_CORES) + 1`
- 2 CPU cores → 5 workers
- 4 CPU cores → 9 workers
- 8 CPU cores → 17 workers

### Nginx Reverse Proxy (Optional)

If using Nginx as reverse proxy:

```nginx
upstream shopping_optimizer {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://shopping_optimizer;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running requests
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    location /health {
        proxy_pass http://shopping_optimizer/health;
        access_log off;
    }
}
```

## Monitoring and Observability

### Health Checks

The application provides multiple health check endpoints:

```bash
# Basic health check
curl http://localhost:3000/health

# Detailed health check (checks all dependencies)
curl http://localhost:3000/health/detailed

# Metrics (JSON)
curl http://localhost:3000/metrics

# Metrics (Prometheus format)
curl http://localhost:3000/metrics/prometheus
```

### Prometheus Integration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'shopping-optimizer'
    scrape_interval: 15s
    static_configs:
      - targets: ['shopping-optimizer:3000']
    metrics_path: '/metrics/prometheus'
```

### Grafana Dashboard

Import the provided dashboard (when Task 31 is complete):
- Agent execution metrics
- API call latency
- Cache hit rate
- Error rates

## Scaling Guidelines

### Horizontal Scaling

The application is stateless (except for in-memory cache) and can be scaled horizontally:

```bash
# Cloud Run (automatic)
gcloud run services update shopping-optimizer \
  --min-instances 2 \
  --max-instances 20

# Kubernetes
kubectl scale deployment shopping-optimizer --replicas=5
```

**Note**: In-memory cache will be replaced with Redis in Task 25 for proper multi-instance caching.

### Vertical Scaling

Resource recommendations based on load:

| Load Level | Memory | CPU | Workers |
|------------|--------|-----|---------|
| Light (<10 req/s) | 512Mi | 0.5 | 2 |
| Medium (10-50 req/s) | 1Gi | 1.0 | 4 |
| Heavy (50-100 req/s) | 2Gi | 2.0 | 8 |
| Very Heavy (>100 req/s) | 4Gi | 4.0 | 16 |

## Troubleshooting

### Application Won't Start

```bash
# Check logs
docker logs shopping-optimizer-app

# Common issues:
# 1. Missing API keys
# 2. Port already in use
# 3. Missing dependencies
```

### Poor Performance

```bash
# Check if using ASGI server
ps aux | grep gunicorn

# Should see: uvicorn.workers.UvicornWorker
# Should NOT see: python app.py or flask run

# Check metrics
curl http://localhost:3000/metrics/summary
```

### High Memory Usage

```bash
# Reduce worker count
gunicorn app:app -k uvicorn.workers.UvicornWorker --workers 2

# Enable max-requests for worker recycling
gunicorn app:app -k uvicorn.workers.UvicornWorker --max-requests 1000
```

### Connection Pool Exhaustion

```bash
# Increase max connections in .env
MAX_CONCURRENT_REQUESTS=20

# Or reduce worker count to limit total connections
```

## Security Checklist

- [ ] API keys stored in Secret Manager (not in code)
- [ ] HTTPS enabled (SSL/TLS certificates)
- [ ] Security headers configured (X-Frame-Options, etc.)
- [ ] Rate limiting enabled (at load balancer level)
- [ ] Non-root user in Docker container
- [ ] Minimal Docker image (no unnecessary packages)
- [ ] Regular security updates (base image, dependencies)
- [ ] Firewall rules configured (only necessary ports open)
- [ ] Logging enabled (for audit trail)
- [ ] Monitoring and alerting configured

## Next Steps

After deployment:

1. **Task 25**: Migrate to Redis cache for multi-instance support
2. **Task 26**: Fix frontend integration with new API
3. **Task 27**: Set up CI/CD pipeline
4. **Task 31**: Configure Grafana dashboards

## Support

For deployment issues:
- Check logs: `docker logs` or Cloud Run logs
- Review metrics: `/metrics/summary` endpoint
- Verify health: `/health/detailed` endpoint
- Check configuration: Environment variables and secrets

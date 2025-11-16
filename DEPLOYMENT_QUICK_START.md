# Cloud Run Deployment - Quick Start Guide

This guide provides a quick reference for deploying Shopping Optimizer to Google Cloud Run.

## Prerequisites

- Google Cloud Project with billing enabled
- gcloud CLI installed and authenticated
- API keys: Google API key and Salling Group API key

## Quick Deployment (3 Steps)

### Step 1: Set Up Infrastructure

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Run infrastructure setup script
./scripts/setup-gcp-infrastructure.sh
```

This script will:
- Enable required GCP APIs
- Create VPC network and Redis instance
- Create VPC connector
- Set up service account and secrets
- Configure IAM permissions

**Time**: ~10-15 minutes (Redis creation takes the longest)

### Step 2: Deploy to Staging (Optional)

```bash
# Deploy to staging environment
./scripts/deploy-staging.sh
```

Configuration:
- Memory: 1Gi
- CPU: 1
- Min instances: 0 (scale to zero)
- Max instances: 3
- Log level: DEBUG

### Step 3: Deploy to Production

```bash
# Deploy to production environment
./scripts/deploy-production.sh
```

Configuration:
- Memory: 2Gi
- CPU: 2
- Min instances: 1 (always warm)
- Max instances: 10
- Log level: INFO

## Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe shopping-optimizer \
  --region=us-central1 \
  --format="value(status.url)")

# Test health endpoint
curl $SERVICE_URL/health

# Test detailed health (includes dependencies)
curl $SERVICE_URL/health/detailed

# View metrics
curl $SERVICE_URL/metrics/summary
```

## Manual Deployment (Alternative)

If you prefer manual control:

```bash
# Build and deploy in one command
gcloud builds submit --config cloudbuild.yaml

# Or build locally and deploy
docker build -t gcr.io/$PROJECT_ID/shopping-optimizer:latest .
docker push gcr.io/$PROJECT_ID/shopping-optimizer:latest

gcloud run deploy shopping-optimizer \
  --image=gcr.io/$PROJECT_ID/shopping-optimizer:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --max-instances=10 \
  --min-instances=1 \
  --vpc-connector=shopping-optimizer-vpc \
  --set-secrets="GOOGLE_API_KEY=google-api-key:latest,SALLING_GROUP_API_KEY=salling-api-key:latest,REDIS_URL=redis-url:latest"
```

## Common Commands

### View Logs

```bash
# Stream logs in real-time
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=shopping-optimizer"

# View recent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=shopping-optimizer" --limit=50

# View errors only
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=shopping-optimizer AND severity>=ERROR" --limit=20
```

### Update Configuration

```bash
# Update scaling settings
gcloud run services update shopping-optimizer \
  --region=us-central1 \
  --min-instances=2 \
  --max-instances=20

# Update resources
gcloud run services update shopping-optimizer \
  --region=us-central1 \
  --memory=4Gi \
  --cpu=4

# Update environment variables
gcloud run services update shopping-optimizer \
  --region=us-central1 \
  --set-env-vars="LOG_LEVEL=DEBUG"
```

### Rollback

```bash
# List revisions
gcloud run revisions list \
  --service=shopping-optimizer \
  --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic shopping-optimizer \
  --region=us-central1 \
  --to-revisions=REVISION_NAME=100
```

## Custom Domain Setup

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service=shopping-optimizer \
  --domain=shopping.yourdomain.com \
  --region=us-central1

# Get DNS records to configure
gcloud run domain-mappings describe \
  --domain=shopping.yourdomain.com \
  --region=us-central1
```

Then add the DNS records to your domain registrar.

## Monitoring

### Cloud Console

1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Click on `shopping-optimizer` service
3. View metrics, logs, and revisions

### Application Metrics

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe shopping-optimizer \
  --region=us-central1 \
  --format="value(status.url)")

# View metrics summary
curl $SERVICE_URL/metrics/summary

# View full metrics (JSON)
curl $SERVICE_URL/metrics

# View Prometheus format
curl $SERVICE_URL/metrics/prometheus
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs for errors
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=shopping-optimizer AND severity>=ERROR" --limit=20

# Check service status
gcloud run services describe shopping-optimizer --region=us-central1
```

### Can't Connect to Redis

```bash
# Verify VPC connector
gcloud compute networks vpc-access connectors describe shopping-optimizer-vpc --region=us-central1

# Verify Redis instance
gcloud redis instances describe shopping-optimizer-redis --region=us-central1

# Check Redis URL secret
gcloud secrets versions access latest --secret=redis-url
```

### High Latency

```bash
# Increase min instances to reduce cold starts
gcloud run services update shopping-optimizer \
  --region=us-central1 \
  --min-instances=2

# Increase resources
gcloud run services update shopping-optimizer \
  --region=us-central1 \
  --memory=4Gi \
  --cpu=4
```

## Cost Estimation

### Production (24/7)
- Cloud Run: ~$50-150/month
- Redis (Standard HA): ~$150/month
- VPC Connector: ~$10/month
- **Total: ~$210-310/month**

### Staging (scale to zero)
- Cloud Run: ~$10-30/month
- Redis (Basic): ~$50/month
- VPC Connector: ~$10/month
- **Total: ~$70-90/month**

## Environment Variables

Key environment variables (set via Cloud Run):

```bash
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
CACHE_TYPE=redis

# Agent configuration
AGENT_MODEL=gemini-2.0-flash-exp
AGENT_TEMPERATURE=0.7

# Feature flags
ENABLE_AI_MEAL_SUGGESTIONS=true
ENABLE_CACHING=true
ENABLE_METRICS=true

# Secrets (from Secret Manager)
GOOGLE_API_KEY=<from secret>
SALLING_GROUP_API_KEY=<from secret>
REDIS_URL=<from secret>
```

## CI/CD Setup (Optional)

Set up automatic deployments on git push:

```bash
# Create trigger for production (main branch)
gcloud builds triggers create github \
  --name="deploy-production" \
  --repo-name="shopping-optimizer" \
  --repo-owner="your-github-org" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --substitutions="_ENVIRONMENT=production"

# Create trigger for staging (staging branch)
gcloud builds triggers create github \
  --name="deploy-staging" \
  --repo-name="shopping-optimizer" \
  --repo-owner="your-github-org" \
  --branch-pattern="^staging$" \
  --build-config="cloudbuild.yaml" \
  --substitutions="_ENVIRONMENT=staging,_MIN_INSTANCES=0,_MAX_INSTANCES=3"
```

## Additional Resources

- [Full Deployment Guide](docs/CLOUD_RUN_DEPLOYMENT.md) - Comprehensive documentation
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Memorystore for Redis](https://cloud.google.com/memorystore/docs/redis)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)

## Support

For issues:
1. Check logs: `gcloud logging tail "resource.type=cloud_run_revision"`
2. Check health: `curl $SERVICE_URL/health/detailed`
3. Check metrics: `curl $SERVICE_URL/metrics/summary`
4. Review [Troubleshooting Guide](docs/CLOUD_RUN_DEPLOYMENT.md#troubleshooting)

---

**Last Updated**: November 2025

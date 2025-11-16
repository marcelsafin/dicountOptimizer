# Google Cloud Run Deployment Guide

This guide provides comprehensive instructions for deploying the Shopping Optimizer to Google Cloud Run with production-grade configuration.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Redis (Memorystore) Configuration](#redis-memorystore-configuration)
4. [Secret Management](#secret-management)
5. [VPC Configuration](#vpc-configuration)
6. [Cloud Build Setup](#cloud-build-setup)
7. [Deployment](#deployment)
8. [Custom Domain and SSL](#custom-domain-and-ssl)
9. [Monitoring and Observability](#monitoring-and-observability)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before deploying, ensure you have:

- **Google Cloud Project**: Active GCP project with billing enabled
- **gcloud CLI**: Installed and authenticated (`gcloud auth login`)
- **Required APIs**: Enabled in your project
- **API Keys**: Google API key and Salling Group API key
- **Permissions**: Owner or Editor role on the project

### Enable Required APIs

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  secretmanager.googleapis.com \
  redis.googleapis.com \
  vpcaccess.googleapis.com \
  compute.googleapis.com
```

---

## Initial Setup

### 1. Clone and Prepare Repository

```bash
# Clone the repository
git clone https://github.com/your-org/shopping-optimizer.git
cd shopping-optimizer

# Verify Dockerfile exists
ls -la Dockerfile

# Test local build (optional)
docker build -t shopping-optimizer:test .
```

### 2. Set Environment Variables

```bash
# Project configuration
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export SERVICE_NAME="shopping-optimizer"

# Set gcloud defaults
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION
```

---

## Redis (Memorystore) Configuration

Cloud Run requires Redis (Memorystore) for distributed caching across multiple instances.

### 1. Create VPC Network (if not exists)

```bash
# Create VPC network
gcloud compute networks create shopping-optimizer-network \
  --subnet-mode=auto \
  --bgp-routing-mode=regional

# Create firewall rule for internal traffic
gcloud compute firewall-rules create allow-internal \
  --network=shopping-optimizer-network \
  --allow=tcp,udp,icmp \
  --source-ranges=10.0.0.0/8
```

### 2. Create Redis Instance

```bash
# Create Redis instance (Standard tier for production)
gcloud redis instances create shopping-optimizer-redis \
  --size=1 \
  --region=$REGION \
  --network=shopping-optimizer-network \
  --redis-version=redis_7_0 \
  --tier=STANDARD_HA \
  --replica-count=1 \
  --enable-auth

# Get Redis connection details
gcloud redis instances describe shopping-optimizer-redis \
  --region=$REGION \
  --format="value(host,port,authString)"

# Save the output - you'll need it for the REDIS_URL secret
# Format: redis://:AUTH_STRING@HOST:PORT/0
```

**Cost Optimization for Development:**

For development/staging, use Basic tier:

```bash
gcloud redis instances create shopping-optimizer-redis-dev \
  --size=1 \
  --region=$REGION \
  --network=shopping-optimizer-network \
  --redis-version=redis_7_0 \
  --tier=BASIC
```

### 3. Create VPC Connector

Cloud Run needs a VPC connector to access Redis:

```bash
# Create VPC connector
gcloud compute networks vpc-access connectors create shopping-optimizer-vpc \
  --region=$REGION \
  --network=shopping-optimizer-network \
  --range=10.8.0.0/28 \
  --min-instances=2 \
  --max-instances=10

# Verify connector is ready
gcloud compute networks vpc-access connectors describe shopping-optimizer-vpc \
  --region=$REGION
```

---

## Secret Management

Store sensitive data in Google Secret Manager for secure access.

### 1. Create Secrets

```bash
# Create Google API Key secret
echo -n "your-google-api-key" | \
  gcloud secrets create google-api-key \
  --data-file=- \
  --replication-policy="automatic"

# Create Salling API Key secret
echo -n "your-salling-api-key" | \
  gcloud secrets create salling-api-key \
  --data-file=- \
  --replication-policy="automatic"

# Create Redis URL secret
# Format: redis://:AUTH_STRING@HOST:PORT/0
echo -n "redis://:your-redis-auth@10.x.x.x:6379/0" | \
  gcloud secrets create redis-url \
  --data-file=- \
  --replication-policy="automatic"
```

### 2. Create Service Account

```bash
# Create service account for Cloud Run
gcloud iam service-accounts create shopping-optimizer \
  --display-name="Shopping Optimizer Service Account" \
  --description="Service account for Shopping Optimizer Cloud Run service"

# Grant Secret Manager access
gcloud secrets add-iam-policy-binding google-api-key \
  --member="serviceAccount:shopping-optimizer@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding salling-api-key \
  --member="serviceAccount:shopping-optimizer@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding redis-url \
  --member="serviceAccount:shopping-optimizer@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 3. Verify Secrets

```bash
# List all secrets
gcloud secrets list

# View secret metadata (not the actual value)
gcloud secrets describe google-api-key
```

---

## VPC Configuration

Ensure Cloud Run can access Redis through VPC.

### Verify VPC Connector

```bash
# Check connector status
gcloud compute networks vpc-access connectors describe shopping-optimizer-vpc \
  --region=$REGION

# Should show STATE: READY
```

---

## Cloud Build Setup

### 1. Grant Cloud Build Permissions

```bash
# Get Cloud Build service account
export CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# Get project number
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Grant Cloud Run Admin role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUD_BUILD_SA}" \
  --role="roles/run.admin"

# Grant Service Account User role (to deploy as service account)
gcloud iam service-accounts add-iam-policy-binding \
  shopping-optimizer@${PROJECT_ID}.iam.gserviceaccount.com \
  --member="serviceAccount:${CLOUD_BUILD_SA}" \
  --role="roles/iam.serviceAccountUser"

# Grant Container Registry access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUD_BUILD_SA}" \
  --role="roles/storage.admin"
```

### 2. Configure Build Triggers (Optional)

Set up automatic deployments on git push:

```bash
# Create trigger for production (main branch)
gcloud builds triggers create github \
  --name="deploy-production" \
  --repo-name="shopping-optimizer" \
  --repo-owner="your-github-org" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --substitutions="_ENVIRONMENT=production,_MIN_INSTANCES=1,_MAX_INSTANCES=10"

# Create trigger for staging (staging branch)
gcloud builds triggers create github \
  --name="deploy-staging" \
  --repo-name="shopping-optimizer" \
  --repo-owner="your-github-org" \
  --branch-pattern="^staging$" \
  --build-config="cloudbuild.yaml" \
  --substitutions="_ENVIRONMENT=staging,_MIN_INSTANCES=0,_MAX_INSTANCES=3,_MEMORY=1Gi"
```

---

## Deployment

### Option 1: Manual Deployment with Cloud Build

```bash
# Deploy to production
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions=_ENVIRONMENT=production,_REGION=$REGION

# Deploy to staging
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions=_ENVIRONMENT=staging,_REGION=$REGION,_MIN_INSTANCES=0,_MAX_INSTANCES=3
```

### Option 2: Direct Deployment (without Cloud Build)

```bash
# Build and push image
docker build -t gcr.io/$PROJECT_ID/shopping-optimizer:latest .
docker push gcr.io/$PROJECT_ID/shopping-optimizer:latest

# Deploy to Cloud Run
gcloud run deploy shopping-optimizer \
  --image=gcr.io/$PROJECT_ID/shopping-optimizer:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300s \
  --max-instances=10 \
  --min-instances=1 \
  --concurrency=80 \
  --vpc-connector=shopping-optimizer-vpc \
  --vpc-egress=private-ranges-only \
  --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO,CACHE_TYPE=redis" \
  --set-secrets="GOOGLE_API_KEY=google-api-key:latest,SALLING_GROUP_API_KEY=salling-api-key:latest,REDIS_URL=redis-url:latest" \
  --service-account=shopping-optimizer@${PROJECT_ID}.iam.gserviceaccount.com
```

### 3. Verify Deployment

```bash
# Get service URL
export SERVICE_URL=$(gcloud run services describe shopping-optimizer \
  --region=$REGION \
  --format="value(status.url)")

echo "Service URL: $SERVICE_URL"

# Test health endpoint
curl $SERVICE_URL/health

# Test detailed health endpoint
curl $SERVICE_URL/health/detailed

# Test metrics endpoint
curl $SERVICE_URL/metrics/summary
```

---

## Custom Domain and SSL

### 1. Map Custom Domain

```bash
# Map domain to Cloud Run service
gcloud run domain-mappings create \
  --service=shopping-optimizer \
  --domain=shopping.yourdomain.com \
  --region=$REGION

# Get DNS records to configure
gcloud run domain-mappings describe \
  --domain=shopping.yourdomain.com \
  --region=$REGION
```

### 2. Configure DNS

Add the DNS records shown in the previous command to your domain registrar:

- **Type**: A or CNAME
- **Name**: shopping (or your subdomain)
- **Value**: ghs.googlehosted.com (or the value shown)

### 3. Verify SSL Certificate

SSL certificates are automatically provisioned by Google. Verify:

```bash
# Check domain mapping status
gcloud run domain-mappings describe \
  --domain=shopping.yourdomain.com \
  --region=$REGION

# Should show certificateStatus: ACTIVE
```

**Note**: SSL provisioning can take 15-60 minutes.

---

## Auto-Scaling Configuration

Cloud Run auto-scales based on traffic. Configure scaling parameters:

### Production Configuration

```yaml
# In cloudbuild.yaml substitutions:
_MIN_INSTANCES: '1'      # Always keep 1 instance warm
_MAX_INSTANCES: '10'     # Scale up to 10 instances
_CONCURRENCY: '80'       # 80 concurrent requests per instance
_MEMORY: '2Gi'           # 2GB RAM per instance
_CPU: '2'                # 2 vCPUs per instance
_TIMEOUT: '300s'         # 5 minute timeout for long operations
```

### Staging/Development Configuration

```yaml
_MIN_INSTANCES: '0'      # Scale to zero when idle
_MAX_INSTANCES: '3'      # Limit to 3 instances
_CONCURRENCY: '80'
_MEMORY: '1Gi'           # 1GB RAM (cost optimization)
_CPU: '1'                # 1 vCPU
_TIMEOUT: '300s'
```

### Update Scaling Settings

```bash
# Update min/max instances
gcloud run services update shopping-optimizer \
  --region=$REGION \
  --min-instances=1 \
  --max-instances=10

# Update concurrency
gcloud run services update shopping-optimizer \
  --region=$REGION \
  --concurrency=80

# Update resources
gcloud run services update shopping-optimizer \
  --region=$REGION \
  --memory=2Gi \
  --cpu=2
```

---

## Monitoring and Observability

### 1. Cloud Monitoring Dashboard

Create a monitoring dashboard:

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=shopping-optimizer" \
  --limit=50 \
  --format=json

# View metrics
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_count" AND resource.label.service_name="shopping-optimizer"' \
  --interval-start-time="2024-01-01T00:00:00Z"
```

### 2. Application Metrics

The application exposes custom metrics at:

- `/metrics` - JSON format
- `/metrics/summary` - Summary statistics
- `/metrics/prometheus` - Prometheus format

### 3. Set Up Alerts

```bash
# Create alert for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Shopping Optimizer - High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s \
  --condition-filter='resource.type="cloud_run_revision" AND resource.label.service_name="shopping-optimizer" AND metric.type="run.googleapis.com/request_count" AND metric.label.response_code_class="5xx"'

# Create alert for high latency
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Shopping Optimizer - High Latency" \
  --condition-display-name="P95 latency > 5s" \
  --condition-threshold-value=5000 \
  --condition-threshold-duration=300s \
  --condition-filter='resource.type="cloud_run_revision" AND resource.label.service_name="shopping-optimizer" AND metric.type="run.googleapis.com/request_latencies"'
```

### 4. Log-Based Metrics

Create custom metrics from logs:

```bash
# Create metric for agent execution time
gcloud logging metrics create agent_execution_time \
  --description="Agent execution time in milliseconds" \
  --value-extractor='EXTRACT(jsonPayload.duration_ms)' \
  --log-filter='resource.type="cloud_run_revision" AND jsonPayload.event="agent_execution"'
```

---

## Troubleshooting

### Common Issues

#### 1. Service Won't Start

```bash
# Check logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=shopping-optimizer" \
  --limit=50 \
  --format=json

# Check service status
gcloud run services describe shopping-optimizer --region=$REGION

# Common causes:
# - Missing secrets
# - Invalid environment variables
# - VPC connector not ready
# - Redis connection failed
```

#### 2. Can't Connect to Redis

```bash
# Verify VPC connector
gcloud compute networks vpc-access connectors describe shopping-optimizer-vpc \
  --region=$REGION

# Verify Redis instance
gcloud redis instances describe shopping-optimizer-redis --region=$REGION

# Test Redis connection from Cloud Shell
gcloud compute ssh test-vm --zone=us-central1-a --command="redis-cli -h REDIS_HOST -p 6379 -a AUTH_STRING ping"
```

#### 3. High Latency

```bash
# Check instance count
gcloud run services describe shopping-optimizer \
  --region=$REGION \
  --format="value(status.traffic[0].latestRevision)"

# Increase min instances to reduce cold starts
gcloud run services update shopping-optimizer \
  --region=$REGION \
  --min-instances=2

# Increase resources
gcloud run services update shopping-optimizer \
  --region=$REGION \
  --memory=4Gi \
  --cpu=4
```

#### 4. Secrets Not Accessible

```bash
# Verify service account has access
gcloud secrets get-iam-policy google-api-key

# Grant access if missing
gcloud secrets add-iam-policy-binding google-api-key \
  --member="serviceAccount:shopping-optimizer@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Health Check Endpoints

```bash
# Basic health check
curl $SERVICE_URL/health

# Detailed health check (includes dependencies)
curl $SERVICE_URL/health/detailed

# Metrics
curl $SERVICE_URL/metrics/summary
```

### Debugging Commands

```bash
# Stream logs in real-time
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=shopping-optimizer"

# Get recent errors
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=shopping-optimizer AND severity>=ERROR" \
  --limit=20 \
  --format=json

# Check revision status
gcloud run revisions list \
  --service=shopping-optimizer \
  --region=$REGION

# Describe specific revision
gcloud run revisions describe REVISION_NAME \
  --region=$REGION
```

---

## Cost Optimization

### Estimated Monthly Costs

**Production (24/7 operation):**
- Cloud Run: ~$50-150/month (depends on traffic)
- Redis (Standard HA): ~$150/month
- VPC Connector: ~$10/month
- **Total: ~$210-310/month**

**Staging/Development:**
- Cloud Run: ~$10-30/month (scale to zero)
- Redis (Basic): ~$50/month
- VPC Connector: ~$10/month
- **Total: ~$70-90/month**

### Cost Reduction Tips

1. **Use scale-to-zero for non-production**: Set `_MIN_INSTANCES=0`
2. **Use Basic Redis tier for dev/staging**: Saves ~$100/month
3. **Reduce memory allocation**: Use 1Gi instead of 2Gi if possible
4. **Set appropriate timeouts**: Avoid long-running idle connections
5. **Use request-based pricing**: Only pay for actual usage

---

## Production Checklist

Before going live, verify:

- [ ] All secrets are configured in Secret Manager
- [ ] Redis instance is running and accessible
- [ ] VPC connector is in READY state
- [ ] Service account has all required permissions
- [ ] Health checks return 200 OK
- [ ] Custom domain is mapped (if applicable)
- [ ] SSL certificate is active
- [ ] Monitoring alerts are configured
- [ ] Auto-scaling parameters are set
- [ ] Logs are being collected
- [ ] Backup and disaster recovery plan is in place

---

## Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Memorystore for Redis](https://cloud.google.com/memorystore/docs/redis)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)
- [VPC Access](https://cloud.google.com/vpc/docs/configure-serverless-vpc-access)
- [Cloud Build](https://cloud.google.com/build/docs)

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review Cloud Run logs
3. Check application metrics at `/metrics/summary`
4. Contact the development team

---

**Last Updated**: November 2025
**Version**: 1.0.0

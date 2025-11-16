#!/bin/bash
# Production deployment script for Shopping Optimizer
# This script deploys the application to Google Cloud Run with production configuration
#
# Usage:
#   ./scripts/deploy-production.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Project ID set in gcloud config
#   - All secrets configured in Secret Manager
#   - Redis instance running
#   - VPC connector created
#
# Requirements: 9.5

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=$(gcloud config get-value project)
REGION="${REGION:-us-central1}"
SERVICE_NAME="shopping-optimizer"
ENVIRONMENT="production"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Shopping Optimizer - Production Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo "Environment: $ENVIRONMENT"
echo ""

# Verify prerequisites
echo -e "${YELLOW}Verifying prerequisites...${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    exit 1
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${RED}Error: Not authenticated with gcloud${NC}"
    echo "Run: gcloud auth login"
    exit 1
fi

# Check if project is set
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No project ID set${NC}"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites verified${NC}"
echo ""

# Verify secrets exist
echo -e "${YELLOW}Verifying secrets...${NC}"

REQUIRED_SECRETS=("google-api-key" "salling-api-key" "redis-url")
for secret in "${REQUIRED_SECRETS[@]}"; do
    if ! gcloud secrets describe "$secret" &> /dev/null; then
        echo -e "${RED}Error: Secret '$secret' not found${NC}"
        echo "Create it with: gcloud secrets create $secret --data-file=-"
        exit 1
    fi
    echo -e "${GREEN}✓ Secret '$secret' exists${NC}"
done

echo ""

# Verify VPC connector
echo -e "${YELLOW}Verifying VPC connector...${NC}"

if ! gcloud compute networks vpc-access connectors describe shopping-optimizer-vpc \
    --region="$REGION" &> /dev/null; then
    echo -e "${RED}Error: VPC connector 'shopping-optimizer-vpc' not found${NC}"
    echo "Create it following the deployment guide"
    exit 1
fi

echo -e "${GREEN}✓ VPC connector exists${NC}"
echo ""

# Verify Redis instance
echo -e "${YELLOW}Verifying Redis instance...${NC}"

if ! gcloud redis instances describe shopping-optimizer-redis \
    --region="$REGION" &> /dev/null; then
    echo -e "${RED}Error: Redis instance 'shopping-optimizer-redis' not found${NC}"
    echo "Create it following the deployment guide"
    exit 1
fi

echo -e "${GREEN}✓ Redis instance exists${NC}"
echo ""

# Confirm deployment
echo -e "${YELLOW}Ready to deploy to production${NC}"
read -p "Continue? (yes/no): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# Deploy using Cloud Build
echo -e "${YELLOW}Starting deployment with Cloud Build...${NC}"
echo ""

gcloud builds submit \
    --config cloudbuild.yaml \
    --substitutions="\
_ENVIRONMENT=production,\
_REGION=$REGION,\
_MEMORY=2Gi,\
_CPU=2,\
_TIMEOUT=300s,\
_MAX_INSTANCES=10,\
_MIN_INSTANCES=1,\
_CONCURRENCY=80,\
_LOG_LEVEL=INFO,\
_AGENT_MODEL=gemini-2.0-flash-exp,\
_AGENT_TEMPERATURE=0.7,\
_CACHE_TTL_SECONDS=3600"

# Get service URL
echo ""
echo -e "${YELLOW}Getting service URL...${NC}"

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" \
    --format="value(status.url)")

echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
echo ""
echo "Service URL: $SERVICE_URL"
echo ""

# Test health endpoint
echo -e "${YELLOW}Testing health endpoint...${NC}"

if curl -f -s "$SERVICE_URL/health" > /dev/null; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    echo "Check logs: gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --limit=50"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Service: $SERVICE_NAME"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "URL: $SERVICE_URL"
echo ""
echo "Next steps:"
echo "1. Test the API: curl $SERVICE_URL/health/detailed"
echo "2. View logs: gcloud logging tail \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\""
echo "3. View metrics: curl $SERVICE_URL/metrics/summary"
echo "4. Configure custom domain (optional)"
echo ""
echo -e "${GREEN}Deployment complete!${NC}"

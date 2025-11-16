#!/bin/bash
# GCP Infrastructure Setup Script for Shopping Optimizer
# This script sets up all required GCP infrastructure for Cloud Run deployment
#
# Usage:
#   ./scripts/setup-gcp-infrastructure.sh
#
# This script will:
#   1. Enable required APIs
#   2. Create VPC network
#   3. Create Redis instance
#   4. Create VPC connector
#   5. Create service account
#   6. Set up secrets
#   7. Configure IAM permissions
#
# Requirements: 9.5

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${REGION:-us-central1}"
ENVIRONMENT="${ENVIRONMENT:-production}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Shopping Optimizer - GCP Infrastructure Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo ""

# Verify prerequisites
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No project ID set${NC}"
    echo "Set it with: export PROJECT_ID=your-project-id"
    exit 1
fi

# Confirm setup
echo -e "${YELLOW}This script will set up GCP infrastructure for Shopping Optimizer${NC}"
echo "This includes:"
echo "  - Enabling required APIs"
echo "  - Creating VPC network and firewall rules"
echo "  - Creating Redis instance (Memorystore)"
echo "  - Creating VPC connector"
echo "  - Creating service account"
echo "  - Setting up IAM permissions"
echo ""
read -p "Continue? (yes/no): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Setup cancelled"
    exit 0
fi

# Set project
echo -e "${YELLOW}Setting project...${NC}"
gcloud config set project "$PROJECT_ID"
echo -e "${GREEN}✓ Project set${NC}"
echo ""

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"

APIS=(
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "containerregistry.googleapis.com"
    "secretmanager.googleapis.com"
    "redis.googleapis.com"
    "vpcaccess.googleapis.com"
    "compute.googleapis.com"
)

for api in "${APIS[@]}"; do
    echo "Enabling $api..."
    gcloud services enable "$api" --quiet
done

echo -e "${GREEN}✓ APIs enabled${NC}"
echo ""

# Create VPC network
echo -e "${YELLOW}Creating VPC network...${NC}"

if gcloud compute networks describe shopping-optimizer-network &> /dev/null; then
    echo -e "${BLUE}VPC network already exists${NC}"
else
    gcloud compute networks create shopping-optimizer-network \
        --subnet-mode=auto \
        --bgp-routing-mode=regional
    
    echo -e "${GREEN}✓ VPC network created${NC}"
fi

# Create firewall rule
if gcloud compute firewall-rules describe allow-internal-shopping-optimizer &> /dev/null; then
    echo -e "${BLUE}Firewall rule already exists${NC}"
else
    gcloud compute firewall-rules create allow-internal-shopping-optimizer \
        --network=shopping-optimizer-network \
        --allow=tcp,udp,icmp \
        --source-ranges=10.0.0.0/8
    
    echo -e "${GREEN}✓ Firewall rule created${NC}"
fi

echo ""

# Create Redis instance
echo -e "${YELLOW}Creating Redis instance...${NC}"

REDIS_INSTANCE_NAME="shopping-optimizer-redis"
if [ "$ENVIRONMENT" != "production" ]; then
    REDIS_INSTANCE_NAME="shopping-optimizer-redis-${ENVIRONMENT}"
fi

if gcloud redis instances describe "$REDIS_INSTANCE_NAME" --region="$REGION" &> /dev/null; then
    echo -e "${BLUE}Redis instance already exists${NC}"
else
    if [ "$ENVIRONMENT" = "production" ]; then
        # Production: Standard HA tier
        echo "Creating production Redis instance (Standard HA)..."
        gcloud redis instances create "$REDIS_INSTANCE_NAME" \
            --size=1 \
            --region="$REGION" \
            --network=shopping-optimizer-network \
            --redis-version=redis_7_0 \
            --tier=STANDARD_HA \
            --replica-count=1 \
            --enable-auth
    else
        # Staging/Dev: Basic tier
        echo "Creating ${ENVIRONMENT} Redis instance (Basic)..."
        gcloud redis instances create "$REDIS_INSTANCE_NAME" \
            --size=1 \
            --region="$REGION" \
            --network=shopping-optimizer-network \
            --redis-version=redis_7_0 \
            --tier=BASIC
    fi
    
    echo -e "${GREEN}✓ Redis instance created${NC}"
fi

# Get Redis connection details
echo ""
echo -e "${YELLOW}Getting Redis connection details...${NC}"

REDIS_HOST=$(gcloud redis instances describe "$REDIS_INSTANCE_NAME" \
    --region="$REGION" \
    --format="value(host)")

REDIS_PORT=$(gcloud redis instances describe "$REDIS_INSTANCE_NAME" \
    --region="$REGION" \
    --format="value(port)")

REDIS_AUTH=$(gcloud redis instances describe "$REDIS_INSTANCE_NAME" \
    --region="$REGION" \
    --format="value(authString)" 2>/dev/null || echo "")

if [ -n "$REDIS_AUTH" ]; then
    REDIS_URL="redis://:${REDIS_AUTH}@${REDIS_HOST}:${REDIS_PORT}/0"
else
    REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}/0"
fi

echo "Redis Host: $REDIS_HOST"
echo "Redis Port: $REDIS_PORT"
echo "Redis URL: $REDIS_URL"
echo ""
echo -e "${GREEN}✓ Redis connection details retrieved${NC}"
echo ""

# Create VPC connector
echo -e "${YELLOW}Creating VPC connector...${NC}"

VPC_CONNECTOR_NAME="shopping-optimizer-vpc"
if [ "$ENVIRONMENT" != "production" ]; then
    VPC_CONNECTOR_NAME="shopping-optimizer-vpc-${ENVIRONMENT}"
fi

if gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR_NAME" \
    --region="$REGION" &> /dev/null; then
    echo -e "${BLUE}VPC connector already exists${NC}"
else
    # Use different IP ranges for different environments
    if [ "$ENVIRONMENT" = "production" ]; then
        IP_RANGE="10.8.0.0/28"
    elif [ "$ENVIRONMENT" = "staging" ]; then
        IP_RANGE="10.8.1.0/28"
    else
        IP_RANGE="10.8.2.0/28"
    fi
    
    gcloud compute networks vpc-access connectors create "$VPC_CONNECTOR_NAME" \
        --region="$REGION" \
        --network=shopping-optimizer-network \
        --range="$IP_RANGE" \
        --min-instances=2 \
        --max-instances=10
    
    echo -e "${GREEN}✓ VPC connector created${NC}"
fi

echo ""

# Create service account
echo -e "${YELLOW}Creating service account...${NC}"

SERVICE_ACCOUNT_NAME="shopping-optimizer"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" &> /dev/null; then
    echo -e "${BLUE}Service account already exists${NC}"
else
    gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
        --display-name="Shopping Optimizer Service Account" \
        --description="Service account for Shopping Optimizer Cloud Run service"
    
    echo -e "${GREEN}✓ Service account created${NC}"
fi

echo ""

# Set up secrets
echo -e "${YELLOW}Setting up secrets...${NC}"
echo ""
echo "You need to provide the following secrets:"
echo "  1. Google API Key (for Gemini and Google Maps)"
echo "  2. Salling Group API Key (for discount data)"
echo ""

# Google API Key
if gcloud secrets describe google-api-key &> /dev/null; then
    echo -e "${BLUE}Secret 'google-api-key' already exists${NC}"
else
    read -p "Enter Google API Key: " -s GOOGLE_API_KEY
    echo ""
    
    if [ -n "$GOOGLE_API_KEY" ]; then
        echo -n "$GOOGLE_API_KEY" | gcloud secrets create google-api-key \
            --data-file=- \
            --replication-policy="automatic"
        
        echo -e "${GREEN}✓ Secret 'google-api-key' created${NC}"
    else
        echo -e "${YELLOW}⚠ Skipping 'google-api-key' - you'll need to create it manually${NC}"
    fi
fi

# Salling API Key
if gcloud secrets describe salling-api-key &> /dev/null; then
    echo -e "${BLUE}Secret 'salling-api-key' already exists${NC}"
else
    read -p "Enter Salling Group API Key: " -s SALLING_API_KEY
    echo ""
    
    if [ -n "$SALLING_API_KEY" ]; then
        echo -n "$SALLING_API_KEY" | gcloud secrets create salling-api-key \
            --data-file=- \
            --replication-policy="automatic"
        
        echo -e "${GREEN}✓ Secret 'salling-api-key' created${NC}"
    else
        echo -e "${YELLOW}⚠ Skipping 'salling-api-key' - you'll need to create it manually${NC}"
    fi
fi

# Redis URL
if gcloud secrets describe redis-url &> /dev/null; then
    echo -e "${BLUE}Secret 'redis-url' already exists${NC}"
else
    echo -n "$REDIS_URL" | gcloud secrets create redis-url \
        --data-file=- \
        --replication-policy="automatic"
    
    echo -e "${GREEN}✓ Secret 'redis-url' created${NC}"
fi

echo ""

# Configure IAM permissions
echo -e "${YELLOW}Configuring IAM permissions...${NC}"

# Grant Secret Manager access to service account
SECRETS=("google-api-key" "salling-api-key" "redis-url")

for secret in "${SECRETS[@]}"; do
    if gcloud secrets describe "$secret" &> /dev/null; then
        gcloud secrets add-iam-policy-binding "$secret" \
            --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
            --role="roles/secretmanager.secretAccessor" \
            --quiet
        
        echo "✓ Granted access to '$secret'"
    fi
done

# Grant Cloud Build permissions
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

echo ""
echo "Granting Cloud Build permissions..."

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${CLOUD_BUILD_SA}" \
    --role="roles/run.admin" \
    --quiet

gcloud iam service-accounts add-iam-policy-binding \
    "$SERVICE_ACCOUNT_EMAIL" \
    --member="serviceAccount:${CLOUD_BUILD_SA}" \
    --role="roles/iam.serviceAccountUser" \
    --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${CLOUD_BUILD_SA}" \
    --role="roles/storage.admin" \
    --quiet

echo -e "${GREEN}✓ IAM permissions configured${NC}"
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Infrastructure Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Resources created:"
echo "  ✓ VPC network: shopping-optimizer-network"
echo "  ✓ Redis instance: $REDIS_INSTANCE_NAME"
echo "  ✓ VPC connector: $VPC_CONNECTOR_NAME"
echo "  ✓ Service account: $SERVICE_ACCOUNT_EMAIL"
echo "  ✓ Secrets configured"
echo "  ✓ IAM permissions set"
echo ""
echo "Redis connection:"
echo "  Host: $REDIS_HOST"
echo "  Port: $REDIS_PORT"
echo "  URL: $REDIS_URL"
echo ""
echo "Next steps:"
echo "  1. Verify all secrets are set:"
echo "     gcloud secrets list"
echo ""
echo "  2. Deploy the application:"
echo "     ./scripts/deploy-${ENVIRONMENT}.sh"
echo ""
echo "  3. Test the deployment:"
echo "     curl https://YOUR-SERVICE-URL/health"
echo ""
echo -e "${GREEN}Setup complete!${NC}"

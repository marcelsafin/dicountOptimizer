# CI/CD Pipeline Setup Guide

This document describes the CI/CD pipeline configuration for the Shopping Optimizer application.

## Overview

The CI/CD pipeline is implemented using GitHub Actions and includes:

1. **Linting** - Code quality checks with Ruff
2. **Type Checking** - Static type analysis with mypy
3. **Unit Tests** - Comprehensive test suite with coverage reporting
4. **Integration Tests** - End-to-end testing with Redis
5. **Docker Build** - Container image building and testing
6. **Security Scanning** - Vulnerability scanning with Trivy
7. **Deployment** - Automated deployment to Google Cloud Run

## Pipeline Workflows

### Main CI/CD Pipeline (`ci.yml`)

Triggered on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Manual workflow dispatch

#### Jobs

1. **Lint** - Runs Ruff linter and formatter checks
2. **Type Check** - Validates type safety with mypy on refactored modules
3. **Test** - Runs pytest with coverage on Python 3.11 and 3.12
4. **Integration Test** - Runs integration tests with Redis service
5. **Build Docker** - Builds and tests Docker image, pushes to GHCR
6. **Security Scan** - Scans for vulnerabilities with Trivy
7. **Deploy Production** - Deploys to Cloud Run (main branch only)
8. **Deploy Staging** - Deploys to Cloud Run staging (develop branch only)
9. **Notify** - Sends deployment status notifications

### Type Check Workflow (`type-check.yml`)

Dedicated workflow for type checking that runs on changes to Python files.

## Required GitHub Secrets

Configure these secrets in your GitHub repository settings:

### Required for Testing

| Secret Name | Description | Example |
|------------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key for testing | `AIza...` |
| `SALLING_API_KEY` | Salling Group API key for testing | `Bearer abc...` |

### Required for Google Cloud Deployment

| Secret Name | Description | How to Get |
|------------|-------------|------------|
| `GCP_SA_KEY` | Service account JSON key | See "Creating GCP Service Account" below |
| `GCP_PROJECT_ID` | Google Cloud project ID | From GCP Console |
| `GCP_REGION` | Cloud Run region (optional) | Default: `us-central1` |

## Setting Up Google Cloud Deployment

### 1. Create a Google Cloud Project

```bash
# Create project
gcloud projects create shopping-optimizer-prod --name="Shopping Optimizer"

# Set as default
gcloud config set project shopping-optimizer-prod
```

### 2. Enable Required APIs

```bash
# Enable Cloud Run API
gcloud services enable run.googleapis.com

# Enable Container Registry API
gcloud services enable containerregistry.googleapis.com

# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com
```

### 3. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deployment"

# Get service account email
SA_EMAIL=$(gcloud iam service-accounts list \
  --filter="displayName:GitHub Actions Deployment" \
  --format='value(email)')

# Grant necessary roles
gcloud projects add-iam-policy-binding shopping-optimizer-prod \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding shopping-optimizer-prod \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding shopping-optimizer-prod \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding shopping-optimizer-prod \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

# Create and download key
gcloud iam service-accounts keys create key.json \
  --iam-account="${SA_EMAIL}"

# Display key (copy this to GitHub secrets as GCP_SA_KEY)
cat key.json

# Clean up local key file
rm key.json
```

### 4. Create Secrets in Google Secret Manager

```bash
# Create Google API key secret
echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets create google-api-key \
  --data-file=- \
  --replication-policy="automatic"

# Create Salling API key secret
echo -n "YOUR_SALLING_API_KEY" | gcloud secrets create salling-api-key \
  --data-file=- \
  --replication-policy="automatic"

# Grant Cloud Run service account access to secrets
gcloud secrets add-iam-policy-binding google-api-key \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding salling-api-key \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"
```

### 5. Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add the following secrets:

1. **GCP_SA_KEY**: Paste the entire contents of the service account JSON key
2. **GCP_PROJECT_ID**: Your GCP project ID (e.g., `shopping-optimizer-prod`)
3. **GCP_REGION**: (Optional) Cloud Run region (default: `us-central1`)
4. **GOOGLE_API_KEY**: Your Google Gemini API key (for CI tests)
5. **SALLING_API_KEY**: Your Salling Group API key (for CI tests)

### 6. Configure GitHub Environments

Create two environments in GitHub:

#### Production Environment
- Go to Settings → Environments → New environment
- Name: `production`
- Add protection rules:
  - Required reviewers (recommended)
  - Wait timer (optional)
  - Deployment branches: `main` only

#### Staging Environment
- Name: `staging`
- Deployment branches: `develop` only

## Docker Image Registry

The pipeline pushes Docker images to two registries:

### GitHub Container Registry (GHCR)
- Automatic for all builds
- Images: `ghcr.io/<username>/shopping-optimizer`
- Tags: branch name, PR number, SHA, latest

### Google Container Registry (GCR)
- Only for deployments
- Images: `gcr.io/<project-id>/shopping-optimizer`
- Tags: SHA (production), staging-SHA (staging), latest (production)

## Deployment Configuration

### Production (main branch)
- **Service Name**: `shopping-optimizer`
- **Memory**: 1Gi
- **CPU**: 2
- **Min Instances**: 1
- **Max Instances**: 10
- **Concurrency**: 80
- **Timeout**: 300s

### Staging (develop branch)
- **Service Name**: `shopping-optimizer-staging`
- **Memory**: 512Mi
- **CPU**: 1
- **Min Instances**: 0 (scales to zero)
- **Max Instances**: 5
- **Concurrency**: 80
- **Timeout**: 300s

## Running Locally

### Run Linting
```bash
pip install ruff
ruff check .
ruff format --check .
```

### Run Type Checking
```bash
pip install mypy
pip install -r requirements.txt
mypy agents/discount_optimizer/domain/
mypy agents/discount_optimizer/infrastructure/
# ... other modules
```

### Run Tests
```bash
pip install pytest pytest-cov pytest-asyncio
pytest tests/ --cov=agents --cov-report=term-missing
```

### Build Docker Image
```bash
docker build -t shopping-optimizer .
docker run -p 3000:3000 --env-file .env shopping-optimizer
```

## Monitoring Deployments

### View Cloud Run Logs
```bash
gcloud run services logs read shopping-optimizer \
  --project=shopping-optimizer-prod \
  --region=us-central1 \
  --limit=50
```

### Check Service Status
```bash
gcloud run services describe shopping-optimizer \
  --project=shopping-optimizer-prod \
  --region=us-central1
```

### View Metrics
```bash
# Open Cloud Run console
gcloud run services browse shopping-optimizer \
  --project=shopping-optimizer-prod \
  --region=us-central1
```

## Troubleshooting

### Pipeline Fails on Type Checking
- Run `mypy` locally on the failing module
- Check `mypy.ini` configuration
- Ensure all dependencies are installed

### Pipeline Fails on Tests
- Check test logs in GitHub Actions
- Run tests locally with `pytest -v`
- Verify environment variables are set

### Docker Build Fails
- Check Dockerfile syntax
- Verify all files are included (not in .dockerignore)
- Test build locally

### Deployment Fails
- Verify GCP service account has correct permissions
- Check Secret Manager secrets exist
- Verify Cloud Run API is enabled
- Check deployment logs in GCP Console

### Health Check Fails
- Verify `/health` endpoint exists in app.py
- Check container logs in Cloud Run
- Verify environment variables are set correctly

## Security Best Practices

1. **Never commit secrets** - Use GitHub Secrets and GCP Secret Manager
2. **Rotate keys regularly** - Update API keys and service account keys
3. **Use least privilege** - Grant minimal required permissions
4. **Enable vulnerability scanning** - Trivy scans are automatic
5. **Review dependencies** - Keep requirements.txt updated
6. **Use environment protection** - Require reviews for production

## Cost Optimization

### Cloud Run Costs
- Staging scales to zero when not in use
- Production has min 1 instance for availability
- Adjust `--max-instances` based on traffic
- Monitor usage in GCP Console

### Container Registry Costs
- Old images are retained indefinitely
- Consider setting up lifecycle policies to delete old images
- Use `gcloud container images list-tags` to view images

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [mypy Documentation](https://mypy.readthedocs.io/)

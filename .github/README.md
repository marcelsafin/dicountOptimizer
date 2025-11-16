# CI/CD Documentation

This directory contains all CI/CD pipeline configuration and documentation for the Shopping Optimizer project.

## 📁 Directory Structure

```
.github/
├── workflows/              # GitHub Actions workflows
│   ├── ci.yml             # Main CI/CD pipeline
│   ├── type-check.yml     # Type checking workflow
│   ├── deploy-manual.yml  # Manual deployment workflow
│   └── cleanup.yml        # Image cleanup workflow
├── CICD_SETUP.md          # Complete setup guide
├── DEVELOPER_GUIDE.md     # Developer quick reference
├── SECRETS_CHECKLIST.md   # Secrets configuration guide
└── README.md              # This file
```

## 📚 Documentation Guide

### For First-Time Setup
Start here if you're setting up CI/CD for the first time:

1. **[SECRETS_CHECKLIST.md](SECRETS_CHECKLIST.md)** - Configure all required secrets
2. **[CICD_SETUP.md](CICD_SETUP.md)** - Complete setup guide with GCP configuration
3. Test your setup by creating a PR

### For Daily Development
Use this for day-to-day development:

- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Quick reference for common tasks
  - Pre-commit checklist
  - Running tests locally
  - Troubleshooting CI failures
  - Branch strategy
  - PR process

### For Deployment
When you need to deploy:

- **Manual Deployment**: Use the `deploy-manual.yml` workflow in GitHub Actions UI
- **Automatic Deployment**: 
  - Push to `develop` → deploys to staging
  - Push to `main` → deploys to production

## 🚀 Quick Start

### Run Checks Locally
```bash
# Format and lint
ruff format .
ruff check . --fix

# Type check
mypy agents/discount_optimizer/domain/
mypy agents/discount_optimizer/infrastructure/
# ... other modules

# Run tests
pytest tests/ --cov=agents
```

### Create a Pull Request
```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/my-feature
```

### Deploy Manually
1. Go to **Actions** tab in GitHub
2. Select **Manual Deployment** workflow
3. Click **Run workflow**
4. Choose environment (staging/production)
5. Click **Run workflow** button

## 🔧 Workflows Overview

### ci.yml - Main CI/CD Pipeline
**Triggers**: Push to main/develop, Pull requests

**Jobs**:
1. **Lint** - Code quality with Ruff
2. **Type Check** - Static type analysis with mypy
3. **Test** - Unit tests with coverage (Python 3.11 & 3.12)
4. **Integration Test** - End-to-end tests with Redis
5. **Build Docker** - Container image build and test
6. **Security Scan** - Vulnerability scanning with Trivy
7. **Deploy Production** - Deploy to Cloud Run (main branch)
8. **Deploy Staging** - Deploy to Cloud Run (develop branch)

### type-check.yml - Type Checking
**Triggers**: Changes to Python files

**Purpose**: Validates type safety of refactored modules

### deploy-manual.yml - Manual Deployment
**Triggers**: Manual workflow dispatch

**Purpose**: Deploy specific version to staging or production

### cleanup.yml - Image Cleanup
**Triggers**: Weekly schedule, Manual dispatch

**Purpose**: Delete old Docker images to save storage costs

## 🔐 Required Secrets

### For CI/CD
- `GOOGLE_API_KEY` - Google Gemini API key
- `SALLING_API_KEY` - Salling Group API key

### For Deployment
- `GCP_SA_KEY` - GCP service account JSON key
- `GCP_PROJECT_ID` - GCP project ID
- `GCP_REGION` - Cloud Run region (optional)

See [SECRETS_CHECKLIST.md](SECRETS_CHECKLIST.md) for detailed setup.

## 🌍 Environments

### Production
- **Branch**: `main`
- **Service**: `shopping-optimizer`
- **URL**: Set after first deployment
- **Resources**: 1Gi memory, 2 CPU, 1-10 instances

### Staging
- **Branch**: `develop`
- **Service**: `shopping-optimizer-staging`
- **URL**: Set after first deployment
- **Resources**: 512Mi memory, 1 CPU, 0-5 instances

## 📊 Monitoring

### View CI/CD Status
- GitHub Actions tab shows all workflow runs
- Green ✅ = passed
- Red ❌ = failed
- Yellow 🟡 = in progress

### View Deployment Logs
```bash
# Staging
gcloud run services logs read shopping-optimizer-staging \
  --region us-central1

# Production
gcloud run services logs read shopping-optimizer \
  --region us-central1
```

### View Service Status
```bash
# Staging
gcloud run services describe shopping-optimizer-staging \
  --region us-central1

# Production
gcloud run services describe shopping-optimizer \
  --region us-central1
```

## 🐛 Troubleshooting

### CI Checks Failing
1. Check the specific job that failed in GitHub Actions
2. Review the error logs
3. Run the same check locally (see DEVELOPER_GUIDE.md)
4. Fix the issue and push again

### Deployment Failing
1. Check Cloud Run logs in GCP Console
2. Verify all secrets are configured correctly
3. Ensure service account has required permissions
4. Check that APIs are enabled in GCP

### Common Issues
- **Type check fails**: Run `mypy` locally on the failing module
- **Tests fail**: Run `pytest` locally with `-v` flag
- **Docker build fails**: Test `docker build` locally
- **Deployment fails**: Check GCP service account permissions

See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for detailed troubleshooting.

## 📖 Additional Resources

### Project Documentation
- [Architecture](../docs/ARCHITECTURE.md)
- [API Reference](../docs/API_REFERENCE.md)
- [Type Checking Strategy](../docs/TYPE_CHECKING_STRATEGY.md)
- [Quick Start](../docs/QUICK_START.md)

### External Documentation
- [GitHub Actions](https://docs.github.com/en/actions)
- [Google Cloud Run](https://cloud.google.com/run/docs)
- [Ruff](https://docs.astral.sh/ruff/)
- [mypy](https://mypy.readthedocs.io/)
- [pytest](https://docs.pytest.org/)

## 🤝 Contributing

1. Read [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
2. Create a feature branch from `develop`
3. Make your changes
4. Run all checks locally
5. Create a PR to `develop`
6. Wait for CI checks to pass
7. Get approval from reviewers
8. Merge!

## 📝 Notes

- All workflows use Python 3.11 as the primary version
- Docker images are pushed to both GHCR and GCR
- Staging scales to zero when not in use
- Production maintains minimum 1 instance
- Old images are cleaned up weekly
- Security scans run on all deployments

## 🆘 Getting Help

If you need help:
1. Check the documentation in this directory
2. Review GitHub Actions logs
3. Check Cloud Run logs in GCP Console
4. Ask the team in your communication channel

---

**Last Updated**: November 2025
**Maintained By**: Development Team

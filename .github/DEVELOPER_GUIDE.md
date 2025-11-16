# Developer Guide - CI/CD Pipeline

Quick reference for developers working with the CI/CD pipeline.

## Pre-commit Checklist

Before pushing code, run these checks locally:

```bash
# 1. Format code
ruff format .

# 2. Lint code
ruff check . --fix

# 3. Type check refactored modules
mypy agents/discount_optimizer/domain/
mypy agents/discount_optimizer/infrastructure/
mypy agents/discount_optimizer/agents/
mypy agents/discount_optimizer/services/
mypy agents/discount_optimizer/config.py
mypy agents/discount_optimizer/logging.py
mypy agents/discount_optimizer/factory.py

# 4. Run tests
pytest tests/ -v

# 5. Check test coverage
pytest tests/ --cov=agents --cov-report=term-missing
```

## Quick Commands

### Install Development Dependencies
```bash
pip install -r requirements.txt
```

### Run Linting
```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check . --fix

# Check formatting
ruff format --check .

# Apply formatting
ruff format .
```

### Run Type Checking
```bash
# Check all refactored modules
./scripts/type_check.sh

# Check specific module
mypy agents/discount_optimizer/domain/
```

### Run Tests
```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_meal_suggester_agent.py

# With coverage
pytest tests/ --cov=agents --cov-report=html

# Parallel execution
pytest tests/ -n auto

# Verbose output
pytest tests/ -v -s
```

### Build Docker Image
```bash
# Build
docker build -t shopping-optimizer .

# Run locally
docker run -p 3000:3000 --env-file .env shopping-optimizer

# Test health endpoint
curl http://localhost:3000/health
```

## Branch Strategy

### Main Branch (`main`)
- Production-ready code only
- Triggers deployment to production Cloud Run
- Requires PR review and all checks passing
- Protected branch

### Develop Branch (`develop`)
- Integration branch for features
- Triggers deployment to staging Cloud Run
- All feature branches merge here first
- Protected branch

### Feature Branches
- Branch from `develop`
- Name format: `feature/description` or `fix/description`
- Create PR to `develop` when ready
- All CI checks must pass

## Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/my-feature
   ```

2. **Make Changes**
   - Write code
   - Add tests
   - Update documentation

3. **Run Local Checks**
   ```bash
   ruff format .
   ruff check . --fix
   mypy agents/discount_optimizer/domain/  # and other modules
   pytest tests/
   ```

4. **Commit and Push**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin feature/my-feature
   ```

5. **Create Pull Request**
   - Go to GitHub
   - Create PR from `feature/my-feature` to `develop`
   - Fill in PR template
   - Wait for CI checks to pass
   - Request review

6. **Address Review Comments**
   - Make changes
   - Push updates
   - CI will re-run automatically

7. **Merge**
   - Once approved and CI passes
   - Squash and merge to `develop`
   - Delete feature branch

## CI/CD Pipeline Stages

### On Pull Request
1. ✅ Lint check
2. ✅ Type check
3. ✅ Unit tests (Python 3.11 & 3.12)
4. ✅ Integration tests
5. ✅ Docker build test

### On Push to `develop`
1. All PR checks
2. ✅ Build and push Docker image to GHCR
3. ✅ Build and push Docker image to GCR
4. 🚀 Deploy to staging Cloud Run

### On Push to `main`
1. All PR checks
2. ✅ Build and push Docker image to GHCR
3. ✅ Build and push Docker image to GCR
4. 🔒 Security scan
5. 🚀 Deploy to production Cloud Run

## Troubleshooting CI Failures

### Linting Failures
```bash
# See what would be fixed
ruff check . --diff

# Auto-fix
ruff check . --fix

# Format code
ruff format .
```

### Type Check Failures
```bash
# Run locally to see errors
mypy agents/discount_optimizer/domain/ --show-error-codes

# Common fixes:
# - Add type hints to function parameters
# - Add return type annotations
# - Use proper Pydantic models
# - Import types from typing module
```

### Test Failures
```bash
# Run specific failing test
pytest tests/test_file.py::test_function -v

# Run with print statements
pytest tests/test_file.py -s

# Run with debugger
pytest tests/test_file.py --pdb
```

### Docker Build Failures
```bash
# Build locally to see error
docker build -t shopping-optimizer .

# Check Dockerfile syntax
# Verify all COPY paths exist
# Check requirements.txt is valid
```

### Deployment Failures
- Check GCP service account permissions
- Verify secrets exist in Secret Manager
- Check Cloud Run logs in GCP Console
- Verify environment variables are set

## Environment Variables

### Required for Local Development
```bash
# .env file
GOOGLE_API_KEY=your_key_here
SALLING_API_KEY=your_key_here
ENVIRONMENT=dev
```

### Required for CI/CD (GitHub Secrets)
- `GOOGLE_API_KEY` - For testing
- `SALLING_API_KEY` - For testing
- `GCP_SA_KEY` - Service account JSON
- `GCP_PROJECT_ID` - GCP project ID
- `GCP_REGION` - Cloud Run region (optional)

## Manual Deployment

### Via GitHub Actions UI
1. Go to Actions tab
2. Select "Manual Deployment" workflow
3. Click "Run workflow"
4. Choose environment (staging/production)
5. Optionally specify image tag
6. Click "Run workflow"

### Via gcloud CLI
```bash
# Deploy to staging
gcloud run deploy shopping-optimizer-staging \
  --image gcr.io/PROJECT_ID/shopping-optimizer:TAG \
  --region us-central1

# Deploy to production
gcloud run deploy shopping-optimizer \
  --image gcr.io/PROJECT_ID/shopping-optimizer:TAG \
  --region us-central1
```

## Monitoring

### View CI/CD Status
- GitHub Actions tab shows all workflow runs
- Green checkmark = passed
- Red X = failed
- Yellow circle = in progress

### View Deployment Logs
```bash
# Staging
gcloud run services logs read shopping-optimizer-staging \
  --region us-central1 \
  --limit 100

# Production
gcloud run services logs read shopping-optimizer \
  --region us-central1 \
  --limit 100
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

## Best Practices

### Code Quality
- ✅ Always run linting before committing
- ✅ Maintain 100% type coverage for new code
- ✅ Write tests for new features
- ✅ Keep test coverage above 80%
- ✅ Use Pydantic models for data validation
- ✅ Follow SOLID principles

### Git Workflow
- ✅ Keep commits atomic and focused
- ✅ Write descriptive commit messages
- ✅ Rebase feature branches on develop regularly
- ✅ Squash commits when merging PRs
- ✅ Delete merged branches

### Testing
- ✅ Write unit tests for business logic
- ✅ Write integration tests for workflows
- ✅ Mock external API calls in tests
- ✅ Use fixtures for common test data
- ✅ Test edge cases and error conditions

### Security
- ❌ Never commit secrets or API keys
- ✅ Use environment variables for config
- ✅ Keep dependencies updated
- ✅ Review security scan results
- ✅ Use least privilege for permissions

## Getting Help

- **CI/CD Issues**: Check `.github/CICD_SETUP.md`
- **Type Checking**: Check `docs/TYPE_CHECKING_STRATEGY.md`
- **Architecture**: Check `docs/ARCHITECTURE.md`
- **API Reference**: Check `docs/API_REFERENCE.md`

## Useful Links

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)

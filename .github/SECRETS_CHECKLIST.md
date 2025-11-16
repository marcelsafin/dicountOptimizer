# GitHub Secrets Configuration Checklist

This checklist helps you configure all required secrets for the CI/CD pipeline.

## Required Secrets

### 1. Testing Secrets (Required for CI)

| Secret Name | Description | Where to Get | Required For |
|------------|-------------|--------------|--------------|
| `GOOGLE_API_KEY` | Google Gemini API key | [Google AI Studio](https://makersuite.google.com/app/apikey) | Running tests in CI |
| `SALLING_API_KEY` | Salling Group API key | [Salling Group Developer Portal](https://developer.sallinggroup.com/) | Running tests in CI |

**Note**: These can be test/dummy keys for CI if you don't want to use production keys.

### 2. Google Cloud Deployment Secrets (Required for Deployment)

| Secret Name | Description | Where to Get | Required For |
|------------|-------------|--------------|--------------|
| `GCP_SA_KEY` | Service account JSON key | See setup guide below | Deploying to Cloud Run |
| `GCP_PROJECT_ID` | Google Cloud project ID | GCP Console | Deploying to Cloud Run |
| `GCP_REGION` | Cloud Run region | Choose region (e.g., `us-central1`) | Deploying to Cloud Run (optional, defaults to `us-central1`) |

## Setup Instructions

### Step 1: Configure Testing Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret:

#### GOOGLE_API_KEY
- Name: `GOOGLE_API_KEY`
- Value: Your Google Gemini API key (starts with `AIza...`)
- Get it from: https://makersuite.google.com/app/apikey

#### SALLING_API_KEY
- Name: `SALLING_API_KEY`
- Value: Your Salling Group API key (format: `Bearer xxx...`)
- Get it from: https://developer.sallinggroup.com/

### Step 2: Configure Google Cloud Secrets (For Deployment)

#### Create GCP Service Account

```bash
# 1. Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# 2. Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com

# 3. Create service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deployment"

# 4. Get service account email
export SA_EMAIL=$(gcloud iam service-accounts list \
  --filter="displayName:GitHub Actions Deployment" \
  --format='value(email)')

# 5. Grant required roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

# 6. Create and download key
gcloud iam service-accounts keys create key.json \
  --iam-account="${SA_EMAIL}"

# 7. Display key (copy this entire JSON)
cat key.json

# 8. Clean up local key file
rm key.json
```

#### Add GCP Secrets to GitHub

1. Go to GitHub repository → **Settings** → **Secrets and variables** → **Actions**
2. Add these secrets:

**GCP_SA_KEY**
- Name: `GCP_SA_KEY`
- Value: Paste the entire JSON content from the service account key
- Format: `{"type": "service_account", "project_id": "...", ...}`

**GCP_PROJECT_ID**
- Name: `GCP_PROJECT_ID`
- Value: Your GCP project ID (e.g., `shopping-optimizer-prod`)

**GCP_REGION** (Optional)
- Name: `GCP_REGION`
- Value: Cloud Run region (e.g., `us-central1`, `europe-west1`)
- Default: `us-central1` if not set

### Step 3: Create Secrets in Google Secret Manager

These secrets are used by the deployed application:

```bash
# Create Google API key secret
echo -n "YOUR_ACTUAL_GOOGLE_API_KEY" | \
  gcloud secrets create google-api-key \
    --data-file=- \
    --replication-policy="automatic"

# Create Salling API key secret
echo -n "YOUR_ACTUAL_SALLING_API_KEY" | \
  gcloud secrets create salling-api-key \
    --data-file=- \
    --replication-policy="automatic"

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding google-api-key \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding salling-api-key \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 4: Configure GitHub Environments

#### Production Environment
1. Go to **Settings** → **Environments**
2. Click **New environment**
3. Name: `production`
4. Add protection rules:
   - ✅ Required reviewers (select team members)
   - ✅ Wait timer: 5 minutes (optional)
   - ✅ Deployment branches: `main` only

#### Staging Environment
1. Click **New environment**
2. Name: `staging`
3. Add protection rules:
   - ✅ Deployment branches: `develop` only

## Verification Checklist

Use this checklist to verify your setup:

### Testing Secrets
- [ ] `GOOGLE_API_KEY` is set in GitHub Secrets
- [ ] `SALLING_API_KEY` is set in GitHub Secrets
- [ ] CI tests pass with these secrets

### Deployment Secrets
- [ ] `GCP_SA_KEY` is set in GitHub Secrets
- [ ] `GCP_PROJECT_ID` is set in GitHub Secrets
- [ ] `GCP_REGION` is set (or using default)
- [ ] Service account has required IAM roles
- [ ] Cloud Run API is enabled
- [ ] Container Registry API is enabled
- [ ] Secret Manager API is enabled

### Google Secret Manager
- [ ] `google-api-key` secret exists in Secret Manager
- [ ] `salling-api-key` secret exists in Secret Manager
- [ ] Service account has access to both secrets

### GitHub Environments
- [ ] `production` environment is configured
- [ ] `staging` environment is configured
- [ ] Protection rules are set appropriately

## Testing Your Setup

### Test CI Pipeline
1. Create a feature branch
2. Make a small change
3. Push to GitHub
4. Create a PR to `develop`
5. Verify all CI checks pass:
   - ✅ Lint
   - ✅ Type Check
   - ✅ Tests
   - ✅ Integration Tests
   - ✅ Docker Build

### Test Staging Deployment
1. Merge PR to `develop` branch
2. Watch GitHub Actions for deployment
3. Verify staging deployment succeeds
4. Check Cloud Run console for service

### Test Production Deployment
1. Create PR from `develop` to `main`
2. Get approval from reviewers
3. Merge to `main`
4. Watch GitHub Actions for deployment
5. Verify production deployment succeeds
6. Test production URL

## Troubleshooting

### "Secret not found" Error
- Verify secret name matches exactly (case-sensitive)
- Check secret is in correct repository
- Ensure secret is not empty

### "Permission denied" Error
- Verify service account has required IAM roles
- Check service account key is valid JSON
- Ensure APIs are enabled in GCP

### "Secret Manager access denied" Error
- Verify secrets exist in Secret Manager
- Check service account has `secretmanager.secretAccessor` role
- Ensure secrets are in the same project

### Deployment Fails
- Check Cloud Run logs in GCP Console
- Verify environment variables are set
- Check Docker image was pushed successfully
- Verify service account permissions

## Security Best Practices

1. **Rotate Keys Regularly**
   - Rotate service account keys every 90 days
   - Update API keys when compromised

2. **Use Least Privilege**
   - Only grant necessary IAM roles
   - Use separate service accounts for different environments

3. **Monitor Access**
   - Enable audit logging in GCP
   - Review Secret Manager access logs
   - Monitor GitHub Actions logs

4. **Protect Secrets**
   - Never commit secrets to git
   - Don't print secrets in logs
   - Use GitHub's secret masking

5. **Environment Separation**
   - Use different GCP projects for staging/production
   - Use different API keys for each environment
   - Separate service accounts per environment

## Additional Resources

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GCP Service Accounts](https://cloud.google.com/iam/docs/service-accounts)
- [GCP Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Cloud Run IAM](https://cloud.google.com/run/docs/securing/managing-access)

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review `.github/CICD_SETUP.md` for detailed setup
3. Check `.github/DEVELOPER_GUIDE.md` for common issues
4. Review GitHub Actions logs for error messages
5. Check Cloud Run logs in GCP Console

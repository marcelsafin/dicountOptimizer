# Deployment Guide

## 🐳 Docker (Recommended)

**Prerequisites**: Docker & Docker Compose installed.

### Quick Start
```bash
# 1. Start services
docker-compose up -d

# 2. Check logs
docker-compose logs -f

# 3. Stop services
docker-compose down
```
App available at: `http://localhost:3000`

### Production Build
```bash
docker build -t shopping-optimizer:latest .
docker run -p 3000:3000 --env-file .env shopping-optimizer:latest
```

---

## ☁️ Google Cloud Run

**Prerequisites**: Google Cloud CLI (`gcloud`) installed & authenticated.

### 1. Build & Push
```bash
# Set project ID
export PROJECT_ID=your-project-id

# Submit build
gcloud builds submit --tag gcr.io/$PROJECT_ID/shopping-optimizer
```

### 2. Deploy
```bash
gcloud run deploy shopping-optimizer \
  --image gcr.io/$PROJECT_ID/shopping-optimizer \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_API_KEY=...,SALLING_GROUP_API_KEY=..."
```

---

## 🔧 Manual Deployment (Linux)

**Requirements**: Python 3.11+, Gunicorn, Uvicorn, Redis.

```bash
# 1. Install dependencies
pip install -r requirements.txt gunicorn uvicorn[standard]

# 2. Start Gunicorn with Uvicorn workers
gunicorn app:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8080
```

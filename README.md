# Shopping Optimizer 🛒

**Save money and reduce food waste with AI-powered meal planning.**

The Shopping Optimizer is an intelligent agent that fetches real-time food waste discounts from Danish grocery stores (Netto, Føtex, Bilka) and uses Google's Gemini 2.5 Pro AI to generate creative, delicious meal plans based on what's available nearby.

## Key Features
-   🌱 **Reduce Food Waste**: Prioritizes products expiring soon.
-   💰 **Save Money**: Finds discounts of 30-70%.
-   🤖 **AI Chef**: Generates recipes based on available ingredients.
-   📍 **Local Search**: Finds deals within 2km of your location.
-   🚀 **Enterprise Architecture**: Built with Python, Google ADK, and Async/Await.

## Quick Start

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY and SALLING_GROUP_API_KEY
```

### 2. Run with Docker (Recommended)
```bash
docker-compose up -d
open http://localhost:3000
```

### 3. Run Locally
```bash
pip install -r requirements.txt
gunicorn app:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:3000 --reload
```

## Documentation

-   **[Architecture](docs/ARCHITECTURE.md)**: System design, agents, and layers.
-   **[Configuration](docs/CONFIGURATION.md)**: Environment variables and API keys.
-   **[Development](docs/DEVELOPMENT.md)**: Testing, type checking, and local setup.
-   **[Troubleshooting](docs/TROUBLESHOOTING.md)**: Common errors and solutions.
-   **[Deployment](docs/DEPLOYMENT_GUIDE.md)**: Production deployment guide.

## Project Status
✅ **Stable & Verified**. This project follows enterprise-grade standards with 100% type safety and comprehensive testing.

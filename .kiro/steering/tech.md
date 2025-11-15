---
inclusion: always
---

# Technology Stack

This document defines the core technology stack for the Shopping Optimizer project. Kiro must use these technologies for all implementations.

## Core

**Language**: Python 3.11+

**Agent Framework**: Google ADK (`google.genai.adk`)

## Data & Validation

**Data Models**: Pydantic (`pydantic.BaseModel`). All data transfer objects (DTOs), API schemas, and function inputs/outputs MUST use Pydantic models for validation.

**Configuration**: Pydantic Settings (`pydantic_settings.BaseSettings`). All configuration MUST be loaded via this library.

**Currency**: `Decimal` from the `decimal` module MUST be used for all monetary values. `float` is forbidden for currency.

## API & Infrastructure

**HTTP Client**: `httpx` (async client: `httpx.AsyncClient`).

**Retry Logic**: `tenacity` (using `@retry` decorator) for all external API calls at the infrastructure (transport) layer.

**Logging**: `structlog` for structured, JSON-based logging.

## Testing

**Framework**: `pytest`

**Async Tests**: `pytest-asyncio` (using `@pytest.mark.asyncio`)

**HTTP Mocking**: `pytest-httpx` (for mocking httpx clients)

**Object Mocking**: `unittest.mock` (`MagicMock`, `AsyncMock`, `patch`) or `pytest-monkeypatch`.

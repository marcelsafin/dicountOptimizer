# System Architecture

## Architecture Overview

The Shopping Optimizer follows a modern, enterprise-grade architecture using **Google ADK (Agent Development Kit)** with comprehensive type safety, dependency injection, and clean separation of concerns. The system is built on four distinct layers:

```
┌─────────────────────────────────────────────────────────┐
│              Presentation Layer                          │
│  (Flask API, CLI, Web UI)                               │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Agent Layer (Google ADK)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ MealSuggester│  │IngredientMap │  │OutputFormatter│ │
│  │    Agent     │  │    Agent     │  │    Agent      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │     ShoppingOptimizerAgent (Root Agent)          │  │
│  │  Orchestrates all sub-agents with DI             │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Business Logic Layer                        │
│  (Services, Domain Models, Validation)                  │
│  - InputValidationService                               │
│  - DiscountMatcherService                               │
│  - MultiCriteriaOptimizerService                        │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Infrastructure Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Salling API  │  │ Google Maps  │  │   Cache      │ │
│  │  Repository  │  │  Repository  │  │  Repository  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Agent Composition Pattern

The root `ShoppingOptimizerAgent` composes specialized sub-agents using **dependency injection**:

```
ShoppingOptimizerAgent (Root)
├── InputValidationService (validates user input)
├── DiscountMatcherService (fetches and filters discounts)
├── MealSuggesterAgent (AI meal suggestions via Gemini)
├── IngredientMapperAgent (maps meals to products)
├── MultiCriteriaOptimizerService (optimizes purchases)
└── OutputFormatterAgent (formats recommendations)
```

Each agent:
- Has a **single responsibility** (SOLID principles)
- Uses **typed tool functions** with Pydantic models
- Validates **inputs/outputs** automatically
- Can be **tested independently**
- Implements **retry and error handling**
- Supports **graceful fallbacks**

## High-Level Workflow

```
User Input (address or coordinates)
    ↓
Input Validation (location, timeframe, preferences)
    ↓
Discount Matching (fetch from Salling API, filter by distance)
    ↓
Meal Suggestion (AI-powered via Gemini OR use provided meal plan)
    ↓
Ingredient Mapping (map meals to available products)
    ↓
Multi-Criteria Optimization (select best purchases)
    ↓
Output Formatting (tips, motivation, store summary)
    ↓
Display Results to User
```

## Key Technologies

- **Backend**: Python 3.11+, Flask, Google ADK
- **Type Safety**: Pydantic, mypy strict mode, Protocol classes
- **AI**: Google Gemini 2.0 Flash for agent functionality
- **APIs**: Salling Group Food Waste API, Google Maps API
- **Architecture**: Dependency Injection, Repository Pattern, Factory Pattern
- **Async**: httpx with connection pooling, async/await throughout
- **Caching**: In-memory cache with TTL
- **Logging**: Structured logging with correlation IDs
- **Frontend**: Vanilla JavaScript, HTML5, CSS3

## Type Safety

The codebase achieves **100% type coverage** in all refactored modules using:

- **Pydantic models** for all data structures with validation
- **Protocol classes** for dependency injection interfaces
- **mypy strict mode** for static type checking
- **Gradual typing strategy** for legacy code migration

See [Type Checking Documentation](TYPE_CHECKING_STRATEGY.md) for details.

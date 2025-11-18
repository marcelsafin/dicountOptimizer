# Type Checking Strategy

## Overview

This document describes the gradual typing strategy used in the Shopping Optimizer modernization project. The strategy allows new, refactored code to be fully type-safe while legacy code remains unchanged during migration.

## Strategy: Gradual Typing with Per-Module Configuration

### Philosophy

- **New code is strict**: All refactored modules must pass mypy strict mode with 100% type coverage
- **Legacy code is permissive**: Existing code can remain as-is during migration
- **Incremental migration**: Modules are migrated one at a time, with strict checking enabled as they're refactored
- **No compromises**: Refactored code has zero `type: ignore` comments

### Configuration

Type checking is configured in `mypy.ini` with two policy levels:

#### Global Policy (Permissive)
```ini
[mypy]
strict = False
disallow_untyped_defs = False
# ... other permissive settings
```

This allows legacy code to remain unchanged during migration.

#### Per-Module Overrides (Strict)
```ini
[mypy-agents.discount_optimizer.domain.*]
strict = True
disallow_untyped_defs = True
# ... other strict settings
```

Refactored modules have strict checking enforced.

## Refactored Modules (100% Type Coverage)

The following modules have been refactored and pass strict type checking:

### 1. Domain Layer
- `agents/discount_optimizer/domain/models.py` - Pydantic models with validation
- `agents/discount_optimizer/domain/protocols.py` - Protocol interfaces for DI
- `agents/discount_optimizer/domain/exceptions.py` - Exception hierarchy

**Type Safety Features:**
- All models use Pydantic BaseModel with strict validation
- Field constraints (min/max, regex, decimal places)
- Custom validators for business logic
- Immutable models where appropriate (frozen=True)
- Protocol classes for structural typing

### 2. Infrastructure Layer
- `agents/discount_optimizer/infrastructure/salling_repository.py` - Salling API client
- `agents/discount_optimizer/infrastructure/google_maps_repository.py` - Google Maps client
- `agents/discount_optimizer/infrastructure/cache_repository.py` - Caching layer

**Type Safety Features:**
- Async/await with proper type annotations
- Protocol implementations with runtime checking
- Retry decorators with typed exceptions
- Connection pooling with typed clients

### 3. Configuration & Logging
- `agents/discount_optimizer/config.py` - Pydantic Settings
- `agents/discount_optimizer/logging.py` - Structured logging setup

**Type Safety Features:**
- Environment variable validation with Pydantic Settings
- SecretStr for sensitive data
- Literal types for enums
- Typed logging context

### 4. Agent Layer
- `agents/discount_optimizer/agents/meal_suggester_agent.py` - Meal suggestion agent
- `agents/discount_optimizer/agents/ingredient_mapper_agent.py` - Ingredient mapping agent
- `agents/discount_optimizer/agents/output_formatter_agent.py` - Output formatting agent
- `agents/discount_optimizer/agents/shopping_optimizer_agent.py` - Root orchestration agent

**Type Safety Features:**
- Pydantic models for all tool inputs/outputs
- Typed agent composition
- Structured logging with typed context
- Async tool functions with proper annotations

### 5. Services Layer
- `agents/discount_optimizer/services/discount_matcher_service.py` - Discount matching logic
- `agents/discount_optimizer/services/input_validation_service.py` - Input validation
- `agents/discount_optimizer/services/multi_criteria_optimizer_service.py` - Optimization logic

**Type Safety Features:**
- Pure Python business logic with full type annotations
- Decimal for financial calculations
- Typed scoring algorithms
- Sequence types for covariance

### 6. Factory
- `agents/discount_optimizer/factory.py` - Dependency injection factory

**Type Safety Features:**
- Typed factory methods
- Protocol-based dependency injection
- Configuration validation

## Legacy Modules (Ignored During Migration)

The following modules are explicitly ignored during migration:

```ini
[mypy-agents.discount_optimizer.salling_api_client]
ignore_errors = True

[mypy-agents.discount_optimizer.google_maps_service]
ignore_errors = True

# ... other legacy modules
```

These modules will be gradually refactored and moved to the new architecture.

## Type: Ignore Comments

**Current Count: 0**

The refactored codebase has **zero** `type: ignore` comments. All type issues have been resolved through proper typing.

### Policy on Type: Ignore

If a `type: ignore` comment becomes necessary:

1. **Document the reason**: Add a comment explaining why it's needed
2. **Use specific error codes**: Use `# type: ignore[error-code]` not just `# type: ignore`
3. **Create a tracking issue**: Document the technical debt
4. **Plan for removal**: Add a TODO with a plan to remove it

Example (if needed):
```python
# type: ignore[attr-defined]  # TODO: Remove when google.genai.adk adds type stubs
```

## Running Type Checks

### Local Development

Check all refactored modules:
```bash
./scripts/type_check.sh
```

Check specific module:
```bash
mypy agents/discount_optimizer/domain/ --show-error-codes --pretty
```

Check with strict mode:
```bash
mypy agents/discount_optimizer/domain/ --strict
```

### CI/CD Pipeline

Add to your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Type Check
  run: |
    pip install mypy
    ./scripts/type_check.sh
```

```yaml
# GitLab CI example
type-check:
  script:
    - pip install mypy
    - ./scripts/type_check.sh
```

## Type Coverage Metrics

| Layer | Files | Type Coverage | Status |
|-------|-------|---------------|--------|
| Domain | 3 | 100% | ✅ Complete |
| Infrastructure | 3 | 100% | ✅ Complete |
| Config & Logging | 2 | 100% | ✅ Complete |
| Agents | 4 | 100% | ✅ Complete |
| Services | 3 | 100% | ✅ Complete |
| Factory | 1 | 100% | ✅ Complete |
| **Total Refactored** | **16** | **100%** | ✅ **Complete** |

## Best Practices

### 1. Use Pydantic for Data Validation
```python
from pydantic import BaseModel, Field

class Location(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
```

### 2. Use Protocol for Interfaces
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Repository(Protocol):
    async def fetch(self) -> list[Item]: ...
```

### 3. Use Literal for Enums
```python
from typing import Literal

Environment = Literal['dev', 'staging', 'production']
```

### 4. Use Decimal for Money
```python
from decimal import Decimal

price: Decimal = Decimal('19.99')
```

### 5. Use Sequence for Covariance
```python
from typing import Sequence

def process(items: Sequence[Item]) -> None:
    # Accepts list[Item], tuple[Item], etc.
    ...
```

## Migration Checklist

When refactoring a new module:

- [ ] Add type hints to all functions and methods
- [ ] Use Pydantic models for data structures
- [ ] Replace dict with TypedDict or Pydantic models
- [ ] Add Protocol interfaces for dependencies
- [ ] Enable strict checking in mypy.ini
- [ ] Run `mypy <module>` and fix all errors
- [ ] Remove from legacy ignore list
- [ ] Update this documentation

## Troubleshooting

### Common Issues

**Issue: "Incompatible types in assignment"**
- Solution: Check if you're mixing Optional and non-Optional types
- Use `| None` for optional types

**Issue: "List is invariant"**
- Solution: Use `Sequence` instead of `list` for function parameters
- Lists are invariant, Sequences are covariant

**Issue: "Cannot determine type of X"**
- Solution: Add explicit type annotation
- Mypy can't always infer complex types

**Issue: "Module has no attribute"**
- Solution: Check if third-party library has type stubs
- Add to `[mypy-library.*]` with `ignore_missing_imports = True`

## Resources

- [Mypy Documentation](https://mypy.readthedocs.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Type Hints PEP 484](https://www.python.org/dev/peps/pep-0484/)
- [Protocols PEP 544](https://www.python.org/dev/peps/pep-0544/)

## Maintenance

This document should be updated when:
- New modules are refactored and added to strict checking
- Type: ignore comments are added (with justification)
- Type checking strategy changes
- New best practices are discovered

Last Updated: November 2025

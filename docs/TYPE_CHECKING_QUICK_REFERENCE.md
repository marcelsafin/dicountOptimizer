# Type Checking Quick Reference

## Quick Commands

### Run All Type Checks
```bash
./scripts/type_check.sh
```

### Check Specific Module
```bash
mypy agents/discount_optimizer/domain/
mypy agents/discount_optimizer/infrastructure/
mypy agents/discount_optimizer/agents/
mypy agents/discount_optimizer/services/
```

### Check Single File
```bash
mypy agents/discount_optimizer/config.py
```

### Show Error Codes
```bash
mypy <path> --show-error-codes --pretty
```

## Common Type Patterns

### 1. Pydantic Models
```python
from pydantic import BaseModel, Field
from decimal import Decimal

class Product(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(gt=0, decimal_places=2)
    quantity: int = Field(ge=0)
```

### 2. Protocol Interfaces
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Repository(Protocol):
    async def fetch(self, id: str) -> Item | None: ...
    async def save(self, item: Item) -> None: ...
```

### 3. Async Functions
```python
async def fetch_data(url: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

### 4. Union Types (Python 3.11+)
```python
# Use | instead of Union
def process(data: str | int) -> str:
    return str(data)

# Optional with |
def get_user(id: str) -> User | None:
    ...
```

### 5. Literal Types
```python
from typing import Literal

Environment = Literal['dev', 'staging', 'production']

def configure(env: Environment) -> None:
    ...
```

### 6. Sequence for Covariance
```python
from typing import Sequence

# Use Sequence for read-only parameters
def process_items(items: Sequence[Item]) -> None:
    for item in items:
        print(item)

# Accepts list[Item], tuple[Item], etc.
```

### 7. Decimal for Money
```python
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Annotated

class Price(BaseModel):
    amount: Annotated[Decimal, Field(gt=0, decimal_places=2)]
```

### 8. TypedDict (Alternative to Pydantic)
```python
from typing import TypedDict

class UserDict(TypedDict):
    name: str
    age: int
    email: str
```

## Common Errors and Solutions

### Error: "Incompatible types in assignment"
```python
# ❌ Wrong
value: str = None  # Error!

# ✅ Correct
value: str | None = None
```

### Error: "List is invariant"
```python
# ❌ Wrong
def process(items: list[dict[str, Any]]) -> None:
    ...

# ✅ Correct
from typing import Sequence
def process(items: Sequence[dict[str, Any]]) -> None:
    ...
```

### Error: "Cannot determine type"
```python
# ❌ Wrong
data = {}  # Type is dict[Unknown, Unknown]

# ✅ Correct
data: dict[str, Any] = {}
```

### Error: "Module has no attribute"
```python
# Add to mypy.ini:
[mypy-third_party_library.*]
ignore_missing_imports = True
```

## Mypy Configuration Levels

### Permissive (Legacy Code)
```ini
[mypy]
strict = False
disallow_untyped_defs = False
```

### Strict (Refactored Code)
```ini
[mypy-agents.discount_optimizer.domain.*]
strict = True
disallow_untyped_defs = True
disallow_any_generics = True
```

## Type Coverage Status

| Module | Status | Coverage |
|--------|--------|----------|
| Domain | ✅ | 100% |
| Infrastructure | ✅ | 100% |
| Agents | ✅ | 100% |
| Services | ✅ | 100% |
| Config | ✅ | 100% |
| Logging | ✅ | 100% |
| Factory | ✅ | 100% |

## CI/CD Integration

### GitHub Actions
```yaml
- name: Type Check
  run: ./scripts/type_check.sh
```

### Pre-commit Hook
```bash
# .git/hooks/pre-commit
#!/bin/bash
./scripts/type_check.sh
```

## Resources

- [Mypy Docs](https://mypy.readthedocs.io/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [Type Checking Strategy](./TYPE_CHECKING_STRATEGY.md)
- [Validation Report](./TYPE_CHECKING_VALIDATION_REPORT.md)

## Need Help?

1. Check error code: `mypy <file> --show-error-codes`
2. Read error message carefully
3. Check this quick reference
4. Check full documentation
5. Ask team for help

---

**Last Updated:** November 15, 2025

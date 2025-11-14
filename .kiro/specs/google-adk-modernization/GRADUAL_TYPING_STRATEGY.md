# Gradual Typing Strategy

## Problem
When introducing strict type checking to an existing codebase, mypy follows import chains and reports errors in all imported modules. This creates a "refactoring trap" where new, type-safe code cannot pass strict checks because it imports legacy code.

## Solution: Per-Module Configuration

### Global Policy (Permissive)
```ini
[mypy]
strict = False
disallow_untyped_defs = False
# ... other permissive settings
```

This allows legacy code to exist without type errors.

### Strict Policy (Refactored Modules Only)
```ini
[mypy-agents.discount_optimizer.domain.*]
strict = True
disallow_untyped_defs = True
disallow_untyped_calls = False  # Allow calls to legacy code
# ... other strict settings
```

This enforces strict checking only on refactored modules.

### Legacy Code (Explicit Ignore)
```ini
[mypy-agents.discount_optimizer.salling_api_client]
ignore_errors = True

[mypy-agents.discount_optimizer.agent]
ignore_errors = True
# ... other legacy modules
```

This explicitly silences errors in legacy modules during migration.

## Verification
```bash
# Only check refactored modules
mypy agents/discount_optimizer/domain/

# Success: no issues found in 3 source files
```

## Migration Path
1. Start with global permissive policy
2. Refactor one module at a time
3. Add strict override for refactored module
4. Add ignore_errors for legacy modules it imports
5. Gradually expand strict checking as more modules are refactored
6. Eventually remove ignore_errors as legacy code is refactored

## Key Insight
Don't fight your tools. Configure mypy to support gradual migration rather than trying to isolate files with command-line flags.

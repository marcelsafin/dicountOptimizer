---
inclusion: always
---

# Architecture Patterns

This file defines our core "Separation of Concerns" architecture.

## 1. AGENT vs. SERVICE (Kritisk Skillnad)

Detta är den centrala arkitekturella regeln. Du måste skilja på deterministisk logik och AI-logik.

### AGENT (AI / Icke-deterministisk)

**Syfte**: Används endast för komplexa, icke-deterministiska uppgifter som kräver AI (Gemini).

**Exempel**:
- `MealSuggesterAgent` (Kreativitet, språkförståelse)
- `IngredientMapperAgent` (Flerspråkig, "fuzzy" mappning)
- `OutputFormatterAgent` (Generera kreativa "tips")

**Plats**: `agents/discount_optimizer/agents/`

**Krav**: Måste anropa `agent.run()` (eller liknande) för att använda Gemini.

### SERVICE (Python / Deterministisk)

**Syfte**: Används för all ren, deterministisk affärslogik.

**Exempel**:
- `DiscountMatcherService` (Filtrering, sortering)
- `MultiCriteriaOptimizerService` (Matematik, poängsättning)
- `InputValidationService` (Validering av data)

**Plats**: `agents/discount_optimizer/services/`

**Krav**: Får INTE anropa Gemini. Är en ren Python-klass.

## 2. Dependency Injection (Fabriken)

- All orkestrering sker i `ShoppingOptimizerAgent`.
- Alla beroenden (Agenter och Tjänster) måste injiceras via `AgentFactory` (Task 17).
- Kärnlogik (Agenter, Tjänster) får aldrig direkt instansiera ett Repository (som `SallingDiscountRepository`). De måste ta emot det via `__init__` (DI).

## 3. Mypy Gradvis Typning

Vi använder en "gradual typing"-strategi.

**Legacy-kod**: (t.ex. `app.py`) är i den globala `[mypy]`-sektionen med `strict = False`.

**Ny Kod**: All ny kod som vi skriver (allt i `agents/discount_optimizer/`) måste läggas till i `mypy.ini` under en "strict override"-sektion.

**Exempel**:
```ini
[mypy-agents.discount_optimizer.domain.*]
strict = True

[mypy-agents.discount_optimizer.infrastructure.*]
strict = True

[mypy-agents.discount_optimizer.services.*]
strict = True

[mypy-agents.discount_optimizer.agents.*]
strict = True

[mypy-agents.discount_optimizer.config]
strict = True

[mypy-agents.discount_optimizer.logging]
strict = True

[mypy-agents.discount_optimizer.factory]
strict = True
```

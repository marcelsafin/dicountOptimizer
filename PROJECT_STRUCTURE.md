# Shopping Optimizer - Projektstruktur

## Katalogstruktur

```
dicountOptimizer/
├── .env                              # API-nyckel (GOOGLE_API_KEY)
├── .env.example                      # Exempel på .env fil
├── .gitignore                        # Git ignore fil
├── requirements.txt                  # Python dependencies
├── README.md                         # Huvuddokumentation
├── SETUP_GUIDE.md                    # Setup instruktioner
├── PROJECT_STRUCTURE.md              # Detta dokument
├── demo.py                           # Demo script för att testa funktioner
│
├── .kiro/
│   └── specs/
│       └── shopping-optimizer/
│           ├── requirements.md       # Krav specifikation
│           ├── design.md             # Design dokument
│           └── tasks.md              # Implementation tasks
│
├── templates/
│   └── index.html                    # Web UI huvudsida
│
├── static/
│   ├── css/
│   │   └── styles.css                # UI styling
│   └── js/
│       └── app.js                    # Frontend JavaScript
│
└── agents/
    ├── agent.py                      # ADK entry point (wrapper)
    └── discount_optimizer/
        ├── __init__.py               # Package exports
        ├── agent.py                  # Huvudagent med root_agent
        └── models.py                 # Datamodeller och mock data
```

## Filbeskrivningar

### Root-nivå filer

- **.env** - Innehåller Google AI API-nyckel (läggs inte till i git)
- **requirements.txt** - Python dependencies (google-adk, python-dotenv)
- **demo.py** - Standalone script för att testa agent-funktioner utan ADK
- **README.md** - Huvuddokumentation med setup och användningsinstruktioner
- **SETUP_GUIDE.md** - Detaljerad guide för att sätta upp projektet

### agents/discount_optimizer/

Detta är huvudpaketet för agenten:

- **agent.py** - Innehåller:
  - `root_agent` - ADK Agent definition
  - `get_discounts_by_location()` - Hämtar erbjudanden
  - `filter_products_by_preferences()` - Filtrerar produkter
  - `optimize_shopping_plan()` - Skapar optimerad inköpsplan

- **models.py** - Innehåller:
  - Dataclasses: `Location`, `Timeframe`, `OptimizationPreferences`, `UserInput`, `DiscountItem`, `Purchase`, `ShoppingRecommendation`
  - `MOCK_DISCOUNTS` - Lista med 20 produkter från 5 butiker i Köpenhamn
  - `MEAL_INGREDIENTS` - Mapping från måltider till ingredienser

- **__init__.py** - Exporterar alla publika funktioner och klasser

### agents/agent.py

Wrapper-fil som gör att ADK kan hitta agenten. Importerar `root_agent` från `discount_optimizer.agent`.

## Hur man använder

### Kör demo script
```bash
python3 demo.py
```

### Starta ADK web server
```bash
adk web --port 8000
```

Öppna sedan http://127.0.0.1:8000 i din webbläsare.

### Importera i Python
```python
from agents.discount_optimizer import (
    get_discounts_by_location,
    optimize_shopping_plan,
    MOCK_DISCOUNTS,
    MEAL_INGREDIENTS
)

# Hämta erbjudanden
discounts = get_discounts_by_location("Köpenhamn")

# Skapa inköpsplan
plan = optimize_shopping_plan("Köpenhamn", "tacos")
```

## Nästa steg

Fortsätt med task 2 i `.kiro/specs/shopping-optimizer/tasks.md` för att implementera fler funktioner!

## Viktiga anteckningar

- API-nyckeln läses från `.env` filen i root
- Alla datamodeller finns i `models.py`
- Mock data innehåller danska butiker (Netto, Føtex, Rema 1000) nära Köpenhamn
- Måltidsdatabasen stödjer både danska och engelska namn

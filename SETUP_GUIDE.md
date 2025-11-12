# Snabbguide: Sätt upp Shopping Optimizer

## Steg-för-steg instruktioner

### 1. Skaffa Google AI API-nyckel

1. Gå till: https://aistudio.google.com/app/apikey
2. Logga in med ditt Google-konto
3. Klicka på "Create API Key"
4. Kopiera din API-nyckel

### 2. Konfigurera projektet

Öppna `.env` filen och ersätt `your_api_key_here` med din API-nyckel:

```bash
GOOGLE_API_KEY=AIzaSy...  # Din riktiga nyckel här
```

### 3. Installera dependencies (om du inte redan gjort det)

```bash
# Aktivera virtual environment
source .venv/bin/activate

# Installera
pip install -r requirements.txt
```

### 4. Starta agenten

```bash
adk web --port 8000
```

### 5. Testa agenten

Öppna http://127.0.0.1:8000 i din webbläsare och prova:

**Exempel på frågor:**
- "Jag vill handla tacos i Köpenhamn, vad är de bästa erbjudandena?"
- "Ge mig en inköpsplan för pasta bolognese med fokus på ekologiska produkter"
- "Vilka butiker har bäst erbjudanden på grönsaker just nu?"

## Vanliga problem

### Problem: "API key not found" eller liknande fel

**Lösning:**
1. Kontrollera att `.env` filen finns i projektets root-mapp
2. Kontrollera att API-nyckeln är korrekt kopierad (ingen extra whitespace)
3. Starta om ADK-servern efter att du lagt till nyckeln

### Problem: Ingen trace syns i dev-ui

**Lösning:**
1. Kontrollera att API-nyckeln är korrekt
2. Skicka ett meddelande till agenten i chatten
3. Kolla terminalen för felmeddelanden
4. Prova att starta om servern: `Ctrl+C` och sedan `adk web --port 8000` igen

### Problem: "Module not found" fel

**Lösning:**
```bash
# Kontrollera att virtual environment är aktiverat
source .venv/bin/activate

# Installera om dependencies
pip install -r requirements.txt
```

## Nästa steg

När allt fungerar kan du fortsätta med implementationen av de andra tasks i `.kiro/specs/shopping-optimizer/tasks.md`!

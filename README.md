# Discount Optimizer Agent

En AI-agent som optimerar matinköp baserat på erbjudanden, användarens plats och preferenser.

## Setup

### 1. Installera dependencies

```bash
# Skapa virtual environment
python3 -m venv .venv
source .venv/bin/activate  # På macOS/Linux
# eller
.venv\Scripts\activate  # På Windows

# Installera dependencies
pip install -r requirements.txt
```

### 2. Konfigurera API-nyckel

1. Skaffa en Google AI API-nyckel från: https://aistudio.google.com/app/apikey
2. Öppna `.env` filen i projektets root
3. Ersätt `your_api_key_here` med din faktiska API-nyckel:

```bash
GOOGLE_API_KEY=din_riktiga_api_nyckel_här
```

**VIKTIGT:** Dela aldrig din API-nyckel publikt! Filen `.env` är redan i `.gitignore`.

## Kör agenten

### Web UI (rekommenderat)

```bash
# Starta Flask web server
python app.py
```

Öppna sedan din webbläsare på: http://127.0.0.1:8000

### Alternativa sätt

```bash
# ADK Web UI
adk web --port 8001

# CLI mode
adk run discount_optimizer
```

## Exempel på användning

"Jag vill handla tacos i Köpenhamn under veckan och spara pengar, ge mig en optimerad inköpsplan!"

## Felsökning

### Ingen trace i dev-ui?

Om du inte ser någon trace i dev-ui:
1. Kontrollera att din API-nyckel är korrekt konfigurerad i `.env`
2. Starta om ADK-servern efter att du lagt till API-nyckeln
3. Kolla terminalen för eventuella felmeddelanden
4. Testa att skicka ett meddelande till agenten i chatten

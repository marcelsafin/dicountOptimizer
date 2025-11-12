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

### 2. Konfigurera API-nycklar

#### Salling Group API (för riktiga rabattdata)

1. Skaffa en Salling Group API-nyckel från: https://developer.sallinggroup.com/
2. Registrera dig och skapa en ny applikation
3. Kopiera din API-nyckel

#### Google AI API (för AI-funktioner)

1. Skaffa en Google AI API-nyckel från: https://aistudio.google.com/app/apikey

#### Google Maps API (för geolokalisering)

1. Gå till Google Cloud Console: https://console.cloud.google.com/
2. Aktivera följande APIs:
   - Geocoding API
   - Places API
   - Distance Matrix API
3. Skapa en API-nyckel

#### Konfigurera .env-filen

Öppna `.env` filen i projektets root och lägg till dina API-nycklar:

```bash
SALLING_GROUP_API_KEY=din_salling_api_nyckel_här
GOOGLE_API_KEY=din_google_ai_api_nyckel_här
GOOGLE_MAPS_API_KEY=din_google_maps_api_nyckel_här
```

**VIKTIGT:** Dela aldrig dina API-nycklar publikt! Filen `.env` är redan i `.gitignore`.

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

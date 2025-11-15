# Shopping Optimizer - Food Waste Meal Planner

An intelligent AI agent that helps you save money and reduce food waste by finding discounted food waste products within 2km of your location and generating creative meal suggestions using Gemini 2.5 Pro.

## What It Does

The Shopping Optimizer fetches real-time food waste discounts from major Danish grocery chains (Netto, Føtex, Bilka, BR) through the Salling Group API, then uses Google's Gemini 2.5 Pro AI to suggest creative meals you can make with the available products. It's designed to:

- **Reduce food waste**: Focus on products that need to be sold quickly
- **Save money**: Find the best discounts (often 30-70% off)
- **Simplify shopping**: Get meal ideas based on what's actually available nearby
- **Support local**: Only shows stores within 2km (walking/biking distance)

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Get API Keys

#### Salling Group API (Required)

The Salling Group API provides real-time food waste data from Danish grocery stores.

1. Visit: https://developer.sallinggroup.com/
2. Click "Sign Up" and create an account
3. Go to "Applications" and create a new application
4. Copy your API key (Bearer token)
5. **Important**: This API only works for stores in Denmark

**API Details**:
- Endpoint used: `https://api.sallinggroup.com/v1/food-waste/`
- Rate limits: 10,000 requests/day (free tier)
- Coverage: Netto, Føtex, Bilka, BR stores in Denmark
- Documentation: https://developer.sallinggroup.com/api-reference#food-waste-api

#### Google Gemini API (Required)

Gemini 2.5 Pro generates creative meal suggestions based on available products.

1. Visit: https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

**API Details**:
- Model used: gemini-2.5-pro
- Free tier: 60 requests per minute
- Used for: AI meal generation and recipe suggestions
- Documentation: https://ai.google.dev/gemini-api/docs

#### Configure Environment Variables

Create or update the `.env` file in the project root:

```bash
SALLING_GROUP_API_KEY=your_salling_api_key_here
GOOGLE_API_KEY=your_gemini_api_key_here
```

**Security Note**: Never share your API keys publicly! The `.env` file is already in `.gitignore`.

### 3. Run the Application

```bash
# Start Flask web server
python app.py
```

Open your browser at: http://127.0.0.1:8000

## How to Use

### Web Interface

1. **Enter Your Location**:
   - Click "Use My Location" to auto-detect (requires browser permission)
   - Or manually enter latitude and longitude coordinates
   - Example: Copenhagen center is approximately 55.6761, 12.5683

2. **Search for Food Waste**:
   - Click "Find Meals" button
   - The system searches within a fixed 2km radius
   - Wait for results (typically 5-15 seconds)

3. **Review Meal Suggestions**:
   - See 3-5 AI-generated meal ideas
   - Each meal shows required products, stores, and savings
   - Products are grouped by store for easy shopping

4. **Check Savings & Tips**:
   - View total monetary savings in DKK
   - Get tips on products expiring soon
   - See which stores to visit

### Understanding the 2km Radius

The system uses a **fixed 2km search radius** for several reasons:

- **Walkable/Bikeable**: Encourages sustainable transportation
- **Fresh Products**: Food waste items need to be used quickly
- **Realistic Shopping**: Most people shop within their neighborhood
- **Better Results**: Focuses on truly nearby options

Distance is calculated using the Haversine formula for geographic accuracy.

### Food Waste Focus

This system specifically targets **food waste products** - items that stores need to sell quickly before expiration. Benefits include:

- **Higher Discounts**: Typically 30-70% off regular prices
- **Environmental Impact**: Helps reduce food waste
- **Quality Products**: Still fresh, just need to be used soon
- **Variety**: Changes daily based on what's available

**Important**: Plan to use these products within 1-3 days of purchase.

## System Architecture

### High-Level Workflow

```
User Location Input
    ↓
Input Validation (coordinates, 2km radius)
    ↓
Salling Group API (fetch food waste within 2km)
    ↓
Distance Calculation (Haversine formula)
    ↓
Gemini 2.5 Pro API (generate meal suggestions)
    ↓
Savings Calculation
    ↓
Output Formatting
    ↓
Display Results to User
```

### Component Architecture

**Presentation Layer**:
- Flask web server (`app.py`)
- HTML/CSS/JavaScript frontend (`templates/`, `static/`)

**Agent Layer**:
- ADK agent orchestration (`agents/discount_optimizer/agent.py`)
- Workflow coordination and error handling

**Integration Layer**:
- `SallingAPIClient`: Fetches food waste data with 24h caching
- `MealSuggester`: Interfaces with Gemini 2.5 Pro for AI meal generation

**Business Logic Layer**:
- `InputValidator`: Validates location coordinates
- `DiscountMatcher`: Filters products by distance, sorts by proximity
- `SavingsCalculator`: Calculates total savings and generates insights
- `OutputFormatter`: Formats results for display

**Data Layer**:
- In-memory cache (24h TTL) for API responses
- Data models: `UserInput`, `Location`, `DiscountItem`, `MealSuggestion`

### Key Technologies

- **Backend**: Python 3.9+, Flask, ADK (Agent Development Kit)
- **AI**: Google Gemini 2.5 Pro for meal generation
- **APIs**: Salling Group Food Waste API
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Distance Calculation**: Haversine formula

## Troubleshooting

### Common Issues

#### "No food waste products found"

**Possible Causes**:
- Location is outside Denmark (Salling API only covers Danish stores)
- No stores within 2km radius
- No food waste available at nearby stores today

**Solutions**:
- Try a different location in Denmark (e.g., Copenhagen, Aarhus, Odense)
- Check that coordinates are correct (latitude, longitude)
- Try again later - food waste inventory changes throughout the day

#### "API Error: 401 Unauthorized"

**Cause**: Invalid or missing Salling Group API key

**Solutions**:
1. Verify your API key is correct in `.env` file
2. Check that you copied the entire key (no extra spaces)
3. Ensure your Salling Group account is active
4. Generate a new API key if needed

#### "API Error: 429 Too Many Requests"

**Cause**: Exceeded Salling Group API rate limit (10,000 requests/day)

**Solutions**:
- Wait a few minutes before trying again
- The system caches responses for 24h to minimize API calls
- Check if you have other applications using the same API key

#### "Gemini API Error"

**Possible Causes**:
- Invalid Google API key
- Rate limit exceeded (60 requests/minute)
- Network connectivity issues

**Solutions**:
1. Verify your Google API key in `.env` file
2. Wait a minute if you've made many requests
3. Check your internet connection
4. Ensure Gemini API is enabled in your Google Cloud project

#### "Invalid coordinates"

**Cause**: Latitude or longitude values are out of valid range

**Solutions**:
- Latitude must be between -90 and 90
- Longitude must be between -180 and 180
- Use decimal format (e.g., 55.6761, not 55°40'34"N)
- Try using the "Use My Location" button instead

#### No results displayed after clicking "Find Meals"

**Solutions**:
1. Open browser console (F12) to check for JavaScript errors
2. Check terminal/console for Python errors
3. Verify both API keys are configured in `.env`
4. Restart the Flask server: `python app.py`
5. Clear browser cache and reload page

#### Geolocation not working

**Cause**: Browser doesn't have location permission

**Solutions**:
- Click the location icon in browser address bar
- Allow location access when prompted
- If blocked, go to browser settings and enable location for localhost
- Alternatively, manually enter coordinates

### API Status & Monitoring

**Check Salling Group API Status**:
- Visit: https://developer.sallinggroup.com/
- Check for service announcements
- Verify your API key is active in your account dashboard

**Check Gemini API Status**:
- Visit: https://status.cloud.google.com/
- Look for "Vertex AI" or "Generative AI" services

### Debug Mode

Enable detailed logging by modifying `app.py`:

```python
# Add at the top of app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show detailed API requests, responses, and processing steps in the terminal.

### Getting Help

If you encounter issues not covered here:

1. Check the terminal/console for error messages
2. Review the API documentation:
   - Salling Group: https://developer.sallinggroup.com/api-reference
   - Gemini: https://ai.google.dev/gemini-api/docs
3. Verify your `.env` file has both API keys configured
4. Try the demo scripts to test individual components:
   - `python demo.py` - Test basic workflow
   - `python demo_optimized_meals.py` - Test meal generation

## Testing

The project includes comprehensive tests:

```bash
# Run all tests
python -m pytest

# Test with real APIs (requires valid API keys)
python test_complete_workflow_real_apis.py

# Test individual components
python test_unit_core_components.py
python test_integration_mocked.py
```

## Project Structure

```
.
├── agents/
│   └── discount_optimizer/
│       ├── agent.py                    # Main ADK agent orchestration
│       ├── salling_api_client.py       # Salling Group API integration
│       ├── meal_suggester.py           # Gemini AI meal generation
│       ├── discount_matcher.py         # Distance filtering & sorting
│       ├── input_validator.py          # Input validation
│       ├── savings_calculator.py       # Savings calculations
│       ├── output_formatter.py         # Result formatting
│       └── models.py                   # Data models
├── templates/
│   └── index.html                      # Web UI template
├── static/
│   ├── css/styles.css                  # UI styling
│   └── js/app.js                       # Frontend logic
├── app.py                              # Flask web server
├── requirements.txt                    # Python dependencies
├── .env                                # API keys (not in git)
└── .env.example                        # Example configuration

```

## Development

### Type Checking

This project uses strict type checking with mypy for all refactored modules. The codebase follows a gradual typing strategy:

- **Refactored modules**: 100% type coverage with strict mode
- **Legacy modules**: Permissive mode during migration

**Run type checks:**
```bash
./scripts/type_check.sh
```

**Documentation:**
- [Type Checking Strategy](docs/TYPE_CHECKING_STRATEGY.md) - Gradual typing approach
- [Validation Report](docs/TYPE_CHECKING_VALIDATION_REPORT.md) - Current status
- [Quick Reference](docs/TYPE_CHECKING_QUICK_REFERENCE.md) - Common patterns

**Type Coverage Status:**
- ✅ Domain layer: 100%
- ✅ Infrastructure layer: 100%
- ✅ Agent layer: 100%
- ✅ Services layer: 100%
- ✅ Configuration: 100%

## Contributing

This project uses the ADK (Agent Development Kit) framework for agent orchestration. See `.kiro/specs/google-adk-modernization/` for detailed requirements, design, and implementation documentation.

All new code must pass strict type checking before merging. Run `./scripts/type_check.sh` to validate.

## License

This project is for educational and personal use. Ensure compliance with API terms of service:
- Salling Group API: https://developer.sallinggroup.com/terms
- Google Gemini API: https://ai.google.dev/gemini-api/terms

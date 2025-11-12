"""
Flask web application for Shopping Optimizer.
Serves the frontend and provides API endpoint for optimization.
"""

from flask import Flask, render_template, request, jsonify
from agents.discount_optimizer.agent import optimize_shopping
import os
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
load_dotenv()

# Validate required API credentials on startup
def validate_api_configuration():
    """
    Validate that all required API credentials are configured.
    Exits the application if critical credentials are missing.
    """
    required_vars = {
        'SALLING_GROUP_API_KEY': 'Salling Group API key',
        'GOOGLE_MAPS_API_KEY': 'Google Maps API key',
        'GEMINI_API_KEY': 'Gemini API key',
        'GMAIL_CREDENTIALS_PATH': 'Gmail credentials path'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value or value.startswith('your_'):
            missing_vars.append(f"  - {var} ({description})")
    
    if missing_vars:
        print("ERROR: Missing required API configuration!", file=sys.stderr)
        print("Please set the following environment variables in your .env file:", file=sys.stderr)
        print("\n".join(missing_vars), file=sys.stderr)
        print("\nRefer to .env.example for the required format.", file=sys.stderr)
        sys.exit(1)
    
    # Validate Gmail credentials file exists
    gmail_creds_path = os.getenv('GMAIL_CREDENTIALS_PATH')
    if not os.path.exists(gmail_creds_path):
        print(f"WARNING: Gmail credentials file not found at {gmail_creds_path}", file=sys.stderr)
        print("Email campaign parsing will not be available until credentials are configured.", file=sys.stderr)
    
    print("✓ API configuration validated successfully")

# Validate configuration on startup
validate_api_configuration()

app = Flask(__name__)


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/api/optimize', methods=['POST'])
def optimize():
    """
    API endpoint for shopping optimization.
    
    Expected JSON payload:
    {
        "location": "55.6761,12.5683" or "Copenhagen",
        "meals": ["taco", "pasta"],
        "preferences": {
            "maximize_savings": true,
            "minimize_stores": false,
            "prefer_organic": false
        }
    }
    
    Returns:
    {
        "success": true/false,
        "recommendation": {...},
        "error": "error message" (if failed)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Parse location
        location_str = data.get('location', '').strip()
        if not location_str:
            return jsonify({
                'success': False,
                'error': 'Location is required'
            }), 400
        
        # Try to parse as coordinates (lat,lon)
        try:
            parts = location_str.split(',')
            if len(parts) == 2:
                latitude = float(parts[0].strip())
                longitude = float(parts[1].strip())
            else:
                # Default to Copenhagen if not coordinates
                latitude = 55.6761
                longitude = 12.5683
        except ValueError:
            # Default to Copenhagen if parsing fails
            latitude = 55.6761
            longitude = 12.5683
        
        # Get meals
        meals = data.get('meals', [])
        if not meals:
            return jsonify({
                'success': False,
                'error': 'At least one meal is required'
            }), 400
        
        # Get preferences
        preferences = data.get('preferences', {})
        maximize_savings = preferences.get('maximize_savings', False)
        minimize_stores = preferences.get('minimize_stores', False)
        prefer_organic = preferences.get('prefer_organic', False)
        
        # Validate at least one preference is selected
        if not (maximize_savings or minimize_stores or prefer_organic):
            return jsonify({
                'success': False,
                'error': 'At least one optimization preference must be selected'
            }), 400
        
        # Call the optimization function
        result = optimize_shopping(
            latitude=latitude,
            longitude=longitude,
            meal_plan=meals,
            timeframe="this week",
            maximize_savings=maximize_savings,
            minimize_stores=minimize_stores,
            prefer_organic=prefer_organic
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=True)

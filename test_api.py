"""
Test script for the Flask API endpoint.
"""

import json

# Test the optimize_shopping function directly
from agents.discount_optimizer.agent import optimize_shopping

print("=== Testing API Integration ===\n")

# Simulate API request payload
test_payload = {
    "location": "55.6761,12.5683",
    "meals": ["taco", "pasta"],
    "preferences": {
        "maximize_savings": True,
        "minimize_stores": True,
        "prefer_organic": False
    }
}

print("Test payload:")
print(json.dumps(test_payload, indent=2))
print()

# Parse location
location_str = test_payload["location"]
parts = location_str.split(',')
latitude = float(parts[0].strip())
longitude = float(parts[1].strip())

# Call optimization
result = optimize_shopping(
    latitude=latitude,
    longitude=longitude,
    meal_plan=test_payload["meals"],
    timeframe="this week",
    maximize_savings=test_payload["preferences"]["maximize_savings"],
    minimize_stores=test_payload["preferences"]["minimize_stores"],
    prefer_organic=test_payload["preferences"]["prefer_organic"]
)

print("API Response:")
print(f"Success: {result['success']}")
if result['success']:
    print(f"Total savings: {result['total_savings']:.2f} kr")
    print(f"Time savings: {result['time_savings']:.2f} hours")
    print(f"Number of purchases: {result['num_purchases']}")
    print("\nRecommendation preview (first 500 chars):")
    print(result['recommendation'][:500] + "...")
else:
    print(f"Error: {result['error']}")

print("\n✓ API integration test complete!")

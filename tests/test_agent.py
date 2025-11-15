"""
Test script for the Shopping Optimizer Agent orchestration.
"""

from agents.discount_optimizer.agent import optimize_shopping

print("=== Shopping Optimizer Agent Test ===\n")

# Test with Copenhagen coordinates and a meal plan
result = optimize_shopping(
    latitude=55.6761,
    longitude=12.5683,
    meal_plan=["taco", "pasta"],
    timeframe="this week",
    maximize_savings=True,
    minimize_stores=True,
    prefer_organic=False
)

if result['success']:
    print("✓ Optimization successful!\n")
    print(result['recommendation'])
    print(f"\nTotal savings: {result['total_savings']:.2f} kr")
    print(f"Time savings: {result['time_savings']:.2f} hours")
    print(f"Number of purchases: {result['num_purchases']}")
else:
    print(f"✗ Optimization failed: {result['error']}")

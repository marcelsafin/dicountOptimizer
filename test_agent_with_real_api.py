"""
Test the complete agent workflow with real Salling API data.
"""

from agents.discount_optimizer.agent import optimize_shopping


def test_agent_with_real_api():
    """Test the complete optimization workflow with real API data."""
    
    print("=== Testing Agent with Real Salling API ===\n")
    
    # Test with Copenhagen coordinates and a meal plan
    print("Testing with meal plan: ['taco', 'pasta']\n")
    
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
        print("✅ Optimization successful!\n")
        print("=" * 60)
        print(result['recommendation'])
        print("=" * 60)
        print(f"\nTotal savings: {result['total_savings']:.2f} kr")
        print(f"Time savings: {result['time_savings']:.2f} hours")
        print(f"Number of purchases: {result['num_purchases']}")
        return True
    else:
        print(f"❌ Optimization failed: {result['error']}")
        return False


def test_agent_with_ai_suggestions():
    """Test the agent with AI meal suggestions."""
    
    print("\n\n=== Testing Agent with AI Meal Suggestions ===\n")
    
    # Test with empty meal plan to trigger AI suggestions
    print("Testing with empty meal plan (AI will suggest meals)\n")
    
    result = optimize_shopping(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=[],
        timeframe="this week",
        maximize_savings=True,
        minimize_stores=False,
        prefer_organic=True
    )
    
    if result['success']:
        print("✅ Optimization with AI suggestions successful!\n")
        print("=" * 60)
        print(result['recommendation'])
        print("=" * 60)
        print(f"\nTotal savings: {result['total_savings']:.2f} kr")
        print(f"Time savings: {result['time_savings']:.2f} hours")
        print(f"Number of purchases: {result['num_purchases']}")
        return True
    else:
        print(f"❌ Optimization failed: {result['error']}")
        return False


if __name__ == "__main__":
    success1 = test_agent_with_real_api()
    success2 = test_agent_with_ai_suggestions()
    
    if success1 and success2:
        print("\n\n✅ All agent tests passed!")
    else:
        print("\n\n⚠️  Some tests failed")

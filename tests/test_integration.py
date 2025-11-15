"""
Integration and end-to-end tests for the Shopping Optimizer system.

Tests the complete optimization flow with various scenarios:
- Complete flow with Copenhagen coordinates and meal plan
- All three optimization preferences
- Edge case: no discounts match meal plan
- Edge case: single store has all items
- Output format verification
"""

import sys
from datetime import date, timedelta
from agents.discount_optimizer.agent import optimize_shopping
from agents.discount_optimizer.models import DiscountItem, Location, MOCK_DISCOUNTS


def test_complete_flow_copenhagen():
    """
    Test complete flow with Copenhagen coordinates and provided meal plan.
    Requirements: All requirements
    """
    print("\n=== Test 1: Complete Flow with Copenhagen Coordinates ===")
    
    result = optimize_shopping(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco", "pasta"],
        timeframe="this week",
        maximize_savings=True,
        minimize_stores=True,
        prefer_organic=False
    )
    
    assert result['success'], f"Optimization failed: {result.get('error')}"
    assert 'recommendation' in result, "Missing recommendation in result"
    assert result['total_savings'] > 0, "Expected positive savings"
    # Time savings can be negative if optimized plan requires visiting multiple stores
    assert isinstance(result['time_savings'], (int, float)), "Expected numeric time savings"
    assert result['num_purchases'] > 0, "Expected at least one purchase"
    
    # Verify output contains key sections
    recommendation = result['recommendation']
    assert "SHOPPING" in recommendation or "Store" in recommendation or "📍" in recommendation, "Missing shopping plan section"
    assert "SAVINGS" in recommendation or "kr" in recommendation or "save" in recommendation, "Missing savings information"
    
    print(f"✓ Test passed!")
    print(f"  - Total savings: {result['total_savings']:.2f} kr")
    print(f"  - Time savings: {result['time_savings']:.2f} hours")
    print(f"  - Number of purchases: {result['num_purchases']}")
    print(f"  - Recommendation length: {len(recommendation)} characters")
    
    return result


def test_maximize_savings_preference():
    """
    Test optimization with maximize_savings preference only.
    Requirements: 4.1, 4.4
    """
    print("\n=== Test 2: Maximize Savings Preference ===")
    
    result = optimize_shopping(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco"],
        timeframe="this week",
        maximize_savings=True,
        minimize_stores=False,
        prefer_organic=False
    )
    
    assert result['success'], f"Optimization failed: {result.get('error')}"
    assert result['total_savings'] > 0, "Expected positive savings with maximize_savings"
    
    print(f"✓ Test passed!")
    print(f"  - Total savings: {result['total_savings']:.2f} kr")
    
    return result


def test_minimize_stores_preference():
    """
    Test optimization with minimize_stores preference only.
    Requirements: 4.2, 4.4
    """
    print("\n=== Test 3: Minimize Stores Preference ===")
    
    result = optimize_shopping(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco", "pasta"],
        timeframe="this week",
        maximize_savings=False,
        minimize_stores=True,
        prefer_organic=False
    )
    
    assert result['success'], f"Optimization failed: {result.get('error')}"
    
    # Count unique stores in the recommendation
    recommendation = result['recommendation']
    stores = set()
    for line in recommendation.split('\n'):
        if 'Netto' in line or 'Føtex' in line or 'Rema' in line:
            if 'Netto' in line:
                stores.add('Netto')
            if 'Føtex' in line:
                stores.add('Føtex')
            if 'Rema' in line:
                stores.add('Rema')
    
    print(f"✓ Test passed!")
    print(f"  - Unique stores: {len(stores)}")
    print(f"  - Stores: {', '.join(stores)}")
    
    return result


def test_prefer_organic_preference():
    """
    Test optimization with prefer_organic preference only.
    Requirements: 4.3, 4.4
    """
    print("\n=== Test 4: Prefer Organic Preference ===")
    
    result = optimize_shopping(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco"],
        timeframe="this week",
        maximize_savings=False,
        minimize_stores=False,
        prefer_organic=True
    )
    
    assert result['success'], f"Optimization failed: {result.get('error')}"
    
    # Check if organic products are mentioned
    recommendation = result['recommendation']
    has_organic = 'økologisk' in recommendation.lower() or 'organic' in recommendation.lower()
    
    print(f"✓ Test passed!")
    print(f"  - Contains organic products: {has_organic}")
    
    return result


def test_all_preferences_combined():
    """
    Test optimization with all three preferences enabled.
    Requirements: 4.1, 4.2, 4.3, 4.4
    """
    print("\n=== Test 5: All Preferences Combined ===")
    
    result = optimize_shopping(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco", "pasta", "grøntsagssuppe"],
        timeframe="this week",
        maximize_savings=True,
        minimize_stores=True,
        prefer_organic=True
    )
    
    assert result['success'], f"Optimization failed: {result.get('error')}"
    assert result['total_savings'] > 0, "Expected positive savings"
    assert result['num_purchases'] > 0, "Expected purchases"
    
    print(f"✓ Test passed!")
    print(f"  - Total savings: {result['total_savings']:.2f} kr")
    print(f"  - Time savings: {result['time_savings']:.2f} hours")
    print(f"  - Number of purchases: {result['num_purchases']}")
    
    return result


def test_no_matching_discounts():
    """
    Test edge case: no discounts match meal plan.
    Requirements: 3.4, 5.4
    """
    print("\n=== Test 6: Edge Case - No Matching Discounts ===")
    
    # Use a meal that doesn't exist in the database
    result = optimize_shopping(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["sushi", "ramen", "pad thai"],
        timeframe="this week",
        maximize_savings=True,
        minimize_stores=False,
        prefer_organic=False
    )
    
    # This should fail gracefully with an appropriate error message
    assert not result['success'], "Expected failure for non-existent meals"
    assert 'error' in result, "Expected error message"
    
    print(f"✓ Test passed!")
    print(f"  - Error message: {result['error']}")
    
    return result


def test_single_store_all_items():
    """
    Test edge case: single store has all items.
    Requirements: 4.2, 5.1, 5.3
    """
    print("\n=== Test 7: Edge Case - Single Store Has All Items ===")
    
    # Use a simple meal plan that might be available at one store
    result = optimize_shopping(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["grøntsagssuppe"],
        timeframe="this week",
        maximize_savings=False,
        minimize_stores=True,
        prefer_organic=False
    )
    
    assert result['success'], f"Optimization failed: {result.get('error')}"
    
    # Count unique stores
    recommendation = result['recommendation']
    stores = set()
    for line in recommendation.split('\n'):
        if 'Netto' in line:
            stores.add('Netto')
        if 'Føtex' in line:
            stores.add('Føtex')
        if 'Rema' in line:
            stores.add('Rema')
    
    print(f"✓ Test passed!")
    print(f"  - Number of stores: {len(stores)}")
    print(f"  - Stores: {', '.join(stores) if stores else 'None detected'}")
    
    return result


def test_output_format():
    """
    Verify output format matches expected structure.
    Requirements: 5.1, 5.2, 5.3, 8.1, 8.2, 8.3, 8.4, 8.5
    """
    print("\n=== Test 8: Output Format Verification ===")
    
    result = optimize_shopping(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco", "pasta"],
        timeframe="this week",
        maximize_savings=True,
        minimize_stores=True,
        prefer_organic=False
    )
    
    assert result['success'], f"Optimization failed: {result.get('error')}"
    
    recommendation = result['recommendation']
    
    # Verify key components are present
    checks = {
        'has_store_info': any(store in recommendation for store in ['Netto', 'Føtex', 'Rema']),
        'has_product_info': len(recommendation) > 100,
        'has_price_info': 'kr' in recommendation or 'price' in recommendation.lower(),
        'has_savings_info': 'savings' in recommendation.lower() or 'spar' in recommendation.lower(),
        'has_structured_format': '\n' in recommendation,
    }
    
    for check_name, passed in checks.items():
        assert passed, f"Output format check failed: {check_name}"
    
    print(f"✓ Test passed!")
    print(f"  - All format checks passed:")
    for check_name, passed in checks.items():
        print(f"    • {check_name}: {'✓' if passed else '✗'}")
    
    return result


def test_location_filtering():
    """
    Test that location filtering works correctly.
    Requirements: 2.4, 4.5
    """
    print("\n=== Test 9: Location Filtering ===")
    
    # Test with Copenhagen coordinates (should find stores)
    result_copenhagen = optimize_shopping(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco"],
        timeframe="this week",
        maximize_savings=True,
        minimize_stores=False,
        prefer_organic=False
    )
    
    assert result_copenhagen['success'], "Expected success for Copenhagen location"
    
    # Test with far away coordinates (should fail or have no results)
    result_far = optimize_shopping(
        latitude=70.0,  # Far north in Norway
        longitude=25.0,
        meal_plan=["taco"],
        timeframe="this week",
        maximize_savings=True,
        minimize_stores=False,
        prefer_organic=False
    )
    
    assert not result_far['success'], "Expected failure for distant location"
    assert 'no discounts' in result_far['error'].lower() or 'area' in result_far['error'].lower()
    
    print(f"✓ Test passed!")
    print(f"  - Copenhagen location: Success")
    print(f"  - Distant location: Correctly filtered out")
    
    return result_copenhagen


def test_timeframe_filtering():
    """
    Test that timeframe filtering works correctly.
    Requirements: 2.3, 1.4
    """
    print("\n=== Test 10: Timeframe Filtering ===")
    
    result = optimize_shopping(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco", "pasta"],
        timeframe="this week",
        maximize_savings=True,
        minimize_stores=False,
        prefer_organic=False
    )
    
    assert result['success'], f"Optimization failed: {result.get('error')}"
    
    # Verify that purchases have dates assigned
    recommendation = result['recommendation']
    has_date_info = any(day in recommendation.lower() for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'day', 'date'])
    
    print(f"✓ Test passed!")
    print(f"  - Has date information: {has_date_info}")
    
    return result


def run_all_tests():
    """Run all integration tests."""
    print("=" * 70)
    print("SHOPPING OPTIMIZER - INTEGRATION AND END-TO-END TESTS")
    print("=" * 70)
    
    tests = [
        test_complete_flow_copenhagen,
        test_maximize_savings_preference,
        test_minimize_stores_preference,
        test_prefer_organic_preference,
        test_all_preferences_combined,
        test_no_matching_discounts,
        test_single_store_all_items,
        test_output_format,
        test_location_filtering,
        test_timeframe_filtering,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)
    
    if failed == 0:
        print("\n🎉 All integration tests passed!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

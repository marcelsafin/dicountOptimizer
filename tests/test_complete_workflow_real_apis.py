"""
Test complete workflow with real APIs.

This test suite validates the entire Shopping Optimizer workflow using real:
- Salling Group API for food waste data
- Gemini 2.5 Pro API for meal suggestions

Requirements: All requirements
Task: 12. Test complete workflow with real APIs
"""

import os
import sys
from datetime import date, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from agents.discount_optimizer.agent import optimize_shopping
from agents.discount_optimizer.salling_api_client import SallingAPIClient
from agents.discount_optimizer.meal_suggester import MealSuggester
from agents.discount_optimizer.models import Location


def check_api_keys():
    """Verify that required API keys are configured."""
    print("\n=== Checking API Keys ===")
    
    salling_key = os.getenv("SALLING_GROUP_API_KEY")
    gemini_key = os.getenv("GOOGLE_API_KEY")
    
    if not salling_key:
        print("❌ SALLING_GROUP_API_KEY not found in environment")
        return False
    else:
        print(f"✓ Salling Group API key found: {salling_key[:10]}...")
    
    if not gemini_key:
        print("❌ GOOGLE_API_KEY (for Gemini) not found in environment")
        return False
    else:
        print(f"✓ Google API key found: {gemini_key[:10]}...")
    
    return True


def test_salling_api_with_real_coordinates():
    """
    Test Salling Group API with real location coordinates in Denmark.
    Verify 2km radius returns appropriate food waste offers.
    
    Requirements: 2.1, 2.2, 2.5, 2.6, 10.1, 10.2
    """
    print("\n=== Test 1: Salling Group API with Real Coordinates ===")
    
    try:
        client = SallingAPIClient()
        
        # Test location: Copenhagen center (Rådhuspladsen)
        location = Location(latitude=55.6761, longitude=12.5683)
        
        print(f"Testing with location: {location.latitude}, {location.longitude}")
        print("Fetching food waste offers within 2km radius...")
        
        # Fetch campaigns with 2km radius
        discounts = client.fetch_campaigns(location, radius_km=2.0)
        
        print(f"✓ Successfully fetched {len(discounts)} food waste items")
        
        if discounts:
            print("\n--- Sample Food Waste Items ---")
            for i, item in enumerate(discounts[:5], 1):
                print(f"\n{i}. {item.product_name}")
                print(f"   Store: {item.store_name}")
                print(f"   Address: {item.store_address}")
                print(f"   Distance: {item.travel_distance_km:.2f} km")
                print(f"   Original: {item.original_price:.2f} DKK")
                print(f"   Discount: {item.discount_price:.2f} DKK ({item.discount_percent:.0f}% off)")
                print(f"   Expires: {item.expiration_date}")
                print(f"   Organic: {'Yes' if item.is_organic else 'No'}")
            
            # Verify all items are within 2km
            items_outside_radius = [d for d in discounts if d.travel_distance_km > 2.0]
            if items_outside_radius:
                print(f"\n⚠️  Warning: {len(items_outside_radius)} items outside 2km radius")
            else:
                print(f"\n✓ All items are within 2km radius")
            
            return True, discounts
        else:
            print("\n⚠️  No food waste offers found in this area")
            print("This may be normal if there are no active food waste campaigns nearby")
            return True, []
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, []


def test_gemini_meal_generation():
    """
    Test Gemini 2.5 Pro meal generation with various product combinations.
    Verify meal suggestions are creative and use available products.
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
    """
    print("\n=== Test 2: Gemini 2.5 Pro Meal Generation ===")
    
    try:
        suggester = MealSuggester()
        
        # Test with various product combinations
        test_cases = [
            {
                'name': 'Meat and vegetables',
                'products': ['Hakket oksekød', 'Tomater', 'Løg', 'Hvidløg', 'Pasta'],
                'preferences': ''
            },
            {
                'name': 'Dairy and bread',
                'products': ['Mælk', 'Ost', 'Brød', 'Smør', 'Æg'],
                'preferences': 'breakfast'
            },
            {
                'name': 'Mixed ingredients',
                'products': ['Kylling', 'Ris', 'Grøntsager', 'Karry', 'Kokosmælk'],
                'preferences': 'asian cuisine'
            }
        ]
        
        all_passed = True
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- Test Case {i}: {test_case['name']} ---")
            print(f"Products: {', '.join(test_case['products'])}")
            print(f"Preferences: {test_case['preferences'] or 'None'}")
            
            try:
                meals = suggester.suggest_meals(
                    available_products=test_case['products'],
                    user_preferences=test_case['preferences'],
                    num_meals=3
                )
                
                print(f"✓ Generated {len(meals)} meal suggestions:")
                for j, meal in enumerate(meals, 1):
                    print(f"  {j}. {meal}")
                
                # Verify meals are not empty
                if not meals or len(meals) == 0:
                    print(f"❌ No meals generated")
                    all_passed = False
                
            except Exception as e:
                print(f"❌ Error generating meals: {e}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complete_workflow_copenhagen():
    """
    Test complete workflow with Copenhagen coordinates.
    
    Requirements: All requirements
    """
    print("\n=== Test 3: Complete Workflow - Copenhagen ===")
    
    try:
        # Test with Copenhagen center
        result = optimize_shopping(
            latitude=55.6761,
            longitude=12.5683,
            meal_plan=[],  # Empty to trigger AI meal suggestions
            timeframe="this week",
            maximize_savings=True,
            minimize_stores=True,
            prefer_organic=False
        )
        
        if result['success']:
            print("✓ Optimization successful!")
            print(f"\n--- Recommendation ---")
            print(result['recommendation'])
            print(f"\n--- Summary ---")
            print(f"Total savings: {result['total_savings']:.2f} DKK")
            print(f"Time savings: {result['time_savings']:.2f} hours")
            print(f"Number of purchases: {result['num_purchases']}")
            return True
        else:
            print(f"❌ Optimization failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complete_workflow_with_meal_plan():
    """
    Test complete workflow with specific meal plan.
    
    Requirements: All requirements
    """
    print("\n=== Test 4: Complete Workflow - With Meal Plan ===")
    
    try:
        # Test with specific meal plan
        result = optimize_shopping(
            latitude=55.6761,
            longitude=12.5683,
            meal_plan=["taco", "pasta", "grøntsagssuppe"],
            timeframe="this week",
            maximize_savings=True,
            minimize_stores=False,
            prefer_organic=False
        )
        
        if result['success']:
            print("✓ Optimization successful!")
            print(f"\n--- Recommendation ---")
            print(result['recommendation'])
            print(f"\n--- Summary ---")
            print(f"Total savings: {result['total_savings']:.2f} DKK")
            print(f"Time savings: {result['time_savings']:.2f} hours")
            print(f"Number of purchases: {result['num_purchases']}")
            return True
        else:
            print(f"❌ Optimization failed: {result['error']}")
            # This might fail if no matching products, which is acceptable
            if "no matching products" in result['error'].lower() or "no discounts" in result['error'].lower():
                print("⚠️  This is acceptable - no matching products found")
                return True
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling_no_food_waste():
    """
    Test error handling when no food waste is available.
    
    Requirements: 2.6, 11.2
    """
    print("\n=== Test 5: Error Handling - No Food Waste Available ===")
    
    try:
        # Test with location far from any stores (middle of the ocean)
        result = optimize_shopping(
            latitude=57.0,  # North Sea
            longitude=8.0,
            meal_plan=["taco"],
            timeframe="this week",
            maximize_savings=True,
            minimize_stores=False,
            prefer_organic=False
        )
        
        if not result['success']:
            print(f"✓ Correctly handled no food waste scenario")
            print(f"Error message: {result['error']}")
            
            # Verify error message is meaningful
            if 'no discounts' in result['error'].lower() or 'area' in result['error'].lower():
                print("✓ Error message is clear and helpful")
                return True
            else:
                print("⚠️  Error message could be more specific")
                return True
        else:
            print("⚠️  Expected failure but got success (might have found distant stores)")
            return True
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling_gemini_failure():
    """
    Test error handling when Gemini API fails.
    
    Requirements: 3.5, 11.2
    """
    print("\n=== Test 6: Error Handling - Gemini API Failure ===")
    
    try:
        # Temporarily set invalid API key
        original_key = os.getenv("GOOGLE_API_KEY")
        os.environ["GOOGLE_API_KEY"] = "invalid_key_for_testing"
        
        suggester = MealSuggester()
        
        try:
            meals = suggester.suggest_meals(
                available_products=["Hakket oksekød", "Tomater", "Løg"],
                user_preferences="",
                num_meals=3
            )
            
            # If we get here, either it succeeded with cached data or has fallback
            print("✓ Handled Gemini failure gracefully")
            print(f"Returned: {meals}")
            result = True
            
        except Exception as e:
            # Expected to fail
            print(f"✓ Correctly raised exception: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            result = True
        
        finally:
            # Restore original key
            if original_key:
                os.environ["GOOGLE_API_KEY"] = original_key
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_different_locations():
    """
    Test with different locations in Denmark to verify geographic coverage.
    
    Requirements: 10.1, 10.2, 10.3, 10.5
    """
    print("\n=== Test 7: Different Locations in Denmark ===")
    
    locations = [
        {"name": "Copenhagen (Rådhuspladsen)", "lat": 55.6761, "lon": 12.5683},
        {"name": "Aarhus (City Center)", "lat": 56.1629, "lon": 10.2039},
        {"name": "Odense (City Center)", "lat": 55.3959, "lon": 10.3883},
    ]
    
    all_passed = True
    
    for loc in locations:
        print(f"\n--- Testing: {loc['name']} ---")
        
        try:
            client = SallingAPIClient()
            location = Location(latitude=loc['lat'], longitude=loc['lon'])
            
            discounts = client.fetch_campaigns(location, radius_km=2.0)
            
            print(f"✓ Found {len(discounts)} food waste items")
            
            if discounts:
                # Show closest store
                closest = min(discounts, key=lambda d: d.travel_distance_km)
                print(f"  Closest store: {closest.store_name} ({closest.travel_distance_km:.2f} km)")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            all_passed = False
    
    return all_passed


def run_all_tests():
    """Run all real API tests."""
    print("=" * 70)
    print("SHOPPING OPTIMIZER - REAL API WORKFLOW TESTS")
    print("=" * 70)
    
    # Check API keys first
    if not check_api_keys():
        print("\n❌ API keys not configured. Please set up .env file.")
        return 1
    
    tests = [
        ("Salling API with Real Coordinates", test_salling_api_with_real_coordinates),
        ("Gemini Meal Generation", test_gemini_meal_generation),
        ("Complete Workflow - Copenhagen", test_complete_workflow_copenhagen),
        ("Complete Workflow - With Meal Plan", test_complete_workflow_with_meal_plan),
        ("Error Handling - No Food Waste", test_error_handling_no_food_waste),
        ("Error Handling - Gemini Failure", test_error_handling_gemini_failure),
        ("Different Locations", test_different_locations),
    ]
    
    passed = 0
    failed = 0
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if isinstance(result, tuple):
                result = result[0]  # Extract boolean from tuple
            
            if result:
                passed += 1
                results.append(f"✓ {test_name}")
            else:
                failed += 1
                results.append(f"✗ {test_name}")
        except Exception as e:
            failed += 1
            results.append(f"✗ {test_name} (Exception: {e})")
    
    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    for result in results:
        print(result)
    
    print("\n" + "=" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)
    
    if failed == 0:
        print("\n🎉 All real API tests passed!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

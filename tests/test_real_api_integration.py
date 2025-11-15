"""
Test script for real API integration with DiscountMatcher.
"""

import os
from agents.discount_optimizer.discount_matcher import DiscountMatcher
from agents.discount_optimizer.models import Location


def test_real_api_integration():
    """Test the DiscountMatcher with real Salling API."""
    
    # Check if API key is configured
    api_key = os.getenv("SALLING_GROUP_API_KEY")
    if not api_key:
        print("❌ SALLING_GROUP_API_KEY not found in environment")
        return False
    
    print("✓ API key found")
    
    try:
        # Initialize DiscountMatcher with real API
        matcher = DiscountMatcher(use_real_api=True)
        print("✓ DiscountMatcher initialized with real API")
        
        # Test location: Copenhagen center
        location = Location(latitude=55.6761, longitude=12.5683)
        
        # Load discounts from real API
        print("\nLoading discounts from Salling Group API...")
        discounts = matcher.load_discounts(location=location, radius_km=2.0)
        
        print(f"✓ Loaded {len(discounts)} discount items")
        
        # Display sample results
        if discounts:
            print("\n=== Sample Discount Items ===")
            for i, item in enumerate(discounts[:5], 1):
                print(f"\n{i}. {item.product_name}")
                print(f"   Store: {item.store_name}")
                print(f"   Original: {item.original_price} DKK")
                print(f"   Discount: {item.discount_price} DKK ({item.discount_percent}% off)")
                print(f"   Expires: {item.expiration_date}")
                print(f"   Organic: {item.is_organic}")
        else:
            print("\n⚠️  No discounts found in the area")
        
        # Test location filtering
        print("\n=== Testing Location Filtering ===")
        filtered = matcher.filter_by_location(discounts, location, max_distance_km=1.0)
        print(f"✓ Filtered to {len(filtered)} items within 1km")
        
        # Test timeframe filtering
        print("\n=== Testing Timeframe Filtering ===")
        from agents.discount_optimizer.models import Timeframe
        from datetime import date, timedelta
        
        timeframe = Timeframe(
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7)
        )
        
        timeframe_filtered = matcher.filter_by_timeframe(discounts, timeframe)
        print(f"✓ Filtered to {len(timeframe_filtered)} items valid within timeframe")
        
        # Test with mock data fallback
        print("\n=== Testing Mock Data Fallback ===")
        matcher_mock = DiscountMatcher(use_real_api=False)
        mock_discounts = matcher_mock.load_discounts()
        print(f"✓ Loaded {len(mock_discounts)} mock discount items")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=== Real API Integration Test ===\n")
    success = test_real_api_integration()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed")

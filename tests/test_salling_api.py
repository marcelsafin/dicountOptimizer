"""
Test script for Salling Group API client.
"""

import os
from agents.discount_optimizer.salling_api_client import SallingAPIClient
from agents.discount_optimizer.models import Location


def test_api_client():
    """Test the Salling API client with real API calls."""
    
    # Check if API key is configured
    api_key = os.getenv("SALLING_GROUP_API_KEY")
    if not api_key:
        print("❌ SALLING_GROUP_API_KEY not found in environment")
        return False
    
    print("✓ API key found")
    
    try:
        # Initialize client
        client = SallingAPIClient(api_key)
        print("✓ Client initialized")
        
        # Test location: Hardcoded location
        location = Location(latitude=55.68072912197687, longitude=12.570726039674597)
        
        # Fetch campaigns
        print("\nFetching campaigns from Salling Group API...")
        campaigns = client.fetch_campaigns(location, radius_km=2.0)
        
        print(f"✓ Fetched {len(campaigns)} discount items")
        
        # Display sample results
        if campaigns:
            print("\n=== Sample Discount Items ===")
            for i, item in enumerate(campaigns[:5], 1):
                print(f"\n{i}. {item.product_name}")
                print(f"   Store: {item.store_name}")
                print(f"   Original: {item.original_price} DKK")
                print(f"   Discount: {item.discount_price} DKK ({item.discount_percent}% off)")
                print(f"   Expires: {item.expiration_date}")
                print(f"   Organic: {item.is_organic}")
                print(f"   Location: ({item.store_location.latitude}, {item.store_location.longitude})")
        else:
            print("\n⚠️  No campaigns found in the area")
        
        # Test caching
        print("\n=== Testing Cache ===")
        cached_campaigns = client.get_cached_campaigns()
        if cached_campaigns:
            print(f"✓ Cache working: {len(cached_campaigns)} items cached")
        else:
            print("❌ Cache not working")
        
        # Test cache retrieval (should use cache, not make new API call)
        print("\nFetching campaigns again (should use cache)...")
        campaigns2 = client.fetch_campaigns(location, radius_km=2.0)
        print(f"✓ Retrieved {len(campaigns2)} items from cache")
        
        # Clear cache
        client.clear_cache()
        print("✓ Cache cleared")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=== Salling Group API Client Test ===\n")
    success = test_api_client()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed")

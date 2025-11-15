"""
Test script for GoogleMapsService with hardcoded coordinates.
"""

from agents.discount_optimizer.google_maps_service import GoogleMapsService
from agents.discount_optimizer.models import Location


def test_google_maps_service():
    """Test GoogleMapsService with hardcoded user location."""
    
    # Hardcoded user location (Malmö area)
    user_location = Location(
        latitude=55.680535554805324,
        longitude=12.570640208986235
    )
    
    print("=" * 60)
    print("Testing GoogleMapsService")
    print("=" * 60)
    print(f"\nUser Location: {user_location.latitude}, {user_location.longitude}")
    
    try:
        # Initialize service
        service = GoogleMapsService()
        print("\n✓ GoogleMapsService initialized successfully")
        
        # Test 1: Find nearby stores
        print("\n" + "-" * 60)
        print("Test 1: Finding nearby stores (20km radius)")
        print("-" * 60)
        
        stores = service.find_nearby_stores(user_location, radius_km=20.0)
        print(f"\nFound {len(stores)} stores:")
        
        for i, store in enumerate(stores[:5], 1):  # Show first 5 stores
            print(f"\n{i}. {store['name']}")
            print(f"   Address: {store['address']}")
            print(f"   Location: {store['location'].latitude}, {store['location'].longitude}")
        
        if len(stores) > 5:
            print(f"\n... and {len(stores) - 5} more stores")
        
        # Test 2: Calculate distance matrix
        if stores:
            print("\n" + "-" * 60)
            print("Test 2: Calculating distances to stores")
            print("-" * 60)
            
            # Get first 3 stores for distance calculation
            test_stores = stores[:3]
            store_locations = [store['location'] for store in test_stores]
            
            distances = service.calculate_distance_matrix(user_location, store_locations)
            
            print(f"\nDistances from user location:")
            for i, store in enumerate(test_stores):
                loc_key = f"{store['location'].latitude},{store['location'].longitude}"
                if loc_key in distances and distances[loc_key]['distance_km'] is not None:
                    dist_info = distances[loc_key]
                    print(f"\n{i+1}. {store['name']}")
                    print(f"   Distance: {dist_info['distance_km']:.2f} km")
                    print(f"   Travel time: {dist_info['duration_minutes']:.1f} minutes")
                else:
                    print(f"\n{i+1}. {store['name']}")
                    print(f"   Distance: Could not calculate")
        
        # Test 3: Geocode address (optional)
        print("\n" + "-" * 60)
        print("Test 3: Geocoding address")
        print("-" * 60)
        
        test_address = "Malmö, Sweden"
        print(f"\nGeocoding: {test_address}")
        
        geocoded_location = service.geocode_address(test_address)
        print(f"Result: {geocoded_location.latitude}, {geocoded_location.longitude}")
        
        # Test caching
        print("\nTesting cache (second call should be instant)...")
        geocoded_location_2 = service.geocode_address(test_address)
        print(f"Cached result: {geocoded_location_2.latitude}, {geocoded_location_2.longitude}")
        
        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        print("=" * 60)
        
    except ValueError as e:
        print(f"\n✗ Configuration Error: {e}")
        print("\nPlease ensure GOOGLE_MAPS_API_KEY is set in your .env file")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_google_maps_service()

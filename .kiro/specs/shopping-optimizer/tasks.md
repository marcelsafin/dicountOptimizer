# Implementation Plan

- [x] 1. Set up environment configuration and API credentials
  - Create .env.example file with all required API keys
  - Set up environment variable loading in app.py
  - Add API configuration validation on startup
  - _Requirements: 2.1, 9.2, 10.1_

- [x] 2. Create core data models
  - Create dataclasses for UserInput, Location, OptimizationPreferences, Timeframe
  - Create dataclasses for DiscountItem, Purchase, ShoppingRecommendation
  - Create meal-to-ingredients mapping database
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.2, 10.4_

- [x] 3. Implement InputValidator component
  - Write validation function for location coordinates
  - Write validation function for meal plan (now optional for AI suggestions)
  - Write timeframe parser to convert "this week" to date range
  - Write validation to ensure at least one preference is selected
  - _Requirements: 1.5, 9.1, 9.2_

- [x] 4. Implement DiscountMatcher component with mock data
  - Write filter_by_location function using Haversine distance calculation
  - Write filter_by_timeframe function to exclude expired discounts
  - Create mock discount data for testing
  - _Requirements: 2.3, 2.4, 2.5, 10.3_

- [x] 5. Implement IngredientMapper component
  - Write get_ingredients_for_meal function using meal database lookup
  - Write fuzzy_match function for ingredient-to-product matching
  - Write match_products_to_ingredients function to find all discount options per ingredient
  - Handle case when no matching products found for an ingredient
  - _Requirements: 2.2, 3.1, 3.2, 3.3, 3.4_

- [x] 6. Implement MultiCriteriaOptimizer component
  - Write calculate_score function with weighted scoring algorithm
  - Implement savings score calculation: (original_price - discount_price) / original_price
  - Implement distance score using Haversine distance
  - Implement organic preference scoring
  - Implement store consolidation bonus logic
  - Write optimize function to select best product-store combination for each ingredient
  - Assign optimal purchase days based on discount expiration and meal timing
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 10.4_

- [x] 7. Implement SavingsCalculator component
  - Write calculate_monetary_savings function summing all discount savings
  - Write calculate_time_savings with heuristic-based time estimation
  - Calculate baseline time (shopping at closest store) vs optimized plan time
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 10.4_

- [x] 8. Implement OutputFormatter component
  - Write group_by_store_and_day function to organize purchases
  - Write generate_tips function for time-sensitive discounts and organic recommendations
  - Limit tips to top 3 most impactful
  - Write generate_motivation function with conversational message
  - Write format_recommendation function to create human-readable output
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3, 8.4, 8.5, 10.5_

- [x] 9. Implement ADK agent orchestration
  - Create root_agent function integrating all components
  - Implement workflow: validate → match → map → optimize → calculate → format
  - Add comprehensive error handling for each stage
  - _Requirements: 1.5, 2.1, 3.1, 4.4, 5.4_

- [x] 10. Implement MealSuggester component with Gemini AI
  - Write suggest_meals function using Gemini API
  - Create prompt for meal suggestions based on available products
  - Implement fallback logic if Gemini API fails
  - Integrate into agent workflow for empty/vague meal plans
  - _Requirements: 1.2, 3.1_

- [x] 11. Create web UI with Flask
  - Create HTML template with location, meal plan, and preference inputs
  - Implement slider-based preference selection (0-5 scale)
  - Add geolocation button for automatic location detection
  - Create results display sections for shopping list, savings, and tips
  - Add loading spinner and error message displays
  - _Requirements: 9.1, 9.3, 9.4, 9.5, 9.6, 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 12. Implement frontend JavaScript logic
  - Add form validation for location and preferences
  - Implement geolocation API integration
  - Add API call to /api/optimize endpoint
  - Parse and display results with proper formatting
  - Maintain input values after displaying results
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 13. Implement GoogleMapsService component
  - Write geocode_address function using Google Maps Geocoding API
  - Write find_nearby_stores function using Google Places API with type "supermarket"
  - Write calculate_distance_matrix function using Google Distance Matrix API
  - Implement caching for geocoding results (24h TTL)
  - Add error handling for API failures and invalid addresses
  - _Requirements: 9.2, 10.1, 10.2, 10.3, 10.4_

- [-] 14. Implement real discount data API client
  - Research and select Danish discount API (eTilbudsavis, Salling Group, or alternative)
  - Write fetch_campaigns function to call discount API with location and radius parameters
  - Write parse_campaign_response function to convert JSON to DiscountItem objects
  - Implement caching with 24h TTL for campaign data
  - Add error handling for API rate limits and network failures
  - _Requirements: 2.1, 2.2, 2.3, 2.6_

- [ ] 15. Extend DiscountItem model for real API integration
  - Add store_address field to DiscountItem dataclass
  - Add travel_distance_km field to DiscountItem dataclass
  - Add travel_time_minutes field to DiscountItem dataclass
  - Update all components to use extended DiscountItem model
  - _Requirements: 10.4, 10.5_

- [ ] 16. Integrate GoogleMapsService into InputValidator
  - Update InputValidator to accept address strings instead of coordinates
  - Add geocode_address call to convert address to coordinates
  - Update validation error messages for address input
  - Add fallback to default location if geocoding fails
  - _Requirements: 9.1, 9.2_

- [ ] 17. Integrate GoogleMapsService into DiscountMatcher
  - Update filter_by_location to use Google Distance Matrix API instead of Haversine
  - Add actual travel time and distance to filtered discounts
  - Update distance calculations to use real road distances
  - _Requirements: 10.2, 10.3, 10.4_

- [ ] 18. Integrate real discount API into agent workflow
  - Replace MOCK_DISCOUNTS with real API calls in DiscountMatcher
  - Update load_discounts function to fetch from real API
  - Add error handling and fallback to cached data if API fails
  - Test with real discount data from Danish stores
  - _Requirements: 2.1, 2.2, 2.3, 2.6_

- [ ] 19. Update SavingsCalculator to use real travel data
  - Update calculate_time_savings to use travel_time_minutes from Google Maps
  - Remove heuristic-based time estimation
  - Calculate actual travel time from Distance Matrix API
  - _Requirements: 6.3, 6.4, 10.4_

- [ ] 20. Update OutputFormatter to include store addresses and distances
  - Add store address display in shopping list output
  - Add travel distance display for each store
  - Update format_recommendation to show location information
  - _Requirements: 10.5_

- [ ] 21. Update web UI to support address input
  - Update location input placeholder to show address example
  - Update location input label to indicate address or coordinates accepted
  - Update form validation messages for address input
  - Test address input with various formats
  - _Requirements: 9.1, 9.2_

- [ ] 22. Update frontend to display store addresses and distances
  - Update results display to show store addresses
  - Add distance information to each store in shopping list
  - Format location information clearly in UI
  - _Requirements: 10.5, 11.4_

- [ ]* 23. Write unit tests for core components
  - Test InputValidator with various input formats
  - Test DiscountMatcher filtering logic
  - Test IngredientMapper fuzzy matching
  - Test MultiCriteriaOptimizer scoring algorithm
  - Test SavingsCalculator calculations
  - Test OutputFormatter formatting logic
  - _Requirements: All requirements_

- [ ]* 24. Write integration tests for API components
  - Test GoogleMapsService with mocked API responses
  - Test discount API client with mocked responses
  - Test complete workflow with mocked external APIs
  - Test error handling and fallback scenarios
  - _Requirements: All requirements_

- [ ]* 25. Integration testing with real APIs
  - Test complete flow with real discount API
  - Test Google Maps integration with Copenhagen addresses
  - Test edge cases: API failures, no nearby stores, invalid addresses
  - Test with various meal plans and preferences
  - _Requirements: All requirements_

- [ ]* 26. Documentation and deployment preparation
  - Update README.md with API setup instructions
  - Document how to obtain each API key
  - Add troubleshooting guide for common API issues
  - Create user guide for the web interface
  - Document system architecture and component interactions
  - _Requirements: All requirements_

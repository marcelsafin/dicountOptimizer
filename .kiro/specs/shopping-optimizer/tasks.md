 # Implementation Plan

- [x] 1. Set up environment configuration and API credentials
  - Create .env.example file with Salling Group API key and Gemini API key
  - Set up environment variable loading in app.py
  - Add API configuration validation on startup
  - _Requirements: 2.1, 2.6_

- [x] 2. Create core data models
  - Create dataclasses for UserInput, Location
  - Create dataclasses for DiscountItem with store address and distance fields
  - Create dataclasses for MealSuggestion and ShoppingRecommendation
  - _Requirements: 1.1, 2.2, 4.2, 5.1_

- [x] 3. Implement InputValidator component
  - Write validation function for location coordinates (lat/lng)
  - Validate latitude (-90 to 90) and longitude (-180 to 180)
  - Set fixed 2km radius for all searches
  - _Requirements: 1.3, 9.1_

- [x] 4. Implement SallingAPIClient component
  - Write fetch_campaigns function to call Salling Group food-waste API endpoint
  - Implement 2km radius parameter in API call
  - Write parse_campaign_response function to convert JSON to DiscountItem objects
  - Extract product name, store name, coordinates, prices, discount %, expiration date
  - Implement in-memory caching with 24h TTL for campaign data
  - Add error handling for API rate limits (429) and network failures
  - _Requirements: 2.1, 2.2, 2.5, 2.6, 10.1_

- [x] 5. Implement DiscountMatcher component
  - Write filter_by_location function using Haversine distance calculation
  - Write calculate_distances function to populate travel_distance_km for each discount
  - Write sort_by_distance function to order stores by proximity
  - Filter to only include stores within 2km radius
  - _Requirements: 2.4, 10.2, 10.3, 10.5_

- [x] 6. Implement MealSuggester component with Gemini 2.5 Pro
  - Write build_gemini_prompt function to format product list for AI
  - Include product names, prices, discounts, stores, distances, and expiration dates in prompt
  - Request 3-5 creative meal suggestions that use available food waste products
  - Write call to Gemini 2.5 Pro API with structured prompt
  - Write parse_gemini_response function to extract meal suggestions from AI response
  - Map suggested meals back to specific DiscountItem objects
  - Implement fallback logic if Gemini API fails
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 7. Implement SavingsCalculator component
  - Write calculate_meal_savings function to sum savings for products in each meal
  - Write calculate_total_savings function to sum across all meal suggestions
  - Write generate_savings_summary with motivational message about food waste reduction
  - _Requirements: 6.1, 6.2, 6.4, 6.5_

- [x] 8. Implement OutputFormatter component
  - Write format_meal_suggestion function to display meal name, description, and products
  - Write format_recommendation function to structure complete output
  - Group products by store for each meal
  - Display store name, address, and distance for each product
  - Show expiration dates for time-sensitive items
  - Write generate_tips function for products expiring within 24 hours
  - Highlight products with highest discount percentages
  - Limit tips to top 3 most impactful
  - Write generate_motivation function with friendly, conversational language
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 9. Implement ADK agent orchestration
  - Create root_agent function integrating all components
  - Implement workflow: validate location → fetch food waste (2km) → generate meals with Gemini → calculate savings → format output
  - Add comprehensive error handling for each stage
  - Handle Salling API failures gracefully
  - Handle Gemini API failures with fallback message
  - _Requirements: 1.3, 2.1, 3.1, 4.1, 11.2_

- [x] 10. Create web UI with Flask
  - Create HTML template with latitude and longitude input fields
  - Add geolocation button for automatic location detection
  - Display fixed 2km search radius to user
  - Create "Find Meals" button to trigger the workflow
  - Remove meal plan input (not needed - AI generates meals)
  - Add loading spinner for processing feedback
  - Create results display sections for meal suggestions, shopping list, savings, and tips
  - Add error message displays
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 11.1, 11.3, 11.4_

- [x] 11. Implement frontend JavaScript logic
  - Add form validation for location coordinates
  - Implement geolocation API integration for automatic position detection
  - Add API call to /api/optimize endpoint
  - Parse and display meal suggestions with proper formatting
  - Display shopping list organized by store
  - Show savings summary with total DKK savings
  - Display tips section
  - Maintain location values after displaying results
  - _Requirements: 11.1, 11.3, 11.4, 11.5_

- [x] 12. Test complete workflow with real APIs
  - Test Salling Group API with real location coordinates in Denmark
  - Verify 2km radius returns appropriate food waste offers
  - Test Gemini 2.5 Pro meal generation with various product combinations
  - Verify meal suggestions are creative and use available products
  - Test error handling when no food waste is available
  - Test error handling when Gemini API fails
  - _Requirements: All requirements_

- [x] 13. Optimize Gemini prompt for better meal suggestions
  - Refine prompt to encourage diverse meal types (breakfast, lunch, dinner, snacks)
  - Add instructions for considering dietary restrictions
  - Test prompt variations to improve meal creativity
  - Ensure meals prioritize products expiring soonest
  - _Requirements: 3.1, 3.2, 7.3_

- [x] 14. Add UI enhancements
  - Display map showing nearby stores with food waste offers
  - Add filters for meal types (breakfast, lunch, dinner)
  - Add ability to exclude certain ingredients or allergens
  - Show product images if available from Salling API
  - _Requirements: 8.5, 11.4_

- [x] 15. Write unit tests for core components
  - Test InputValidator with various coordinate formats
  - Test SallingAPIClient with mocked API responses
  - Test DiscountMatcher Haversine distance calculations
  - Test MealSuggester prompt building and response parsing
  - Test SavingsCalculator calculations
  - Test OutputFormatter formatting logic
  - _Requirements: All requirements_

- [x] 16. Write integration tests
  - Test complete workflow with mocked Salling and Gemini APIs
  - Test error handling scenarios (API failures, no products, invalid location)
  - Test caching behavior
  - Test edge cases (products expiring today, very high discounts)
  - _Requirements: All requirements_

- [x] 17. Documentation and deployment
  - Update README.md with setup instructions for Salling Group API key
  - Document how to obtain Gemini 2.5 Pro API access
  - Add user guide explaining the 2km radius and food waste focus
  - Document system architecture and workflow
  - Add troubleshooting guide for common API issues
  - _Requirements: All requirements_

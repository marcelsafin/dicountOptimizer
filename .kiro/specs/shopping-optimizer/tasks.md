e# Implementation Plan

- [x] 1. Set up data models and core data structures
  - Create dataclasses for UserInput, Location, OptimizationPreferences, Timeframe
  - Create dataclasses for DiscountItem, ShoppingRecommendation, Purchase
  - Create mock discount data with Danish stores (Netto, Føtex, Rema 1000) near Copenhagen coordinates
  - Create meal-to-ingredients mapping database
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1_

- [x] 2. Implement InputValidator component
  - Write validation function for location coordinates (latitude -90 to 90, longitude -180 to 180)
  - Write validation function for meal plan (non-empty list)
  - Write timeframe parser to convert "this week" to date range
  - Write validation to ensure at least one preference is selected
  - _Requirements: 1.5_

- [x] 3. Implement DiscountMatcher component
  - Write Haversine formula function for distance calculation between two coordinates
  - Write filter_by_location function to filter discounts within max_distance_km radius
  - Write filter_by_timeframe function to exclude expired discounts
  - Write load_discounts function to return mock discount data
  - _Requirements: 2.1, 2.3, 2.4_

- [x] 4. Implement IngredientMapper component
  - Write get_ingredients_for_meal function using meal database lookup
  - Write fuzzy_match function for ingredient-to-product matching
  - Write match_products_to_ingredients function to find all discount options per ingredient
  - Handle case when no matching products found for an ingredient
  - _Requirements: 2.2, 3.1, 3.2, 3.3, 3.4_

- [x] 5. Implement MultiCriteriaOptimizer component
  - Write calculate_score function with weighted scoring algorithm
  - Implement savings score calculation: (original_price - discount_price) / original_price
  - Implement distance score calculation: 1 / (1 + distance_km)
  - Implement organic preference scoring
  - Implement store consolidation bonus logic
  - Write optimize function to select best product-store combination for each ingredient
  - Assign optimal purchase days based on discount expiration and meal timing
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 6. Implement SavingsCalculator component
  - Write calculate_monetary_savings function summing all discount savings
  - Write calculate_time_savings function using heuristic (30 min/store + 5 min/km travel)
  - Calculate baseline time (shopping at closest store) vs optimized plan time
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 7. Implement OutputFormatter component
  - Write group_by_store_and_day function to organize purchases
  - Write generate_tips function for time-sensitive discounts and organic recommendations
  - Limit tips to top 3 most impactful
  - Write generate_motivation function with conversational message
  - Write format_recommendation function to create human-readable output
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 8. Create ADK agent orchestration
  - Define root_agent function for Google ADK
  - Wire together all components in optimization pipeline
  - Implement main optimization workflow: validate → match → map → optimize → format
  - Add error handling for each pipeline stage
  - _Requirements: 1.5, 2.1, 3.1, 4.4, 5.4_

- [x] 9. Build web UI with HTML/CSS/JavaScript
  - Create index.html with input form matching UI sketch
  - Add location text input field
  - Add meal plan textarea
  - Add three checkboxes for Cost, Time, Quality preferences
  - Add Optimize button
  - Create results display section with placeholders for shopping list, savings, and tips
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 10. Implement frontend interaction logic
  - Write JavaScript to capture form inputs on Optimize button click
  - Implement client-side validation with error messages for empty fields
  - Add loading spinner during optimization processing
  - Write function to call ADK agent with user inputs
  - Write function to display formatted results in results section
  - Maintain input values after displaying results
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 11. Add CSS styling for UI
  - Style input form with clean, modern design
  - Style checkboxes and buttons
  - Style results display with distinct sections
  - Add responsive design for mobile devices
  - Add visual feedback states (hover, active, disabled)
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 12. Integration and end-to-end testing
  - Test complete flow with Copenhagen coordinates and provided meal plan
  - Verify all three optimization preferences work correctly
  - Test edge case: no discounts match meal plan
  - Test edge case: single store has all items
  - Verify output format matches example format
  - _Requirements: All requirements_

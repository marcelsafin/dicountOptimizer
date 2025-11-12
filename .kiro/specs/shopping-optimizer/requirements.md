# Requirements Document

## Introduction

The Shopping Optimizer is an intelligent agent system that fetches food waste discounts from Salling Group API within 2km of the user's location, then uses Gemini 2.5 Pro to generate meal suggestions based on available discounted products. The system optimizes for savings by suggesting meals that can be prepared using food waste items, reducing both cost and food waste while providing creative meal ideas.

## Glossary

- **Shopping Optimizer**: The intelligent agent system that processes user inputs and generates optimized shopping recommendations
- **Salling Group API**: Official API providing real-time food waste and discount data from major Danish grocery chains (Netto, Føtex, Bilka, BR)
- **Discount Data**: Real-time product prices, discount information, expiration dates, and store locations from Salling Group API
- **Meal Plan**: A list of meals the user intends to prepare during a specified timeframe (can be optional if using AI meal suggestions)
- **User Preferences**: Configurable settings including optimization goals (maximize savings, minimize stores, prefer organic) and location
- **Shopping Recommendation**: The output containing optimized product-store-day combinations with calculated savings
- **Timeframe**: The period during which the user plans to shop (e.g., "this week")
- **Store**: A grocery retail location where products can be purchased
- **Haversine Distance**: Mathematical formula used to calculate distances between geographic coordinates

## Requirements

### Requirement 1

**User Story:** As a user, I want to input my location, so that the system can find nearby food waste discounts and suggest meals

#### Acceptance Criteria

1. WHEN the user provides location coordinates (latitude and longitude), THE Shopping Optimizer SHALL accept and store the location data
2. THE Shopping Optimizer SHALL provide a geolocation button to automatically detect the user's current position
3. THE Shopping Optimizer SHALL validate that location coordinates are provided before processing
4. THE Shopping Optimizer SHALL use a fixed 2km search radius for finding nearby food waste offers
5. THE Shopping Optimizer SHALL NOT require meal plan input from the user (meals are AI-generated)

### Requirement 2

**User Story:** As a user, I want the system to fetch real-time food waste data from Salling Group API within 2km of my location, so that I can find nearby discounted products

#### Acceptance Criteria

1. THE Shopping Optimizer SHALL connect to the Salling Group API food-waste endpoint with the user's coordinates and 2km radius
2. WHEN fetching discount data, THE Shopping Optimizer SHALL parse JSON responses containing product information including original price, discount price, product name, expiration date, store name, and store coordinates
3. THE Shopping Optimizer SHALL extract all available food waste products from stores within the 2km radius
4. THE Shopping Optimizer SHALL organize discount data by store location and product type
5. THE Shopping Optimizer SHALL cache API responses to minimize redundant requests within a 24-hour period
6. THE Shopping Optimizer SHALL handle API errors gracefully and provide meaningful error messages

### Requirement 3

**User Story:** As a user, I want the system to use Gemini 2.5 Pro to generate meal suggestions based on available food waste products, so that I can get creative meal ideas using discounted items

#### Acceptance Criteria

1. THE Shopping Optimizer SHALL send the list of available food waste products to Gemini 2.5 Pro API
2. THE Shopping Optimizer SHALL request Gemini to generate 3-5 meal suggestions that can be prepared using the available products
3. THE Shopping Optimizer SHALL include product names, prices, and store information in the Gemini prompt
4. WHEN Gemini generates meal suggestions, THE Shopping Optimizer SHALL parse and extract meal names, required ingredients, and preparation tips
5. THE Shopping Optimizer SHALL handle cases where Gemini API is unavailable by providing a fallback message

### Requirement 4

**User Story:** As a user, I want the system to present meal suggestions with associated food waste products, so that I can see which discounted items to buy for each meal

#### Acceptance Criteria

1. THE Shopping Optimizer SHALL map each AI-generated meal to the specific food waste products needed
2. THE Shopping Optimizer SHALL display the original price and discounted price for each product
3. THE Shopping Optimizer SHALL calculate total savings for each meal suggestion
4. THE Shopping Optimizer SHALL show which store(s) to visit for each meal's ingredients
5. THE Shopping Optimizer SHALL prioritize meals that maximize food waste utilization and savings

### Requirement 5

**User Story:** As a user, I want to receive clear meal suggestions with shopping details, so that I can easily understand what to buy and where

#### Acceptance Criteria

1. THE Shopping Optimizer SHALL format output with meal suggestions as the primary structure
2. THE Shopping Optimizer SHALL list required food waste products under each meal suggestion
3. THE Shopping Optimizer SHALL include store name, address, and distance for each product
4. THE Shopping Optimizer SHALL show expiration dates for time-sensitive food waste items
5. THE Shopping Optimizer SHALL group products by store when multiple items are from the same location

### Requirement 6

**User Story:** As a user, I want to see calculated savings and environmental impact, so that I can understand the value of using food waste products

#### Acceptance Criteria

1. THE Shopping Optimizer SHALL calculate total monetary savings by comparing discounted prices to original prices
2. THE Shopping Optimizer SHALL display the total monetary savings in Danish Kroner (DKK)
3. THE Shopping Optimizer SHALL show the percentage discount for each product
4. THE Shopping Optimizer SHALL calculate total savings across all suggested meals
5. THE Shopping Optimizer SHALL include a motivational message about reducing food waste

### Requirement 7

**User Story:** As a user, I want to receive actionable tips about food waste products, so that I can make informed purchasing decisions

#### Acceptance Criteria

1. THE Shopping Optimizer SHALL highlight products with expiration dates within 24 hours
2. THE Shopping Optimizer SHALL identify products with the highest discount percentages
3. THE Shopping Optimizer SHALL suggest which meals to prioritize based on product availability
4. THE Shopping Optimizer SHALL provide tips on storing and using food waste products quickly
5. THE Shopping Optimizer SHALL limit tips to the top 3 most important recommendations

### Requirement 8

**User Story:** As a user, I want the output formatted clearly with meal suggestions, product details, and savings, so that I can quickly understand and act on the recommendations

#### Acceptance Criteria

1. THE Shopping Optimizer SHALL format the output with distinct sections for meal suggestions, shopping list, savings summary, and tips
2. THE Shopping Optimizer SHALL present meal suggestions with AI-generated descriptions and ingredient lists
3. THE Shopping Optimizer SHALL present the shopping list organized by store location
4. THE Shopping Optimizer SHALL present the savings summary with total monetary savings clearly labeled
5. THE Shopping Optimizer SHALL use natural, conversational language in the output to enhance readability

### Requirement 9

**User Story:** As a user, I want a simple web interface to input my location, so that I can easily get meal suggestions based on nearby food waste

#### Acceptance Criteria

1. THE Shopping Optimizer SHALL provide input fields for latitude and longitude coordinates
2. THE Shopping Optimizer SHALL provide a geolocation button to automatically detect the user's current location
3. THE Shopping Optimizer SHALL display the fixed 2km search radius to the user
4. THE Shopping Optimizer SHALL provide a "Find Meals" button to trigger the food waste search and meal generation
5. THE Shopping Optimizer SHALL NOT require meal plan input from the user

### Requirement 10

**User Story:** As a user, I want the system to find food waste offers within 2km of my location, so that recommendations include only nearby stores

#### Acceptance Criteria

1. THE Shopping Optimizer SHALL use Salling Group API food-waste endpoint with 2km radius parameter
2. THE Shopping Optimizer SHALL use Haversine distance formula to calculate exact distances from user location to each store
3. THE Shopping Optimizer SHALL use a fixed 2km search radius (not configurable by user)
4. THE Shopping Optimizer SHALL display store addresses and distances in the meal suggestions
5. THE Shopping Optimizer SHALL sort stores by distance from the user's location

### Requirement 11

**User Story:** As a user, I want the interface to be intuitive and responsive, so that I can quickly get my meal suggestions

#### Acceptance Criteria

1. WHEN the user clicks the Find Meals button, THE Shopping Optimizer SHALL validate that location coordinates are provided
2. WHEN location is missing, THE Shopping Optimizer SHALL display a clear error message
3. WHEN the system is processing, THE Shopping Optimizer SHALL provide visual feedback (loading spinner)
4. WHEN processing completes, THE Shopping Optimizer SHALL display meal suggestions and shopping details in a clear, readable format
5. THE Shopping Optimizer SHALL maintain the user's location after displaying results to allow easy re-searching

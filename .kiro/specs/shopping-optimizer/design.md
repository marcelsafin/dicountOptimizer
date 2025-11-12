# Design Document

## Overview

The Shopping Optimizer is a web-based intelligent agent system built using Google ADK (Agent Development Kit) that processes user inputs (location, meal plans, preferences) and generates optimized shopping recommendations by analyzing mock discount data. The system uses a multi-stage pipeline: input validation → discount matching → ingredient identification → optimization → output formatting.

The architecture follows a modular design with clear separation between data models, business logic, optimization algorithms, and presentation layers.

## Architecture

### High-Level Architecture

```mermaid
graph TB
    UI[Web UI] --> Agent[ADK Agent]
    Agent --> InputValidator[Input Validator]
    InputValidator --> DiscountMatcher[Discount Matcher]
    DiscountMatcher --> IngredientMapper[Ingredient Mapper]
    IngredientMapper --> Optimizer[Multi-Criteria Optimizer]
    Optimizer --> OutputFormatter[Output Formatter]
    OutputFormatter --> UI
    
    DiscountData[(Mock Discount Data)] --> DiscountMatcher
    MealDatabase[(Meal-Ingredient DB)] --> IngredientMapper
```

### Component Layers

1. **Presentation Layer**: Web UI built with ADK's web interface
2. **Agent Layer**: Google ADK agent orchestrating the optimization workflow
3. **Business Logic Layer**: Core optimization algorithms and matching logic
4. **Data Layer**: Mock discount data and meal-ingredient mappings

## Components and Interfaces

### 1. Data Models

#### UserInput
```python
@dataclass
class UserInput:
    location: Location
    meal_plan: List[str]
    preferences: OptimizationPreferences
    timeframe: Timeframe
```

#### Location and Preferences
```python
@dataclass
class Location:
    latitude: float
    longitude: float
    
@dataclass
class OptimizationPreferences:
    maximize_savings: bool
    minimize_stores: bool
    prefer_organic: bool
    
@dataclass
class Timeframe:
    start_date: date
    end_date: date
```

#### DiscountItem
```python
@dataclass
class DiscountItem:
    product_name: str
    store_name: str
    store_location: Location
    original_price: float
    discount_price: float
    discount_percent: float
    expiration_date: date
    is_organic: bool
```

#### ShoppingRecommendation
```python
@dataclass
class ShoppingRecommendation:
    purchases: List[Purchase]
    total_savings: float
    time_savings: float
    tips: List[str]
    motivation_message: str
    
@dataclass
class Purchase:
    product_name: str
    store_name: str
    purchase_day: date
    price: float
    savings: float
    meal_association: str
```

### 2. Core Components

#### InputValidator
**Responsibility**: Validate and sanitize user inputs

**Interface**:
```python
class InputValidator:
    def validate(self, raw_input: Dict) -> UserInput
    def validate_location(self, lat: float, lon: float) -> bool
    def validate_meal_plan(self, meals: List[str]) -> bool
    def validate_timeframe(self, timeframe: str) -> Timeframe
```

**Key Logic**:
- Validate latitude (-90 to 90) and longitude (-180 to 180)
- Ensure meal plan is non-empty
- Parse timeframe strings ("this week", "next 7 days") into date ranges
- Ensure at least one optimization preference is selected

#### DiscountMatcher
**Responsibility**: Load and filter discount data based on location and timeframe

**Interface**:
```python
class DiscountMatcher:
    def load_discounts(self) -> List[DiscountItem]
    def filter_by_location(self, discounts: List[DiscountItem], 
                          user_location: Location, 
                          max_distance_km: float) -> List[DiscountItem]
    def filter_by_timeframe(self, discounts: List[DiscountItem], 
                           timeframe: Timeframe) -> List[DiscountItem]
    def calculate_distance(self, loc1: Location, loc2: Location) -> float
```

**Key Logic**:
- Use Haversine formula for distance calculation
- Filter discounts where expiration_date >= timeframe.start_date
- Return discounts within reasonable driving distance (e.g., 20km radius)

#### IngredientMapper
**Responsibility**: Map meals to required ingredients and match with available products

**Interface**:
```python
class IngredientMapper:
    def get_ingredients_for_meal(self, meal_name: str) -> List[str]
    def match_products_to_ingredients(self, 
                                     ingredients: List[str], 
                                     discounts: List[DiscountItem]) -> Dict[str, List[DiscountItem]]
    def fuzzy_match(self, ingredient: str, product_name: str) -> float
```

**Key Logic**:
- Maintain a meal-to-ingredients database
- Use fuzzy string matching to match ingredients to product names
- Handle synonyms (e.g., "ground beef" matches "köttfärs")
- Return multiple discount options per ingredient

**Meal Database Example**:
```python
MEAL_INGREDIENTS = {
    "taco": ["tortillas", "ground beef", "cheese", "sour cream", "salsa", "lettuce", "tomato"],
    "pasta": ["pasta", "tomato sauce", "ground beef", "parmesan", "garlic", "onion"],
    "veggie soup": ["vegetable broth", "carrots", "celery", "onion", "potato", "beans"]
}
```

#### MultiCriteriaOptimizer
**Responsibility**: Optimize product-store combinations based on user preferences

**Interface**:
```python
class MultiCriteriaOptimizer:
    def optimize(self, 
                matches: Dict[str, List[DiscountItem]], 
                preferences: OptimizationPreferences,
                user_location: Location) -> List[Purchase]
    def calculate_score(self, 
                       purchase_option: DiscountItem, 
                       preferences: OptimizationPreferences,
                       user_location: Location) -> float
```

**Key Logic**:
- **Scoring Algorithm**: Weighted sum of normalized criteria
  - Savings score: (original_price - discount_price) / original_price
  - Distance score: 1 / (1 + distance_km)
  - Organic score: 1.0 if organic and preferred, else 0.5
  - Store consolidation bonus: +0.2 for each additional item from same store

- **Weights** (when multiple preferences selected):
  - maximize_savings: 0.5
  - minimize_stores: 0.3
  - prefer_organic: 0.2

#### OutputFormatter
**Responsibility**: Format recommendations into human-readable output

**Interface**:
```python
class OutputFormatter:
    def format_recommendation(self, recommendation: ShoppingRecommendation) -> str
    def generate_tips(self, purchases: List[Purchase]) -> List[str]
    def generate_motivation(self, savings: float, time_savings: float) -> str
```

**Key Logic**:
- Group purchases by store, then by day
- Generate tips for time-sensitive discounts and organic alternatives
- Limit to top 3 most impactful tips
- Use conversational language for readability

### 3. Web UI Components

#### Frontend Structure
```
templates/
  index.html          # Main UI page
static/
  css/
    styles.css        # UI styling
  js/
    app.js           # Client-side logic
```

#### UI Component Breakdown

**Input Form**:
- Location input: Text field for coordinates or city name
- Meal plan input: Textarea for meal list
- Optimization checkboxes: Cost, Time, Quality
- Optimize button: Primary action button

**Results Display**:
- Shopping list section: Grouped by store and day
- Savings summary: Highlighted box with monetary and time savings
- Tips section: Bulleted list of actionable tips
- Motivation message: Friendly closing statement

## Error Handling

### Validation Errors
- **Missing required fields**: Clear message indicating which fields are required
- **Invalid location**: "Please provide valid coordinates"
- **Empty meal plan**: "Please enter at least one meal"
- **No preferences selected**: "Please select at least one optimization preference"

### Processing Errors
- **No discounts found**: "No discounts available in your area"
- **No matching products**: "We couldn't find discounts matching your meal plan"
- **Optimization failure**: Fallback to simple savings-based ranking

## Testing Strategy

### Unit Tests
1. InputValidator: Test validation logic for all input fields
2. DiscountMatcher: Test distance calculation and filtering
3. IngredientMapper: Test meal-to-ingredient mapping and fuzzy matching
4. MultiCriteriaOptimizer: Test scoring algorithm with different preferences
5. OutputFormatter: Test output formatting and tip generation

### Integration Tests
1. End-to-end optimization flow with complete user request
2. Multi-preference optimization scenarios
3. Edge cases with limited discount data

## Design Decisions

### 1. Google ADK Framework
**Rationale**: Built-in web UI support, agent orchestration, easy integration with Google AI models

### 2. Mock Data Approach
**Rationale**: Faster development, no external dependencies, easy testing

### 3. Multi-Criteria Scoring
**Rationale**: Flexible optimization, handles conflicting preferences gracefully

### 4. Fuzzy Ingredient Matching
**Rationale**: Handles variations in product naming, supports multiple languages

### 5. Store Consolidation
**Rationale**: Balances best deals with shopping convenience

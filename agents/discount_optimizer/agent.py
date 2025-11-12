"""
Discount Optimizer Agent - Orchestrates the shopping optimization pipeline.

This module defines the root ADK agent that wires together all components:
- InputValidator: Validates user inputs
- DiscountMatcher: Filters discounts by location and timeframe
- IngredientMapper: Maps meals to ingredients and matches with products
- MultiCriteriaOptimizer: Optimizes product-store combinations
- SavingsCalculator: Calculates monetary and time savings
- OutputFormatter: Formats the final recommendation
"""

from typing import Dict, Any
import os
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent

from .input_validator import InputValidator, ValidationError
from .discount_matcher import DiscountMatcher
from .ingredient_mapper import IngredientMapper
from .multi_criteria_optimizer import MultiCriteriaOptimizer
from .savings_calculator import SavingsCalculator
from .output_formatter import OutputFormatter
from .meal_suggester import MealSuggester

# Load environment variables
load_dotenv()


def optimize_shopping(
    latitude: float,
    longitude: float,
    meal_plan: list[str],
    timeframe: str = "this week",
    maximize_savings: bool = True,
    minimize_stores: bool = False,
    prefer_organic: bool = False
) -> Dict[str, Any]:
    """
    Main optimization workflow that orchestrates all components.
    
    Pipeline: validate → match → map → optimize → calculate → format
    
    Args:
        latitude: User's latitude coordinate (-90 to 90)
        longitude: User's longitude coordinate (-180 to 180)
        meal_plan: List of meal names (e.g., ["taco", "pasta", "grøntsagssuppe"])
        timeframe: Shopping timeframe (e.g., "this week", "next 7 days")
        maximize_savings: Whether to maximize monetary savings
        minimize_stores: Whether to minimize number of stores
        prefer_organic: Whether to prefer organic products
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating if optimization succeeded
        - recommendation: Formatted shopping recommendation (if successful)
        - error: Error message (if failed)
        
    Requirements: 1.5, 2.1, 3.1, 4.4, 5.4
    """
    try:
        # Stage 1: Input Validation
        validator = InputValidator()
        
        raw_input = {
            'location': {
                'latitude': latitude,
                'longitude': longitude
            },
            'meal_plan': meal_plan,
            'timeframe': timeframe,
            'preferences': {
                'maximize_savings': maximize_savings,
                'minimize_stores': minimize_stores,
                'prefer_organic': prefer_organic
            }
        }
        
        user_input = validator.validate(raw_input)
        
    except ValidationError as e:
        return {
            'success': False,
            'error': f"Validation error: {str(e)}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Unexpected validation error: {str(e)}"
        }
    
    try:
        # Stage 2: Discount Matching
        matcher = DiscountMatcher()
        
        # Load all available discounts
        all_discounts = matcher.load_discounts()
        
        # Filter by location (within 20km radius)
        location_filtered = matcher.filter_by_location(
            all_discounts,
            user_input.location,
            max_distance_km=20.0
        )
        
        # Filter by timeframe (exclude expired discounts)
        valid_discounts = matcher.filter_by_timeframe(
            location_filtered,
            user_input.timeframe
        )
        
        if not valid_discounts:
            return {
                'success': False,
                'error': "No discounts available in your area within the specified timeframe"
            }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Error matching discounts: {str(e)}"
        }
    
    try:
        # Stage 2.5: AI Meal Suggestion (if meal plan is empty or vague)
        meal_plan = user_input.meal_plan
        
        if not meal_plan or (len(meal_plan) == 1 and len(meal_plan[0]) < 10):
            # User wants AI suggestions based on discounts
            try:
                suggester = MealSuggester()
                
                # Extract product names from valid discounts
                available_products = list(set([d.product_name for d in valid_discounts]))
                
                # Get user preference text (if provided)
                user_pref = meal_plan[0] if meal_plan else ""
                
                # Generate meal suggestions
                suggested_meals = suggester.suggest_meals(
                    available_products=available_products,
                    user_preferences=user_pref,
                    num_meals=3
                )
                
                meal_plan = suggested_meals
                print(f"AI suggested meals: {meal_plan}")
                
            except Exception as e:
                print(f"Error generating meal suggestions: {e}")
                # Continue with original meal plan or default
                if not meal_plan:
                    meal_plan = ["taco", "pasta"]
        
        # Stage 3: Ingredient Mapping
        mapper = IngredientMapper()
        
        # Get all required ingredients for the meal plan
        all_ingredients = []
        for meal in meal_plan:
            ingredients = mapper.get_ingredients_for_meal(meal)
            all_ingredients.extend(ingredients)
        
        # Remove duplicates while preserving order
        unique_ingredients = list(dict.fromkeys(all_ingredients))
        
        if not unique_ingredients:
            return {
                'success': False,
                'error': f"Could not find ingredient information for meals: {', '.join(meal_plan)}"
            }
        
        # Match products to ingredients
        ingredient_matches = mapper.match_products_to_ingredients(
            unique_ingredients,
            valid_discounts
        )
        
        # Check if we have at least some matches
        matched_ingredients = [ing for ing, matches in ingredient_matches.items() if matches]
        if not matched_ingredients:
            return {
                'success': False,
                'error': "No matching products found for your meal plan"
            }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Error mapping ingredients: {str(e)}"
        }
    
    try:
        # Stage 4: Multi-Criteria Optimization
        optimizer = MultiCriteriaOptimizer()
        
        optimized_purchases = optimizer.optimize(
            ingredient_matches,
            user_input.preferences,
            user_input.location,
            user_input.timeframe.start_date
        )
        
        if not optimized_purchases:
            return {
                'success': False,
                'error': "Could not generate optimized shopping plan"
            }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Error optimizing purchases: {str(e)}"
        }
    
    try:
        # Stage 5: Savings Calculation
        calculator = SavingsCalculator()
        
        total_savings = calculator.calculate_monetary_savings(optimized_purchases)
        time_savings = calculator.calculate_time_savings(
            optimized_purchases,
            user_input.location
        )
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Error calculating savings: {str(e)}"
        }
    
    try:
        # Stage 6: Output Formatting
        formatter = OutputFormatter()
        
        # Generate tips and motivation message
        tips = formatter.generate_tips(optimized_purchases)
        motivation_message = formatter.generate_motivation(total_savings, time_savings)
        
        # Create ShoppingRecommendation object
        from .models import ShoppingRecommendation
        
        recommendation = ShoppingRecommendation(
            purchases=optimized_purchases,
            total_savings=total_savings,
            time_savings=time_savings,
            tips=tips,
            motivation_message=motivation_message
        )
        
        # Format the recommendation
        formatted_output = formatter.format_recommendation(recommendation)
        
        return {
            'success': True,
            'recommendation': formatted_output,
            'total_savings': total_savings,
            'time_savings': time_savings,
            'num_purchases': len(optimized_purchases)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Error formatting output: {str(e)}"
        }


# Root agent definition for Google ADK
root_agent = Agent(
    model='gemini-2.5-flash-latest',
    name='shopping_optimizer',
    description="An intelligent shopping assistant that optimizes grocery shopping based on discounts, location, meal plans, and user preferences",
    instruction="""You are a helpful shopping optimization assistant that helps users save money and time on grocery shopping.

You can help users:
- Find the best discounts for their meal plans
- Optimize shopping across multiple stores based on their preferences
- Calculate potential savings in both money and time
- Generate actionable shopping recommendations organized by store and day

When users provide their location (coordinates), meal plan, and preferences, use the optimize_shopping tool to generate a comprehensive shopping recommendation.

Always be friendly and explain the benefits of the optimized plan!""",
    tools=[optimize_shopping]
)


# Test function for development
if __name__ == "__main__":
    print("=== Shopping Optimizer Agent Test ===\n")
    
    # Test with Copenhagen coordinates and a meal plan
    result = optimize_shopping(
        latitude=55.6761,
        longitude=12.5683,
        meal_plan=["taco", "pasta"],
        timeframe="this week",
        maximize_savings=True,
        minimize_stores=True,
        prefer_organic=False
    )
    
    if result['success']:
        print("✓ Optimization successful!\n")
        print(result['recommendation'])
        print(f"\nTotal savings: {result['total_savings']:.2f} kr")
        print(f"Time savings: {result['time_savings']:.2f} hours")
        print(f"Number of purchases: {result['num_purchases']}")
    else:
        print(f"✗ Optimization failed: {result['error']}")

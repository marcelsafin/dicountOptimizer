"""
MealSuggester component - Uses Gemini to suggest meals based on available discounts.
"""

from typing import List, Dict
from google import genai
from google.genai import types
import os


class MealSuggester:
    """
    Uses Gemini AI to suggest meals based on available discount products.
    """
    
    def __init__(self):
        """Initialize Gemini client."""
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        self.client = genai.Client(api_key=api_key)
        self.model = 'gemini-2.5-flash-latest'
    
    def suggest_meals(
        self, 
        available_products: List[str],
        user_preferences: str = "",
        num_meals: int = 3
    ) -> List[str]:
        """
        Suggest meals based on available discount products and user preferences.
        
        Args:
            available_products: List of product names available on discount
            user_preferences: Optional user description of what they want to eat
            num_meals: Number of meal suggestions to generate
            
        Returns:
            List of meal names suggested by Gemini
        """
        # Create prompt for Gemini
        prompt = self._create_prompt(available_products, user_preferences, num_meals)
        
        try:
            # Call Gemini API
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=500,
                )
            )
            
            # Parse response
            meals = self._parse_response(response.text)
            
            return meals[:num_meals]
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            # Fallback to simple suggestions
            return self._fallback_suggestions(available_products, num_meals)
    
    def _create_prompt(
        self, 
        available_products: List[str],
        user_preferences: str,
        num_meals: int
    ) -> str:
        """Create prompt for Gemini."""
        products_list = "\n".join([f"- {product}" for product in available_products])
        
        prompt = f"""You are a creative meal planning assistant for a Danish grocery shopping app.

Available products on discount this week:
{products_list}

Task: Suggest {num_meals} delicious meals that can be made using these discounted products.

"""
        
        if user_preferences:
            prompt += f"User preferences: {user_preferences}\n\n"
        
        prompt += """Requirements:
- Each meal should use at least 3-4 of the available products
- Meals should be practical and easy to prepare
- Consider Danish cuisine preferences
- Return ONLY the meal names, one per line
- Use simple, clear names (e.g., "Taco", "Pasta Bolognese", "Grøntsagssuppe")

Meal suggestions:"""
        
        return prompt
    
    def _parse_response(self, response_text: str) -> List[str]:
        """Parse Gemini response to extract meal names."""
        meals = []
        
        # Split by lines and clean up
        lines = response_text.strip().split('\n')
        
        for line in lines:
            # Remove numbering, bullets, and extra whitespace
            meal = line.strip()
            meal = meal.lstrip('0123456789.-*• ')
            meal = meal.strip()
            
            # Skip empty lines and very short responses
            if meal and len(meal) > 2:
                meals.append(meal)
        
        return meals
    
    def _fallback_suggestions(
        self, 
        available_products: List[str],
        num_meals: int
    ) -> List[str]:
        """Provide fallback meal suggestions if Gemini fails."""
        # Simple rule-based fallback
        fallback_meals = []
        
        products_lower = [p.lower() for p in available_products]
        
        # Check for common meal patterns
        if any('tortilla' in p or 'hakket' in p for p in products_lower):
            fallback_meals.append("Taco")
        
        if any('pasta' in p for p in products_lower):
            fallback_meals.append("Pasta Bolognese")
        
        if any('grøntsag' in p or 'gulerod' in p or 'kartof' in p for p in products_lower):
            fallback_meals.append("Grøntsagssuppe")
        
        # Pad with generic suggestions if needed
        generic = ["Salat", "Sandwich", "Wrap", "Stir-fry", "Omelet"]
        fallback_meals.extend(generic)
        
        return fallback_meals[:num_meals]

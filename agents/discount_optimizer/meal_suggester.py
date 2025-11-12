"""
MealSuggester component - Uses Gemini to suggest meals based on available discounts.

Uses the latest Google GenAI SDK (google-genai) with best practices:
- Proper client initialization
- Latest model naming conventions
- Structured configuration
- Robust error handling
"""

from typing import List, Optional
from datetime import date, timedelta
import os
from google import genai
from google.genai import types


class MealSuggester:
    """
    Uses Gemini AI to suggest meals based on available discount products.
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
    """
    
    def __init__(self):
        """Initialize Gemini client with latest SDK best practices."""
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        # Initialize client using latest google-genai SDK
        self.client = genai.Client(api_key=api_key)
        
        # Use Gemini 2.5 Flash - latest stable production model (as of Nov 2025)
        self.model = 'models/gemini-2.5-flash'
    
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
            
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
        """
        # Create prompt for Gemini
        prompt = self._create_prompt(available_products, user_preferences, num_meals)
        
        try:
            # Call Gemini API using latest SDK patterns
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=1000,  # Increased to account for thinking tokens
                    top_p=0.95,
                    top_k=40,
                )
            )
            
            # Extract text from response
            # The google-genai SDK returns response with candidates
            response_text = None
            
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        part = candidate.content.parts[0]
                        if hasattr(part, 'text'):
                            response_text = part.text
            
            # Fallback to response.text if available
            if not response_text and hasattr(response, 'text'):
                response_text = response.text
            
            if not response_text:
                raise ValueError("Empty response from Gemini API")
            
            # Parse response
            meals = self._parse_response(response_text)
            
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
        """Create prompt for Gemini - optimized to reduce thinking tokens."""
        # Limit products list to avoid token overflow
        products_sample = available_products[:20] if len(available_products) > 20 else available_products
        products_list = ", ".join(products_sample)
        
        prompt = f"""Suggest {num_meals} meal names using these products: {products_list}

"""
        
        if user_preferences:
            prompt += f"Preference: {user_preferences}\n"
        
        prompt += f"""Return ONLY {num_meals} meal names, one per line. Examples: "Taco", "Pasta Bolognese", "Grøntsagssuppe"

Meals:"""
        
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

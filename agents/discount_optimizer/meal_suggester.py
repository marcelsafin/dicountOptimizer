"""
MealSuggester component - Uses Gemini to suggest meals based on available discounts.

Uses the latest Google GenAI SDK (google-genai) with best practices:
- Proper client initialization
- Latest model naming conventions
- Structured configuration
- Robust error handling
"""

import builtins
import contextlib
import os
from datetime import date

from google import genai
from google.genai import types


class MealSuggester:
    """
    Uses Gemini AI to suggest meals based on available discount products.

    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
    """

    def __init__(self):
        """Initialize Gemini client with latest SDK best practices."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        # Initialize client using latest google-genai SDK
        self.client = genai.Client(api_key=api_key)

        # Use Gemini 2.5 Flash - latest stable production model (as of Nov 2025)
        self.model = "models/gemini-2.5-flash"

    def suggest_meals(
        self,
        available_products: list[str],
        user_preferences: str = "",
        num_meals: int = 3,
        product_details: list[dict] | None = None,
        meal_types: list[str] | None = None,
        excluded_ingredients: list[str] | None = None,
    ) -> list[str]:
        """
        Suggest meals based on available discount products and user preferences.

        Args:
            available_products: List of product names available on discount
            user_preferences: Optional user description of what they want to eat
            num_meals: Number of meal suggestions to generate
            product_details: Optional list of dicts with product details (price, expiration, etc.)
            meal_types: List of meal types to include (breakfast, lunch, dinner, snacks)
            excluded_ingredients: List of ingredients/allergens to exclude

        Returns:
            List of meal names suggested by Gemini

        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 7.3, 8.5, 11.4
        """
        # Create prompt for Gemini
        prompt = self._create_prompt(
            available_products,
            user_preferences,
            num_meals,
            product_details,
            meal_types,
            excluded_ingredients,
        )

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
                ),
            )

            # Extract text from response
            # The google-genai SDK returns response with candidates
            response_text = None

            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and candidate.content:
                    if hasattr(candidate.content, "parts") and candidate.content.parts:
                        part = candidate.content.parts[0]
                        if hasattr(part, "text"):
                            response_text = part.text

            # Fallback to response.text if available
            if not response_text and hasattr(response, "text"):
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
        available_products: list[str],
        user_preferences: str,
        num_meals: int,
        product_details: list[dict] | None = None,
        meal_types: list[str] | None = None,
        excluded_ingredients: list[str] | None = None,
    ) -> str:
        """
        Create optimized prompt for Gemini with diverse meal types and expiration prioritization.

        Requirements: 3.1, 3.2, 7.3, 8.5, 11.4
        """
        # Limit products list to avoid token overflow
        products_sample = (
            available_products[:20] if len(available_products) > 20 else available_products
        )

        # Build detailed product list with expiration info if available
        if product_details:
            product_lines = []
            today = date.today()

            for detail in product_details[:20]:  # Limit to 20 products
                product_name = detail.get("name", "")
                expiration = detail.get("expiration_date")
                discount_percent = detail.get("discount_percent", 0)

                # Calculate days until expiration
                days_until_expiry = None
                urgency_marker = ""
                if expiration:
                    if isinstance(expiration, str):
                        with contextlib.suppress(builtins.BaseException):
                            expiration = date.fromisoformat(expiration)
                    if isinstance(expiration, date):
                        days_until_expiry = (expiration - today).days
                        if days_until_expiry <= 2:
                            urgency_marker = (
                                " [URGENT - expires in " + str(days_until_expiry) + " days]"
                            )
                        elif days_until_expiry <= 5:
                            urgency_marker = " [expires soon - " + str(days_until_expiry) + " days]"

                product_line = f"- {product_name}"
                if discount_percent > 0:
                    product_line += f" ({int(discount_percent)}% off)"
                product_line += urgency_marker
                product_lines.append(product_line)

            products_text = "\n".join(product_lines)
        else:
            products_text = "\n".join([f"- {p}" for p in products_sample])

        # Build comprehensive prompt with diverse meal types and dietary considerations
        prompt = f"""You are a creative chef helping reduce food waste by suggesting meals using discounted products.

Available products:
{products_text}

Task: Suggest {num_meals} diverse and creative meal ideas using these products.

Requirements:
1. DIVERSITY: Include different meal types - breakfast, lunch, dinner, snacks, or desserts
2. URGENCY: Prioritize products marked as URGENT or expiring soon in your meal suggestions
3. CREATIVITY: Think beyond obvious combinations - be inventive with flavors and cuisines
4. PRACTICALITY: Suggest meals that can realistically be made with available products
"""

        # Add meal type filters if provided
        if meal_types and len(meal_types) < 4:  # Only add if user has filtered
            meal_types_str = ", ".join(meal_types)
            prompt += f"5. MEAL TYPES: Only suggest meals suitable for: {meal_types_str}\n"

        # Add excluded ingredients if provided
        if excluded_ingredients:
            excluded_str = ", ".join(excluded_ingredients)
            prompt += f"6. EXCLUSIONS: Do NOT suggest meals containing: {excluded_str}\n"

        # Add user preferences if provided
        if user_preferences:
            prompt += f"7. USER PREFERENCE: Consider this preference - {user_preferences}\n"

        # Add dietary restriction guidance
        prompt += """
Common dietary considerations to keep in mind:
- Vegetarian options (if no meat products are needed)
- Quick meals (under 30 minutes)
- Family-friendly options
- Budget-conscious combinations

"""

        prompt += f"""Output format: Return ONLY {num_meals} meal names, one per line.
Examples: "Morgenmad Burrito", "Hurtig Pasta Carbonara", "Grøntsagssuppe med Brød", "Taco Tuesday"

Meals:"""

        return prompt

    def _parse_response(self, response_text: str) -> list[str]:
        """Parse Gemini response to extract meal names."""
        meals = []

        # Split by lines and clean up
        lines = response_text.strip().split("\n")

        for line in lines:
            # Remove numbering, bullets, and extra whitespace
            meal = line.strip()
            meal = meal.lstrip("0123456789.-*• ")
            meal = meal.strip()

            # Skip empty lines and very short responses
            if meal and len(meal) > 2:
                meals.append(meal)

        return meals

    def _fallback_suggestions(self, available_products: list[str], num_meals: int) -> list[str]:
        """Provide fallback meal suggestions if Gemini fails."""
        # Simple rule-based fallback
        fallback_meals = []

        products_lower = [p.lower() for p in available_products]

        # Check for common meal patterns
        if any("tortilla" in p or "hakket" in p for p in products_lower):
            fallback_meals.append("Taco")

        if any("pasta" in p for p in products_lower):
            fallback_meals.append("Pasta Bolognese")

        if any("grøntsag" in p or "gulerod" in p or "kartof" in p for p in products_lower):
            fallback_meals.append("Grøntsagssuppe")

        # Pad with generic suggestions if needed
        generic = ["Salat", "Sandwich", "Wrap", "Stir-fry", "Omelet"]
        fallback_meals.extend(generic)

        return fallback_meals[:num_meals]

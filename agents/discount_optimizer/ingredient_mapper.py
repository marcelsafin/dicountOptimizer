"""
IngredientMapper component for mapping meals to ingredients and matching with products.
"""

from difflib import SequenceMatcher

from .models import MEAL_INGREDIENTS, DiscountItem


class IngredientMapper:
    """
    Responsible for mapping meals to required ingredients and matching with available products.
    """

    def get_ingredients_for_meal(self, meal_name: str) -> list[str]:
        """
        Get the list of ingredients required for a specific meal.

        Args:
            meal_name: Name of the meal (e.g., "taco", "pasta", "grøntsagssuppe")

        Returns:
            List of ingredient names required for the meal.
            Returns empty list if meal is not found in database.
        """
        # Normalize meal name to lowercase for case-insensitive lookup
        normalized_meal = meal_name.lower().strip()

        # Look up ingredients in the meal database
        ingredients = MEAL_INGREDIENTS.get(normalized_meal, [])

        return ingredients.copy()

    def fuzzy_match(self, ingredient: str, product_name: str) -> float:
        """
        Calculate fuzzy match score between an ingredient and a product name.

        Uses sequence matching to handle variations in product naming and support
        multiple languages (e.g., "ground beef" vs "hakket oksekød").

        Args:
            ingredient: Ingredient name to match
            product_name: Product name from discount data

        Returns:
            Match score between 0.0 (no match) and 1.0 (perfect match)
        """
        # Normalize both strings to lowercase for comparison
        ingredient_lower = ingredient.lower().strip()
        product_lower = product_name.lower().strip()

        # Direct substring match gets high score
        if ingredient_lower in product_lower or product_lower in ingredient_lower:
            return 0.9

        # Use SequenceMatcher for fuzzy matching
        matcher = SequenceMatcher(None, ingredient_lower, product_lower)
        return matcher.ratio()

    def match_products_to_ingredients(
        self, ingredients: list[str], discounts: list[DiscountItem]
    ) -> dict[str, list[DiscountItem]]:
        """
        Match available discounted products to required meal ingredients.

        For each ingredient, finds all discount options across different stores
        using fuzzy matching to handle product name variations.

        Args:
            ingredients: List of required ingredient names
            discounts: List of available discount items

        Returns:
            Dictionary mapping ingredient names to lists of matching discount items.
            Ingredients with no matches will have an empty list.
        """
        # Initialize result dictionary with empty lists for all ingredients
        matches: dict[str, list[DiscountItem]] = {ingredient: [] for ingredient in ingredients}

        # Minimum match threshold for considering a product as matching
        MATCH_THRESHOLD = 0.6

        # For each ingredient, find matching products
        for ingredient in ingredients:
            for discount in discounts:
                match_score = self.fuzzy_match(ingredient, discount.product_name)

                # If match score exceeds threshold, add to matches
                if match_score >= MATCH_THRESHOLD:
                    matches[ingredient].append(discount)

        return matches

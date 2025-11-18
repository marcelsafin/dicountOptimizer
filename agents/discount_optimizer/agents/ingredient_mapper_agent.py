"""
IngredientMapper ADK Agent - AI-powered ingredient mapping using Google ADK.

This module implements the IngredientMapper as a proper Google ADK agent with:
- Typed tool functions using Pydantic models
- Gemini-powered intelligent mapping with multi-language support
- Structured logging with agent context
- Ingredient-to-product mapping with confidence scores
- Handles product name variations across languages (English, Danish, etc.)

Requirements: 2.1, 2.3, 3.1, 3.3
"""

from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, field_validator

from agents.discount_optimizer.config import settings
from agents.discount_optimizer.logging import get_logger, set_agent_context


# Get logger for this module
logger = get_logger(__name__)


class ProductMatch(BaseModel):
    """
    A matched product with confidence score.

    Attributes:
        product_name: Name of the matched product
        store_name: Name of the store offering the product
        match_score: Confidence score (0.0-1.0) indicating match quality
        discount_percent: Discount percentage for the product
        price: Discounted price of the product

    Example:
        >>> match = ProductMatch(
        ...     product_name="Hakket oksekød 8-12%",
        ...     store_name="Føtex",
        ...     match_score=0.92,
        ...     discount_percent=25.0,
        ...     price=35.00,
        ... )
    """

    product_name: str = Field(description="Name of the matched product")
    store_name: str = Field(description="Name of the store")
    match_score: float = Field(ge=0.0, le=1.0, description="Match confidence score")
    discount_percent: float = Field(ge=0.0, le=100.0, description="Discount percentage")
    price: float = Field(gt=0.0, description="Discounted price")


class IngredientMapping(BaseModel):
    """
    Mapping of an ingredient to matched products.

    Attributes:
        ingredient: The ingredient name being mapped
        matched_products: List of products that match this ingredient
        best_match: The highest-scoring product match (if any)
        has_matches: Whether any products were found for this ingredient

    Example:
        >>> mapping = IngredientMapping(
        ...     ingredient="ground beef",
        ...     matched_products=[...],
        ...     best_match=ProductMatch(...),
        ...     has_matches=True,
        ... )
    """

    ingredient: str = Field(description="The ingredient name")
    matched_products: list[ProductMatch] = Field(
        default_factory=list, description="List of matching products"
    )
    best_match: ProductMatch | None = Field(
        default=None, description="Highest-scoring product match"
    )
    has_matches: bool = Field(default=False, description="Whether any matches were found")


class IngredientMappingInput(BaseModel):
    """
    Input model for ingredient mapping tool.

    Attributes:
        meal_name: Name of the meal to map ingredients for
        ingredients: List of ingredient names required for the meal
        available_products: List of available discounted products
        match_threshold: Minimum match score to consider (0.0-1.0)
        max_matches_per_ingredient: Maximum number of matches to return per ingredient

    Example:
        >>> input_data = IngredientMappingInput(
        ...     meal_name="Taco Tuesday",
        ...     ingredients=["tortillas", "ground beef", "cheese", "lettuce"],
        ...     available_products=[...],
        ...     match_threshold=0.6,
        ... )
    """

    meal_name: str = Field(description="Name of the meal", min_length=1, max_length=200)
    ingredients: list[str] = Field(
        description="List of ingredient names required for the meal", min_length=1, max_length=50
    )
    available_products: list[dict[str, Any]] = Field(
        description="List of available discounted products with details",
        min_length=0,
        max_length=200,
    )
    match_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum match score to consider a product as matching",
    )
    max_matches_per_ingredient: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of product matches to return per ingredient",
    )

    @field_validator("ingredients")
    @classmethod
    def validate_ingredients_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure ingredients list is not empty and contains valid strings."""
        if not v:
            raise ValueError("ingredients list cannot be empty")

        # Filter out empty strings
        valid_ingredients = [ing.strip() for ing in v if ing and ing.strip()]

        if not valid_ingredients:
            raise ValueError("ingredients list must contain at least one non-empty string")

        return valid_ingredients


class IngredientMappingOutput(BaseModel):
    """
    Output model from ingredient mapping tool.

    Attributes:
        meal_name: Name of the meal that was mapped
        mappings: List of ingredient mappings with matched products
        total_ingredients: Total number of ingredients requested
        ingredients_with_matches: Number of ingredients that had at least one match
        coverage_percent: Percentage of ingredients that were successfully matched
        unmapped_ingredients: List of ingredients with no matches

    Example:
        >>> output = IngredientMappingOutput(
        ...     meal_name="Taco Tuesday",
        ...     mappings=[...],
        ...     total_ingredients=4,
        ...     ingredients_with_matches=3,
        ...     coverage_percent=75.0,
        ...     unmapped_ingredients=["lettuce"],
        ... )
    """

    meal_name: str = Field(description="Name of the meal")
    mappings: list[IngredientMapping] = Field(description="List of ingredient mappings")
    total_ingredients: int = Field(ge=0, description="Total number of ingredients")
    ingredients_with_matches: int = Field(ge=0, description="Number of ingredients with matches")
    coverage_percent: float = Field(
        ge=0.0, le=100.0, description="Percentage of ingredients matched"
    )
    unmapped_ingredients: list[str] = Field(
        default_factory=list, description="Ingredients with no matches"
    )


class IngredientMapperAgent:
    """
    ADK agent for AI-powered ingredient mapping.

    This agent uses Gemini to intelligently map meal ingredients to available
    discounted products. Unlike rule-based fuzzy matching, Gemini can:
    - Understand multi-language product names (English, Danish, etc.)
    - Handle product variations ("ground beef" → "Hakket oksekød 8-12%")
    - Provide confidence scores for matches
    - Adapt to new products without code changes

    The agent follows Google ADK best practices (November 2025):
    - Uses latest google.genai SDK
    - Implements typed tool functions
    - Validates inputs/outputs with Pydantic
    - Includes structured logging
    - Delegates complex logic to AI

    Example:
        >>> agent = IngredientMapperAgent()
        >>> input_data = IngredientMappingInput(
        ...     meal_name="Taco Tuesday",
        ...     ingredients=["tortillas", "ground beef", "cheese"],
        ...     available_products=[...],
        ... )
        >>> output = await agent.run(input_data)
        >>> print(
        ...     f"Matched {output.ingredients_with_matches}/{output.total_ingredients} ingredients"
        ... )

    Requirements: 2.1, 2.3, 3.1, 3.3
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize IngredientMapper agent with Google ADK.

        Args:
            api_key: Optional Google API key. If None, uses settings.google_api_key

        Raises:
            ValueError: If API key is not provided and not in settings
        """
        # Set agent context for logging
        set_agent_context("ingredient_mapper")

        # Get API key
        if api_key is None:
            api_key = settings.google_api_key.get_secret_value()

        if not api_key:
            raise ValueError("Google API key is required for IngredientMapperAgent")

        # Initialize Gemini client using latest google-genai SDK
        self.client = genai.Client(api_key=api_key)
        self.model = f"models/{settings.agent_model}"

        logger.info(
            "ingredient_mapper_agent_initialized",
            model=settings.agent_model,
            temperature=settings.agent_temperature,
            max_tokens=settings.agent_max_tokens,
        )

    async def run(self, input_data: IngredientMappingInput) -> IngredientMappingOutput:
        """
        Run the ingredient mapper agent with input data.

        This is the main entry point for the agent. It validates input,
        calls Gemini to perform intelligent mapping, and returns structured
        output with ingredient-to-product mappings.

        Args:
            input_data: Validated input data for ingredient mapping

        Returns:
            Structured output with ingredient mappings and match statistics

        Raises:
            ValueError: If input validation fails
            Exception: If Gemini API call fails after retries

        Requirements: 2.1, 2.3, 3.1, 3.3
        """
        logger.info(
            "ingredient_mapping_started",
            meal_name=input_data.meal_name,
            num_ingredients=len(input_data.ingredients),
            num_products=len(input_data.available_products),
            match_threshold=input_data.match_threshold,
        )

        try:
            # Map ingredients to products using Gemini
            output = await self.map_ingredients(input_data)

            logger.info(
                "ingredient_mapping_completed",
                meal_name=output.meal_name,
                total_ingredients=output.total_ingredients,
                ingredients_with_matches=output.ingredients_with_matches,
                coverage_percent=output.coverage_percent,
                unmapped_count=len(output.unmapped_ingredients),
            )

            return output

        except Exception as e:
            logger.exception(
                "ingredient_mapping_failed",
                error=str(e),
                error_type=type(e).__name__,
                meal_name=input_data.meal_name,
            )

            # Fallback to empty mappings
            logger.warning("falling_back_to_empty_mappings")
            return self._fallback_mappings(input_data)

    async def map_ingredients(self, input_data: IngredientMappingInput) -> IngredientMappingOutput:
        """
        Map ingredients to available products using Gemini.

        This tool uses Gemini's language understanding to intelligently match
        ingredients to products. Gemini can:
        - Understand multi-language product names (English, Danish, etc.)
        - Handle product variations and synonyms
        - Provide confidence scores for matches
        - Adapt to new products without code changes

        Args:
            input_data: Validated input data for ingredient mapping

        Returns:
            Structured output with ingredient mappings

        Requirements: 2.1, 2.3, 3.1, 3.3
        """
        # Create prompt for Gemini
        prompt = self._create_prompt(input_data)

        logger.debug("calling_gemini_api", model=self.model, prompt_length=len(prompt))

        try:
            # Call Gemini API using latest SDK patterns
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=settings.agent_temperature,
                    max_output_tokens=settings.agent_max_tokens,
                    top_p=settings.agent_top_p,
                    top_k=settings.agent_top_k,
                ),
            )

            # Extract text from response
            response_text = self._extract_response_text(response)

            if not response_text:
                raise ValueError("Empty response from Gemini API")

            logger.debug("gemini_response_received", response_length=len(response_text))

            # Parse response into structured output
            return self._parse_response(response_text, input_data)

        except Exception as e:
            logger.exception("gemini_api_call_failed", error=str(e), error_type=type(e).__name__)
            raise

    def _create_prompt(self, input_data: IngredientMappingInput) -> str:
        """
        Create optimized prompt for Gemini ingredient mapping.

        The prompt instructs Gemini to:
        - Map each ingredient to the best matching products
        - Handle multi-language product names
        - Provide confidence scores (0.0-1.0)
        - Return structured JSON output

        Args:
            input_data: Validated input data

        Returns:
            Formatted prompt string for Gemini

        Requirements: 3.1, 3.3
        """
        # System instruction
        system_instruction = self._get_system_instruction()

        # Format ingredients list
        ingredients_text = "\n".join([f"- {ing}" for ing in input_data.ingredients])

        # Format products list (limit to avoid token overflow)
        max_products = 50
        products_sample = input_data.available_products[:max_products]
        products_text = "\n".join(
            [
                f"- {p.get('name', p.get('product_name', 'Unknown'))} "
                f"(Store: {p.get('store_name', p.get('store', 'Unknown'))}, "
                f"Discount: {p.get('discount_percent', 0)}%, "
                f"Price: {p.get('discount_price', p.get('price', 0))})"
                for p in products_sample
            ]
        )

        # Build complete prompt
        return f"""{system_instruction}

Meal: {input_data.meal_name}

Required Ingredients:
{ingredients_text}

Available Products:
{products_text}

Task: Map each ingredient to the best matching products from the available list.

Requirements:
1. For each ingredient, find ALL products that could match it
2. Provide a confidence score (0.0-1.0) for each match
3. Only include matches with confidence >= {input_data.match_threshold}
4. Return up to {input_data.max_matches_per_ingredient} matches per ingredient
5. Handle multi-language names (e.g., "ground beef" matches "Hakket oksekød")
6. Consider product variations (e.g., "cheese" matches "Cheddar skiver")

Output format: Return a JSON object with this exact structure:
{{
    "mappings": [
        {{
            "ingredient": "tortillas",
            "matches": [
                {{
                    "product_name": "Tortillas 8 stk",
                    "store_name": "Føtex",
                    "confidence": 0.95,
                    "discount_percent": 30.0,
                    "price": 14.95
                }}
            ]
        }}
    ]
}}

Respond with ONLY the JSON object, no additional text.
"""

    def _get_system_instruction(self) -> str:
        """
        Get system instruction for the agent.

        This defines the agent's role, goals, and behavior.

        Returns:
            System instruction string

        Requirements: 3.1, 3.3
        """
        return """You are an expert grocery product matcher with deep knowledge of:
- Multi-language product names (English, Danish, Swedish, Norwegian, etc.)
- Product variations and synonyms (e.g., "ground beef" = "hakket oksekød" = "minced beef")
- Brand names and generic equivalents
- Product categories and substitutions

Your task is to intelligently map ingredient names to actual grocery products, handling:
- Language differences (English ingredients → Danish products)
- Product variations (e.g., "cheese" → "Cheddar skiver", "Mozzarella", "Ost")
- Partial matches (e.g., "beef" → "Hakket oksekød 8-12%")
- Synonyms and common names

Provide confidence scores based on:
- Exact name match: 0.95-1.0
- Strong semantic match: 0.80-0.94
- Partial/category match: 0.60-0.79
- Weak/uncertain match: 0.40-0.59
- No match: < 0.40 (exclude from results)"""

    def _extract_response_text(self, response: Any) -> str | None:
        """
        Extract text from Gemini API response.

        Handles different response formats from the google-genai SDK.

        Args:
            response: Response object from Gemini API

        Returns:
            Extracted text or None if not found
        """
        response_text = None

        # Try to extract from candidates
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

        return response_text

    def _parse_response(
        self, response_text: str, input_data: IngredientMappingInput
    ) -> IngredientMappingOutput:
        """
        Parse Gemini response into structured output.

        Attempts to parse JSON response from Gemini and convert it to
        IngredientMappingOutput with proper validation.

        Args:
            response_text: Raw text response from Gemini
            input_data: Original input data for context

        Returns:
            Structured IngredientMappingOutput
        """
        import json

        # Try to parse as JSON
        try:
            # Remove markdown code blocks if present
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            # Parse JSON
            data = json.loads(cleaned_text)

            # Extract mappings
            mappings_data = data.get("mappings", [])

            # Build IngredientMapping objects
            mappings: list[IngredientMapping] = []
            unmapped_ingredients: list[str] = []

            for ingredient in input_data.ingredients:
                # Find mapping for this ingredient
                ingredient_data = next(
                    (
                        m
                        for m in mappings_data
                        if m.get("ingredient", "").lower() == ingredient.lower()
                    ),
                    None,
                )

                if ingredient_data and ingredient_data.get("matches"):
                    # Convert matches to ProductMatch objects
                    matched_products = [
                        ProductMatch(
                            product_name=m.get("product_name", ""),
                            store_name=m.get("store_name", "Unknown"),
                            match_score=float(m.get("confidence", 0.0)),
                            discount_percent=float(m.get("discount_percent", 0.0)),
                            price=float(m.get("price", 0.0)),
                        )
                        for m in ingredient_data.get("matches", [])
                    ]

                    best_match = matched_products[0] if matched_products else None

                    mapping = IngredientMapping(
                        ingredient=ingredient,
                        matched_products=matched_products,
                        best_match=best_match,
                        has_matches=True,
                    )
                    mappings.append(mapping)
                else:
                    # No matches found
                    mapping = IngredientMapping(
                        ingredient=ingredient,
                        matched_products=[],
                        best_match=None,
                        has_matches=False,
                    )
                    mappings.append(mapping)
                    unmapped_ingredients.append(ingredient)

            # Calculate statistics
            total_ingredients = len(input_data.ingredients)
            ingredients_with_matches = total_ingredients - len(unmapped_ingredients)
            coverage_percent = (
                (ingredients_with_matches / total_ingredients * 100.0)
                if total_ingredients > 0
                else 0.0
            )

            return IngredientMappingOutput(
                meal_name=input_data.meal_name,
                mappings=mappings,
                total_ingredients=total_ingredients,
                ingredients_with_matches=ingredients_with_matches,
                coverage_percent=coverage_percent,
                unmapped_ingredients=unmapped_ingredients,
            )

        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            logger.warning("json_parsing_failed", error=str(e))
            raise ValueError(f"Failed to parse Gemini response: {e}")

    def _fallback_mappings(self, input_data: IngredientMappingInput) -> IngredientMappingOutput:
        """
        Provide fallback empty mappings if Gemini fails.

        Args:
            input_data: Original input data

        Returns:
            IngredientMappingOutput with empty mappings

        Requirements: 4.2
        """
        logger.info("generating_fallback_empty_mappings")

        # Create empty mappings for all ingredients
        mappings = [
            IngredientMapping(
                ingredient=ingredient, matched_products=[], best_match=None, has_matches=False
            )
            for ingredient in input_data.ingredients
        ]

        return IngredientMappingOutput(
            meal_name=input_data.meal_name,
            mappings=mappings,
            total_ingredients=len(input_data.ingredients),
            ingredients_with_matches=0,
            coverage_percent=0.0,
            unmapped_ingredients=input_data.ingredients.copy(),
        )

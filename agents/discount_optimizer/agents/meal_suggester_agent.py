"""
MealSuggester ADK Agent - AI-powered meal suggestions using Google ADK.

This module implements the MealSuggester as a proper Google ADK agent with:
- Typed tool functions using Pydantic models
- Structured logging with agent context
- Creative meal suggestions based on available products
- Expiration date prioritization to reduce food waste
- Dietary preference and restriction support

Requirements: 2.1, 2.3, 3.1, 3.3, 10.1
"""

from datetime import UTC, date, datetime
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field


def get_today() -> date:
    """Get today's date in a timezone-aware manner."""
    return datetime.now(UTC).date()


import contextlib

from agents.discount_optimizer.config import settings
from agents.discount_optimizer.logging import get_logger, set_agent_context


# Get logger for this module
logger = get_logger(__name__)


class MealSuggestionInput(BaseModel):
    """
    Input model for meal suggestion tool.

    Attributes:
        available_products: List of product names available on discount
        user_preferences: Optional user dietary preferences or meal desires
        num_meals: Number of meal suggestions to generate (1-10)
        meal_types: List of meal types to include (breakfast, lunch, dinner, snacks)
        excluded_ingredients: List of ingredients or allergens to exclude
        product_details: Optional detailed product information with expiration dates

    Example:
        >>> input_data = MealSuggestionInput(
        ...     available_products=["tortillas", "hakket oksekød", "ost"],
        ...     user_preferences="quick and easy meals",
        ...     num_meals=3,
        ...     meal_types=["lunch", "dinner"],
        ... )
    """

    available_products: list[str] = Field(
        description="List of available product names from discount offers",
        min_length=1,
        max_length=50,
    )
    user_preferences: str = Field(
        default="", description="User dietary preferences or meal desires", max_length=500
    )
    num_meals: int = Field(
        default=3, ge=1, le=10, description="Number of meal suggestions to generate"
    )
    meal_types: list[str] = Field(
        default_factory=lambda: ["breakfast", "lunch", "dinner", "snacks"],
        description="List of meal types to include in suggestions",
    )
    excluded_ingredients: list[str] = Field(
        default_factory=list,
        description="List of ingredients or allergens to exclude",
        max_length=20,
    )
    product_details: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional detailed product information with expiration dates and discounts",
    )


class MealSuggestionOutput(BaseModel):
    """
    Output model from meal suggestion tool.

    Attributes:
        suggested_meals: List of suggested meal names
        reasoning: Brief explanation of why these meals were suggested
        urgency_notes: Notes about products expiring soon that should be used first

    Example:
        >>> output = MealSuggestionOutput(
        ...     suggested_meals=["Taco Tuesday", "Pasta Carbonara", "Grøntsagssuppe"],
        ...     reasoning="Meals prioritize products expiring within 2 days",
        ...     urgency_notes="Use tortillas and hakket oksekød first (expire in 1 day)",
        ... )
    """

    suggested_meals: list[str] = Field(
        description="List of suggested meal names", min_length=1, max_length=10
    )
    reasoning: str = Field(
        description="Explanation of meal suggestions and product usage", max_length=1000
    )
    urgency_notes: str = Field(
        default="", description="Notes about products expiring soon", max_length=500
    )


class MealSuggesterAgent:
    """
    ADK agent for AI-powered meal suggestions.

    This agent uses Google's Gemini model to generate creative meal suggestions
    based on available discounted products. It prioritizes products expiring soon
    to reduce food waste and respects dietary preferences and restrictions.

    The agent follows Google ADK best practices (November 2025):
    - Uses latest google.genai SDK
    - Implements typed tool functions
    - Validates inputs/outputs with Pydantic
    - Includes structured logging
    - Handles errors gracefully with fallbacks

    Example:
        >>> agent = MealSuggesterAgent()
        >>> input_data = MealSuggestionInput(
        ...     available_products=["tortillas", "hakket oksekød", "ost"], num_meals=3
        ... )
        >>> output = await agent.run(input_data)
        >>> print(output.suggested_meals)
        ['Taco Tuesday', 'Quesadillas', 'Burrito Bowl']

    Requirements: 2.1, 2.3, 3.1, 3.3, 10.1
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize MealSuggester agent with Google ADK.

        Args:
            api_key: Optional Google API key. If None, uses settings.google_api_key

        Raises:
            ValueError: If API key is not provided and not in settings
        """
        # Set agent context for logging
        set_agent_context("meal_suggester")

        # Get API key
        if api_key is None:
            api_key = settings.google_api_key.get_secret_value()

        if not api_key:
            raise ValueError("Google API key is required for MealSuggesterAgent")

        # Initialize Gemini client using latest google-genai SDK
        self.client = genai.Client(api_key=api_key)
        self.model = f"models/{settings.agent_model}"

        logger.info(
            "meal_suggester_agent_initialized",
            model=settings.agent_model,
            temperature=settings.agent_temperature,
            max_tokens=settings.agent_max_tokens,
        )

    async def run(self, input_data: MealSuggestionInput) -> MealSuggestionOutput:
        """
        Run the meal suggester agent with input data.

        This is the main entry point for the agent. It validates input,
        calls the Gemini model, and returns structured output.

        Args:
            input_data: Validated input data for meal suggestions

        Returns:
            Structured output with meal suggestions and reasoning

        Raises:
            ValueError: If input validation fails
            Exception: If Gemini API call fails after retries

        Requirements: 2.1, 2.3, 3.1, 3.3, 10.1
        """
        logger.info(
            "meal_suggestion_started",
            num_products=len(input_data.available_products),
            num_meals=input_data.num_meals,
            has_preferences=bool(input_data.user_preferences),
            meal_types=input_data.meal_types,
            excluded_ingredients=input_data.excluded_ingredients,
        )

        try:
            # Generate meal suggestions using Gemini
            output = await self.suggest_meals(input_data)

            logger.info(
                "meal_suggestion_completed",
                num_meals_generated=len(output.suggested_meals),
                has_urgency_notes=bool(output.urgency_notes),
            )

            return output

        except Exception as e:
            logger.exception("meal_suggestion_failed", error=str(e), error_type=type(e).__name__)

            # Fallback to rule-based suggestions
            logger.warning("falling_back_to_rule_based_suggestions")
            return self._fallback_suggestions(input_data)

    async def suggest_meals(self, input_data: MealSuggestionInput) -> MealSuggestionOutput:
        """
        Suggest meals based on available products using Gemini.

        This tool uses Gemini to generate creative meal suggestions that:
        - Utilize available discounted products
        - Respect dietary preferences and restrictions
        - Prioritize products expiring soon
        - Offer diverse meal types

        Args:
            input_data: Validated input data for meal suggestions

        Returns:
            Structured output with meal suggestions and reasoning

        Requirements: 2.1, 2.3, 3.1, 3.3, 10.1
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

    def _create_prompt(self, input_data: MealSuggestionInput) -> str:
        """
        Create optimized prompt for Gemini with system instruction.

        The prompt includes:
        - System instruction defining the agent's role
        - Available products with expiration urgency markers
        - User preferences and dietary restrictions
        - Output format specification

        Args:
            input_data: Validated input data

        Returns:
            Formatted prompt string for Gemini

        Requirements: 3.1, 3.3
        """
        # System instruction
        system_instruction = self._get_system_instruction()

        # Build product list with expiration info
        products_text = self._format_products(input_data)

        # Build requirements section
        requirements = [
            f"1. DIVERSITY: Include different meal types - {', '.join(input_data.meal_types)}",
            "2. URGENCY: Prioritize products marked as URGENT or expiring soon",
            "3. CREATIVITY: Think beyond obvious combinations - be inventive with flavors and cuisines",
            "4. PRACTICALITY: Suggest meals that can realistically be made with available products",
        ]

        # Add meal type filters if user has filtered
        if len(input_data.meal_types) < 4:
            meal_types_str = ", ".join(input_data.meal_types)
            requirements.append(f"5. MEAL TYPES: Only suggest meals suitable for: {meal_types_str}")

        # Add excluded ingredients if provided
        if input_data.excluded_ingredients:
            excluded_str = ", ".join(input_data.excluded_ingredients)
            requirements.append(f"6. EXCLUSIONS: Do NOT suggest meals containing: {excluded_str}")

        # Add user preferences if provided
        if input_data.user_preferences:
            requirements.append(f"7. USER PREFERENCE: {input_data.user_preferences}")

        requirements_text = "\n".join(requirements)

        # Build complete prompt
        return f"""{system_instruction}

Available products:
{products_text}

Task: Suggest {input_data.num_meals} diverse and creative meal ideas using these products.

Requirements:
{requirements_text}

Output format: Return a JSON object with the following structure:
{{
    "suggested_meals": ["Meal 1", "Meal 2", "Meal 3"],
    "reasoning": "Brief explanation of why these meals were suggested",
    "urgency_notes": "Notes about products expiring soon that should be used first"
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
        return """You are a creative chef helping reduce food waste by suggesting meals using discounted products.

Your goals:
1. Suggest diverse, practical meals using available discounted products
2. Prioritize products expiring soon to reduce food waste
3. Respect dietary preferences and restrictions
4. Be creative with flavor combinations and cuisines
5. Ensure meals are realistic and achievable for home cooks
6. Consider different meal types (breakfast, lunch, dinner, snacks)

Your suggestions should be:
- Creative but practical
- Culturally diverse (Danish, Italian, Mexican, Asian, etc.)
- Appropriate for the meal type
- Achievable with common kitchen equipment
- Family-friendly when possible"""

    def _format_products(self, input_data: MealSuggestionInput) -> str:
        """
        Format product list with expiration urgency markers.

        Args:
            input_data: Input data with products and optional details

        Returns:
            Formatted product list string
        """
        # Limit products to avoid token overflow
        max_products = 20
        products_sample = input_data.available_products[:max_products]

        # Build detailed product list with expiration info if available
        if input_data.product_details:
            product_lines = []
            today = get_today()

            for detail in input_data.product_details[:max_products]:
                product_name = detail.get("name", "")
                expiration = detail.get("expiration_date")
                discount_percent = detail.get("discount_percent", 0)

                # Calculate days until expiration
                urgency_marker = ""
                if expiration:
                    if isinstance(expiration, str):
                        with contextlib.suppress(ValueError, TypeError):
                            expiration = date.fromisoformat(expiration)

                    if isinstance(expiration, date):
                        days_until_expiry = (expiration - today).days
                        if days_until_expiry <= 2:
                            urgency_marker = f" [URGENT - expires in {days_until_expiry} days]"
                        elif days_until_expiry <= 5:
                            urgency_marker = f" [expires soon - {days_until_expiry} days]"

                product_line = f"- {product_name}"
                if discount_percent > 0:
                    product_line += f" ({int(discount_percent)}% off)"
                product_line += urgency_marker
                product_lines.append(product_line)

            return "\n".join(product_lines)
        return "\n".join([f"- {p}" for p in products_sample])

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
        self, response_text: str, input_data: MealSuggestionInput
    ) -> MealSuggestionOutput:
        """
        Parse Gemini response into structured output.

        Attempts to parse JSON response first, falls back to text parsing.

        Args:
            response_text: Raw text response from Gemini
            input_data: Original input data for context

        Returns:
            Structured MealSuggestionOutput
        """
        import json

        # Try to parse as JSON first
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

            # Handle different response formats
            suggested_meals = data.get("suggested_meals", [])

            # If suggested_meals contains dicts, extract meal names
            if suggested_meals and isinstance(suggested_meals[0], dict):
                # Try different keys for meal names
                meal_names = []
                for meal_obj in suggested_meals:
                    if isinstance(meal_obj, dict):
                        # Try common keys
                        meal_name = (
                            meal_obj.get("meal")
                            or meal_obj.get("meal_name")
                            or meal_obj.get("name")
                            or str(meal_obj)
                        )
                        meal_names.append(meal_name)
                    else:
                        meal_names.append(str(meal_obj))
                suggested_meals = meal_names

            # Validate and create output
            return MealSuggestionOutput(
                suggested_meals=suggested_meals[: input_data.num_meals],
                reasoning=data.get("reasoning", "Meals suggested based on available products"),
                urgency_notes=data.get("urgency_notes", ""),
            )

        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            logger.warning("json_parsing_failed_falling_back_to_text_parsing", error=str(e))

            # Fallback to text parsing
            meals = []
            lines = response_text.strip().split("\n")

            for line in lines:
                # Remove numbering, bullets, and extra whitespace
                meal = line.strip()
                meal = meal.lstrip("0123456789.-*• ")
                meal = meal.strip()

                # Skip empty lines, very short responses, and JSON artifacts
                if meal and len(meal) > 2 and not meal.startswith("{") and not meal.startswith("["):
                    meals.append(meal)

            return MealSuggestionOutput(
                suggested_meals=meals[: input_data.num_meals],
                reasoning="Meals suggested based on available products",
                urgency_notes="",
            )

    def _fallback_suggestions(self, input_data: MealSuggestionInput) -> MealSuggestionOutput:
        """
        Provide fallback meal suggestions if Gemini fails.

        Uses simple rule-based logic to suggest meals based on
        common product patterns.

        Args:
            input_data: Original input data

        Returns:
            Structured output with fallback suggestions

        Requirements: 4.2
        """
        logger.info("generating_fallback_suggestions")

        fallback_meals = []
        products_lower = [p.lower() for p in input_data.available_products]

        # Check for common meal patterns
        if any("tortilla" in p or "hakket" in p for p in products_lower):
            fallback_meals.append("Taco")

        if any("pasta" in p for p in products_lower):
            fallback_meals.append("Pasta Bolognese")

        if any("grøntsag" in p or "gulerod" in p or "kartof" in p for p in products_lower):
            fallback_meals.append("Grøntsagssuppe")

        if any("brød" in p or "bread" in p for p in products_lower):
            fallback_meals.append("Sandwich")

        if any("ris" in p or "rice" in p for p in products_lower):
            fallback_meals.append("Stir-fry")

        # Pad with generic suggestions if needed
        generic = ["Salat", "Wrap", "Omelet", "Suppe", "Grillret"]
        fallback_meals.extend(generic)

        return MealSuggestionOutput(
            suggested_meals=fallback_meals[: input_data.num_meals],
            reasoning="Fallback suggestions based on available products (AI service unavailable)",
            urgency_notes="",
        )

"""
OutputFormatter ADK Agent - AI-powered output formatting using Google ADK.

This module implements the OutputFormatter as a proper Google ADK agent with:
- Typed tool functions using Pydantic models
- Gemini-powered tip generation and motivation messages
- Structured logging with agent context
- Professional, user-friendly output formatting
- Personalized recommendations based on shopping context

Requirements: 2.1, 2.3, 3.1, 3.3
"""

from decimal import Decimal
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from agents.discount_optimizer.config import settings
from agents.discount_optimizer.domain.models import Purchase, ShoppingRecommendation
from agents.discount_optimizer.logging import get_logger, set_agent_context


# Get logger for this module
logger = get_logger(__name__)


class FormattingInput(BaseModel):
    """
    Input model for output formatting tool.

    Attributes:
        purchases: List of recommended purchases
        total_savings: Total amount saved across all purchases
        time_savings: Estimated time saved in minutes
        stores: List of stores to visit with details
        user_context: Optional context about user preferences or situation
        num_tips: Number of tips to generate (1-10)

    Example:
        >>> input_data = FormattingInput(
        ...     purchases=[...],
        ...     total_savings=Decimal("50.00"),
        ...     time_savings=15.0,
        ...     stores=[{"name": "Føtex", "address": "..."}],
        ...     user_context="Family of 4, busy weeknights",
        ...     num_tips=5,
        ... )
    """

    purchases: list[Purchase] = Field(
        description="List of recommended purchases", min_length=0, max_length=100
    )
    total_savings: Decimal = Field(ge=0, description="Total amount saved across all purchases")
    time_savings: float = Field(ge=0, description="Estimated time saved in minutes")
    stores: list[dict[str, Any]] = Field(
        description="List of stores to visit with details", min_length=0, max_length=20
    )
    user_context: str = Field(
        default="",
        description="Optional context about user preferences or situation",
        max_length=500,
    )
    num_tips: int = Field(default=5, ge=1, le=10, description="Number of tips to generate")


class FormattingOutput(BaseModel):
    """
    Output model from output formatting tool.

    Attributes:
        tips: List of helpful, actionable shopping tips
        motivation_message: Personalized motivational message for the user
        formatted_recommendation: Complete formatted shopping recommendation

    Example:
        >>> output = FormattingOutput(
        ...     tips=["Shop early in the morning", "Bring reusable bags"],
        ...     motivation_message="Great job planning ahead!",
        ...     formatted_recommendation=ShoppingRecommendation(...),
        ... )
    """

    tips: list[str] = Field(
        description="List of helpful, actionable shopping tips", min_length=1, max_length=10
    )
    motivation_message: str = Field(
        description="Personalized motivational message", min_length=10, max_length=500
    )
    formatted_recommendation: ShoppingRecommendation = Field(
        description="Complete formatted shopping recommendation"
    )


class OutputFormatterAgent:
    """
    ADK agent for AI-powered output formatting.

    This agent uses Gemini to generate personalized tips and motivation messages
    that make the shopping experience more engaging and helpful. Unlike static
    templates, Gemini can:
    - Generate contextually relevant tips based on the shopping plan
    - Create personalized motivation messages
    - Adapt tone and content to user preferences
    - Provide creative, actionable advice

    The agent follows Google ADK best practices (November 2025):
    - Uses latest google.genai SDK
    - Implements typed tool functions
    - Validates inputs/outputs with Pydantic
    - Includes structured logging
    - Delegates creative content to AI

    Example:
        >>> agent = OutputFormatterAgent()
        >>> input_data = FormattingInput(
        ...     purchases=[...], total_savings=Decimal("50.00"), time_savings=15.0, stores=[...]
        ... )
        >>> output = await agent.run(input_data)
        >>> print(output.motivation_message)
        'Amazing! You're saving 50 kr while reducing food waste...'

    Requirements: 2.1, 2.3, 3.1, 3.3
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize OutputFormatter agent with Google ADK.

        Args:
            api_key: Optional Google API key. If None, uses settings.google_api_key

        Raises:
            ValueError: If API key is not provided and not in settings
        """
        # Set agent context for logging
        set_agent_context("output_formatter")

        # Get API key
        if api_key is None:
            api_key = settings.google_api_key.get_secret_value()

        if not api_key:
            raise ValueError("Google API key is required for OutputFormatterAgent")

        # Initialize Gemini client using latest google-genai SDK
        self.client = genai.Client(api_key=api_key)
        self.model = f"models/{settings.agent_model}"

        logger.info(
            "output_formatter_agent_initialized",
            model=settings.agent_model,
            temperature=settings.agent_temperature,
            max_tokens=settings.agent_max_tokens,
        )

    async def run(self, input_data: FormattingInput) -> FormattingOutput:
        """
        Run the output formatter agent with input data.

        This is the main entry point for the agent. It validates input,
        calls Gemini to generate tips and motivation, and returns structured
        output with a complete shopping recommendation.

        Args:
            input_data: Validated input data for output formatting

        Returns:
            Structured output with tips, motivation, and formatted recommendation

        Raises:
            ValueError: If input validation fails
            Exception: If Gemini API call fails after retries

        Requirements: 2.1, 2.3, 3.1, 3.3
        """
        logger.info(
            "output_formatting_started",
            num_purchases=len(input_data.purchases),
            total_savings=float(input_data.total_savings),
            time_savings=input_data.time_savings,
            num_stores=len(input_data.stores),
            has_user_context=bool(input_data.user_context),
        )

        try:
            # Format output using Gemini
            output = await self.format_output(input_data)

            logger.info(
                "output_formatting_completed",
                num_tips=len(output.tips),
                motivation_length=len(output.motivation_message),
            )

            return output

        except Exception as e:
            logger.exception("output_formatting_failed", error=str(e), error_type=type(e).__name__)

            # Fallback to rule-based formatting
            logger.warning("falling_back_to_rule_based_formatting")
            return self._fallback_formatting(input_data)

    async def format_output(self, input_data: FormattingInput) -> FormattingOutput:
        """
        Format output with AI-generated tips and motivation using Gemini.

        This tool uses Gemini to generate:
        - Contextually relevant shopping tips
        - Personalized motivation messages
        - Actionable advice based on the shopping plan

        Args:
            input_data: Validated input data for output formatting

        Returns:
            Structured output with tips, motivation, and formatted recommendation

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

    def _create_prompt(self, input_data: FormattingInput) -> str:
        """
        Create optimized prompt for Gemini output formatting.

        The prompt instructs Gemini to:
        - Generate helpful, actionable shopping tips
        - Create a personalized motivation message
        - Consider the shopping context and user preferences
        - Return structured JSON output

        Args:
            input_data: Validated input data

        Returns:
            Formatted prompt string for Gemini

        Requirements: 3.1, 3.3
        """
        # System instruction
        system_instruction = self._get_system_instruction()

        # Format shopping context
        context_text = self._format_shopping_context(input_data)

        # Build complete prompt
        return f"""{system_instruction}

Shopping Context:
{context_text}

Task: Generate {input_data.num_tips} helpful shopping tips and a motivational message.

Requirements:
1. TIPS: Provide practical, actionable advice specific to this shopping plan
2. RELEVANCE: Tips should be relevant to the stores, products, and savings
3. MOTIVATION: Create an encouraging message that celebrates the user's smart planning
4. TONE: Friendly, supportive, and enthusiastic
5. SPECIFICITY: Reference actual savings amounts and store details when relevant

Output format: Return a JSON object with this exact structure:
{{
    "tips": [
        "Tip 1: Specific actionable advice",
        "Tip 2: Another helpful tip",
        "Tip 3: More practical guidance"
    ],
    "motivation_message": "Encouraging message that celebrates the user's smart shopping choices"
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
        return """You are a friendly shopping assistant helping users make smart, sustainable shopping choices.

Your goals:
1. Provide practical, actionable shopping tips tailored to the user's plan
2. Create motivational messages that celebrate smart planning and savings
3. Encourage sustainable shopping habits (reducing waste, buying on discount)
4. Be specific and reference actual details (savings amounts, store names)
5. Maintain a warm, supportive, enthusiastic tone

Your tips should cover:
- Timing advice (best times to shop, when to use products)
- Store-specific guidance (parking, layout, special sections)
- Product handling (storage, preparation, freshness)
- Savings strategies (combining discounts, meal planning)
- Sustainability tips (reducing waste, reusable bags)

Your motivation messages should:
- Celebrate the user's smart planning
- Highlight specific achievements (savings amount, waste reduction)
- Encourage continued smart shopping habits
- Be genuine and enthusiastic without being over-the-top
- Reference specific details from their shopping plan"""

    def _format_shopping_context(self, input_data: FormattingInput) -> str:
        """
        Format shopping context for the prompt.

        Args:
            input_data: Input data with shopping details

        Returns:
            Formatted context string
        """
        lines = []

        # Savings information
        lines.append(f"Total Savings: {input_data.total_savings} kr")
        lines.append(f"Time Savings: {input_data.time_savings:.0f} minutes")

        # Store information
        if input_data.stores:
            store_names = [s.get("name", "Unknown") for s in input_data.stores]
            lines.append(f"Stores to Visit: {', '.join(store_names)}")

        # Purchase summary
        if input_data.purchases:
            lines.append(f"Number of Items: {len(input_data.purchases)}")

            # Group by meal
            meals = {p.meal_association for p in input_data.purchases if p.meal_association}
            if meals:
                lines.append(f"Meals Planned: {', '.join(sorted(meals))}")

        # User context
        if input_data.user_context:
            lines.append(f"User Context: {input_data.user_context}")

        return "\n".join(lines)

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

    def _parse_response(self, response_text: str, input_data: FormattingInput) -> FormattingOutput:
        """
        Parse Gemini response into structured output.

        Attempts to parse JSON response from Gemini and convert it to
        FormattingOutput with proper validation.

        Args:
            response_text: Raw text response from Gemini
            input_data: Original input data for context

        Returns:
            Structured FormattingOutput
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

            # Extract tips and motivation
            tips = data.get("tips", [])
            motivation_message = data.get("motivation_message", "")

            # Ensure we have the requested number of tips
            if len(tips) < input_data.num_tips:
                logger.warning(
                    "fewer_tips_than_requested", requested=input_data.num_tips, received=len(tips)
                )

            # Ensure tips are strings
            tips = [str(tip) for tip in tips if tip]

            # Create formatted recommendation
            formatted_recommendation = ShoppingRecommendation(
                purchases=input_data.purchases,
                total_savings=input_data.total_savings,
                time_savings=input_data.time_savings,
                tips=tips,
                motivation_message=motivation_message,
                stores=input_data.stores,
            )

            return FormattingOutput(
                tips=tips,
                motivation_message=motivation_message,
                formatted_recommendation=formatted_recommendation,
            )

        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            logger.warning("json_parsing_failed", error=str(e))
            raise ValueError(f"Failed to parse Gemini response: {e}")

    def _fallback_formatting(self, input_data: FormattingInput) -> FormattingOutput:
        """
        Provide fallback formatting if Gemini fails.

        Uses rule-based logic to generate basic tips and motivation.

        Args:
            input_data: Original input data

        Returns:
            FormattingOutput with fallback content

        Requirements: 4.2
        """
        logger.info("generating_fallback_formatting")

        # Generate rule-based tips
        tips = self._generate_fallback_tips(input_data)

        # Generate rule-based motivation
        motivation_message = self._generate_fallback_motivation(input_data)

        # Create formatted recommendation
        formatted_recommendation = ShoppingRecommendation(
            purchases=input_data.purchases,
            total_savings=input_data.total_savings,
            time_savings=input_data.time_savings,
            tips=tips,
            motivation_message=motivation_message,
            stores=input_data.stores,
        )

        return FormattingOutput(
            tips=tips,
            motivation_message=motivation_message,
            formatted_recommendation=formatted_recommendation,
        )

    def _generate_fallback_tips(self, input_data: FormattingInput) -> list[str]:
        """
        Generate rule-based tips as fallback.

        Args:
            input_data: Input data with shopping details

        Returns:
            List of generic but helpful tips
        """
        tips = []

        # Timing tip
        tips.append("Shop early in the morning for the freshest products and shortest lines")

        # Store tip
        if len(input_data.stores) > 1:
            tips.append(f"Plan your route to visit all {len(input_data.stores)} stores efficiently")

        # Savings tip
        if input_data.total_savings > 0:
            tips.append("Check expiration dates carefully on discounted items to ensure freshness")

        # Sustainability tip
        tips.append("Bring reusable bags to reduce plastic waste")

        # Product tip
        if input_data.purchases:
            tips.append("Store perishable items in the refrigerator immediately after shopping")

        # Meal planning tip
        tips.append("Prep ingredients in advance to save time during busy weeknights")

        # Budget tip
        tips.append("Keep track of your actual spending to compare with your planned budget")

        return tips[: input_data.num_tips]

    def _generate_fallback_motivation(self, input_data: FormattingInput) -> str:
        """
        Generate rule-based motivation message as fallback.

        Args:
            input_data: Input data with shopping details

        Returns:
            Generic but encouraging motivation message
        """
        savings_amount = float(input_data.total_savings)

        if savings_amount > 100:
            return f"Fantastic planning! You're saving {savings_amount:.0f} kr while reducing food waste. Keep up the smart shopping!"
        if savings_amount > 50:
            return f"Great job! You're saving {savings_amount:.0f} kr with this shopping plan. Smart choices lead to big savings!"
        if savings_amount > 0:
            return f"Nice work! Every krone saved counts, and you're saving {savings_amount:.0f} kr. Keep making smart choices!"
        return "Great job planning your meals! Smart shopping starts with good planning."

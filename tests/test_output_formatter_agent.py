"""
Unit tests for OutputFormatter ADK Agent.

Tests cover:
- Agent initialization
- Input/output model validation
- Tip generation logic
- Motivation message generation
- Fallback formatting
- Gemini API integration (mocked)

Requirements: 2.1, 2.3, 3.1, 3.3
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from agents.discount_optimizer.agents.output_formatter_agent import (
    FormattingInput,
    FormattingOutput,
    OutputFormatterAgent,
)
from agents.discount_optimizer.domain.models import Purchase, ShoppingRecommendation


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_gemini_json_response() -> str:
    """Fixture providing a valid JSON response from Gemini."""
    return """{
    "tips": [
        "Shop early in the morning for the freshest products",
        "Check expiration dates carefully on discounted items",
        "Bring reusable bags to reduce plastic waste",
        "Store perishable items in the refrigerator immediately",
        "Plan your route to visit all stores efficiently"
    ],
    "motivation_message": "Amazing! You're saving 31 kr while reducing food waste. Keep up the smart shopping!"
}"""


@pytest.fixture
def mock_gemini_invalid_json_response() -> str:
    """Fixture providing an invalid JSON response from Gemini."""
    return """This is not valid JSON at all!
    Just some random text that will fail parsing."""


@pytest.fixture
def sample_purchases() -> list[Purchase]:
    """Create sample purchases for testing."""
    today = date.today()

    return [
        Purchase(
            product_name="Tortillas 8 stk",
            store_name="Føtex",
            purchase_day=today,
            price=Decimal("14.95"),
            savings=Decimal("10.00"),
            meal_association="Taco Tuesday",
        ),
        Purchase(
            product_name="Hakket oksekød 8-12%",
            store_name="Føtex",
            purchase_day=today,
            price=Decimal("35.00"),
            savings=Decimal("15.00"),
            meal_association="Taco Tuesday",
        ),
        Purchase(
            product_name="Pasta 500g",
            store_name="Netto",
            purchase_day=today + timedelta(days=1),
            price=Decimal("12.00"),
            savings=Decimal("6.00"),
            meal_association="Pasta Carbonara",
        ),
    ]


@pytest.fixture
def sample_stores() -> list[dict]:
    """Create sample store data for testing."""
    return [
        {
            "name": "Føtex",
            "address": "Nørrebrogade 123, Copenhagen",
            "distance_km": 1.2,
            "travel_time_minutes": 5.0,
        },
        {
            "name": "Netto",
            "address": "Vesterbrogade 456, Copenhagen",
            "distance_km": 2.5,
            "travel_time_minutes": 10.0,
        },
    ]


@pytest.fixture
def formatting_input(sample_purchases, sample_stores) -> FormattingInput:
    """Create sample formatting input."""
    return FormattingInput(
        purchases=sample_purchases,
        total_savings=Decimal("31.00"),
        time_savings=15.0,
        stores=sample_stores,
        user_context="Family of 4, busy weeknights",
        num_tips=5,
    )


# ============================================================================
# Input/Output Model Validation Tests
# ============================================================================


def test_input_validation_valid(sample_purchases, sample_stores):
    """Test that valid input is accepted."""
    input_data = FormattingInput(
        purchases=sample_purchases,
        total_savings=Decimal("31.00"),
        time_savings=15.0,
        stores=sample_stores,
        num_tips=5,
    )

    assert len(input_data.purchases) == 3
    assert input_data.total_savings == Decimal("31.00")
    assert input_data.time_savings == 15.0
    assert len(input_data.stores) == 2
    assert input_data.num_tips == 5


def test_input_validation_empty_purchases():
    """Test that empty purchases list is accepted."""
    input_data = FormattingInput(
        purchases=[], total_savings=Decimal("0.00"), time_savings=0.0, stores=[], num_tips=3
    )

    assert len(input_data.purchases) == 0
    assert input_data.total_savings == Decimal("0.00")


def test_input_validation_negative_savings():
    """Test that negative savings is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        FormattingInput(
            purchases=[], total_savings=Decimal("-10.00"), time_savings=0.0, stores=[], num_tips=3
        )


def test_input_validation_invalid_num_tips():
    """Test that invalid num_tips is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        FormattingInput(
            purchases=[],
            total_savings=Decimal("0.00"),
            time_savings=0.0,
            stores=[],
            num_tips=0,  # Must be >= 1
        )


def test_output_validation_valid(sample_purchases, sample_stores):
    """Test that valid output is accepted."""
    output = FormattingOutput(
        tips=["Tip 1", "Tip 2", "Tip 3"],
        motivation_message="Great job planning ahead!",
        formatted_recommendation=ShoppingRecommendation(
            purchases=sample_purchases,
            total_savings=Decimal("31.00"),
            time_savings=15.0,
            tips=["Tip 1", "Tip 2", "Tip 3"],
            motivation_message="Great job planning ahead!",
            stores=sample_stores,
        ),
    )

    assert len(output.tips) == 3
    assert len(output.motivation_message) >= 10
    assert isinstance(output.formatted_recommendation, ShoppingRecommendation)


def test_output_validation_empty_tips():
    """Test that empty tips list is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        FormattingOutput(
            tips=[],  # Must have at least 1 tip
            motivation_message="Great job!",
            formatted_recommendation=ShoppingRecommendation(
                purchases=[],
                total_savings=Decimal("0.00"),
                time_savings=0.0,
                tips=[],
                motivation_message="Great job!",
                stores=[],
            ),
        )


def test_output_validation_short_motivation():
    """Test that short motivation message is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        FormattingOutput(
            tips=["Tip 1"],
            motivation_message="Hi",  # Too short (< 10 chars)
            formatted_recommendation=ShoppingRecommendation(
                purchases=[],
                total_savings=Decimal("0.00"),
                time_savings=0.0,
                tips=["Tip 1"],
                motivation_message="Hi",
                stores=[],
            ),
        )


# ============================================================================
# Fallback Formatting Tests
# ============================================================================


def test_fallback_tips_generation(formatting_input):
    """Test rule-based tip generation as fallback."""
    agent = OutputFormatterAgent()

    tips = agent._generate_fallback_tips(formatting_input)

    assert isinstance(tips, list)
    assert len(tips) <= formatting_input.num_tips
    assert all(isinstance(tip, str) for tip in tips)
    assert all(len(tip) > 10 for tip in tips)  # Tips should be meaningful


def test_fallback_motivation_high_savings():
    """Test motivation message for high savings."""
    agent = OutputFormatterAgent()

    input_data = FormattingInput(
        purchases=[], total_savings=Decimal("150.00"), time_savings=0.0, stores=[], num_tips=3
    )

    motivation = agent._generate_fallback_motivation(input_data)

    assert isinstance(motivation, str)
    assert len(motivation) > 10
    assert "150" in motivation or "saving" in motivation.lower()


def test_fallback_motivation_medium_savings():
    """Test motivation message for medium savings."""
    agent = OutputFormatterAgent()

    input_data = FormattingInput(
        purchases=[], total_savings=Decimal("75.00"), time_savings=0.0, stores=[], num_tips=3
    )

    motivation = agent._generate_fallback_motivation(input_data)

    assert isinstance(motivation, str)
    assert len(motivation) > 10


def test_fallback_motivation_low_savings():
    """Test motivation message for low savings."""
    agent = OutputFormatterAgent()

    input_data = FormattingInput(
        purchases=[], total_savings=Decimal("25.00"), time_savings=0.0, stores=[], num_tips=3
    )

    motivation = agent._generate_fallback_motivation(input_data)

    assert isinstance(motivation, str)
    assert len(motivation) > 10


def test_fallback_formatting_complete(formatting_input):
    """Test complete fallback formatting."""
    agent = OutputFormatterAgent()

    output = agent._fallback_formatting(formatting_input)

    assert isinstance(output, FormattingOutput)
    assert len(output.tips) > 0
    assert len(output.motivation_message) >= 10
    assert isinstance(output.formatted_recommendation, ShoppingRecommendation)
    assert output.formatted_recommendation.total_savings == formatting_input.total_savings


# ============================================================================
# Agent Initialization Tests
# ============================================================================


def test_agent_initialization_with_api_key():
    """Test agent initialization with explicit API key."""
    agent = OutputFormatterAgent(api_key="test-api-key")

    assert agent.client is not None
    assert agent.model.startswith("models/")


def test_agent_initialization_without_api_key():
    """Test agent initialization without API key (uses settings)."""
    # This will use the API key from settings/environment
    agent = OutputFormatterAgent()

    assert agent.client is not None
    assert agent.model.startswith("models/")


# ============================================================================
# Helper Method Tests
# ============================================================================


def test_format_shopping_context(formatting_input):
    """Test shopping context formatting for prompt."""
    agent = OutputFormatterAgent()

    context = agent._format_shopping_context(formatting_input)

    assert isinstance(context, str)
    assert "31" in context  # Total savings
    assert "15" in context  # Time savings
    assert "Føtex" in context or "Netto" in context  # Store names
    assert "Taco Tuesday" in context or "Pasta Carbonara" in context  # Meals


def test_format_shopping_context_empty():
    """Test shopping context formatting with empty data."""
    agent = OutputFormatterAgent()

    input_data = FormattingInput(
        purchases=[], total_savings=Decimal("0.00"), time_savings=0.0, stores=[], num_tips=3
    )

    context = agent._format_shopping_context(input_data)

    assert isinstance(context, str)
    assert "0" in context  # Should show zero savings


def test_create_prompt(formatting_input):
    """Test prompt creation for Gemini."""
    agent = OutputFormatterAgent()

    prompt = agent._create_prompt(formatting_input)

    assert isinstance(prompt, str)
    assert len(prompt) > 100  # Should be substantial
    assert "tips" in prompt.lower()
    assert "motivation" in prompt.lower()
    assert str(formatting_input.num_tips) in prompt


def test_system_instruction():
    """Test system instruction content."""
    agent = OutputFormatterAgent()

    instruction = agent._get_system_instruction()

    assert isinstance(instruction, str)
    assert len(instruction) > 50
    assert "shopping" in instruction.lower()
    assert "tips" in instruction.lower()


# ============================================================================
# CRITICAL: Happy Path Tests (AI Integration)
# ============================================================================


@pytest.mark.asyncio
async def test_format_output_parses_valid_json(
    monkeypatch, formatting_input: FormattingInput, mock_gemini_json_response: str
):
    """Test that agent correctly parses valid JSON response from Gemini (HAPPY PATH)."""
    # Mock the Gemini API response
    mock_response = MagicMock()
    mock_response.text = mock_gemini_json_response
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_gemini_json_response

    # Patch the client's generate_content method
    agent = OutputFormatterAgent(api_key="test_key")
    monkeypatch.setattr(agent.client.models, "generate_content", lambda **kwargs: mock_response)

    # Act
    output = await agent.format_output(formatting_input)

    # Assert
    assert isinstance(output, FormattingOutput)
    assert len(output.tips) == 5
    assert output.tips[0] == "Shop early in the morning for the freshest products"
    assert output.tips[1] == "Check expiration dates carefully on discounted items"
    assert "Amazing! You're saving 31 kr" in output.motivation_message
    assert isinstance(output.formatted_recommendation, ShoppingRecommendation)
    assert output.formatted_recommendation.total_savings == formatting_input.total_savings


@pytest.mark.asyncio
async def test_run_agent_parses_valid_json(
    monkeypatch, formatting_input: FormattingInput, mock_gemini_json_response: str
):
    """Test that agent.run() correctly parses valid JSON response from Gemini (HAPPY PATH)."""
    # Mock the Gemini API response
    mock_response = MagicMock()
    mock_response.text = mock_gemini_json_response
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_gemini_json_response

    # Patch the client's generate_content method
    agent = OutputFormatterAgent(api_key="test_key")
    monkeypatch.setattr(agent.client.models, "generate_content", lambda **kwargs: mock_response)

    # Act
    output = await agent.run(formatting_input)

    # Assert
    assert isinstance(output, FormattingOutput)
    assert len(output.tips) == 5
    assert "Shop early in the morning" in output.tips[0]
    assert "31 kr" in output.motivation_message
    assert output.formatted_recommendation.purchases == formatting_input.purchases


@pytest.mark.asyncio
async def test_format_output_parses_json_with_markdown(
    monkeypatch, formatting_input: FormattingInput
):
    """Test that agent handles JSON wrapped in markdown code blocks."""
    # Mock response with markdown code blocks
    mock_response_text = """```json
{
    "tips": [
        "Test tip 1",
        "Test tip 2",
        "Test tip 3"
    ],
    "motivation_message": "Test motivation message for markdown parsing"
}
```"""

    mock_response = MagicMock()
    mock_response.text = mock_response_text
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_response_text

    # Patch the client's generate_content method
    agent = OutputFormatterAgent(api_key="test_key")
    monkeypatch.setattr(agent.client.models, "generate_content", lambda **kwargs: mock_response)

    # Act
    output = await agent.format_output(formatting_input)

    # Assert
    assert isinstance(output, FormattingOutput)
    assert len(output.tips) == 3
    assert output.tips[0] == "Test tip 1"
    assert output.motivation_message == "Test motivation message for markdown parsing"


@pytest.mark.asyncio
async def test_format_output_invalid_json_triggers_fallback(
    monkeypatch, formatting_input: FormattingInput, mock_gemini_invalid_json_response: str
):
    """Test that invalid JSON response triggers fallback logic."""
    # Mock the Gemini API response with invalid JSON
    mock_response = MagicMock()
    mock_response.text = mock_gemini_invalid_json_response
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_gemini_invalid_json_response

    # Patch the client's generate_content method
    agent = OutputFormatterAgent(api_key="test_key")
    monkeypatch.setattr(agent.client.models, "generate_content", lambda **kwargs: mock_response)

    # Act - should raise ValueError which triggers fallback in run()
    with pytest.raises(ValueError, match="Failed to parse Gemini response"):
        await agent.format_output(formatting_input)


@pytest.mark.asyncio
async def test_run_agent_invalid_json_triggers_fallback(
    monkeypatch, formatting_input: FormattingInput, mock_gemini_invalid_json_response: str
):
    """Test that agent.run() falls back gracefully when JSON parsing fails."""
    # Mock the Gemini API response with invalid JSON
    mock_response = MagicMock()
    mock_response.text = mock_gemini_invalid_json_response
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_gemini_invalid_json_response

    # Patch the client's generate_content method
    agent = OutputFormatterAgent(api_key="test_key")
    monkeypatch.setattr(agent.client.models, "generate_content", lambda **kwargs: mock_response)

    # Act - run() should catch the error and use fallback
    output = await agent.run(formatting_input)

    # Assert - should get fallback output
    assert isinstance(output, FormattingOutput)
    assert len(output.tips) > 0
    assert len(output.motivation_message) >= 10
    # Fallback should still have correct savings
    assert output.formatted_recommendation.total_savings == formatting_input.total_savings


@pytest.mark.asyncio
async def test_format_output_fewer_tips_than_requested(
    monkeypatch, formatting_input: FormattingInput
):
    """Test that agent handles response with fewer tips than requested."""
    # Mock response with only 2 tips (requested 5)
    mock_response_text = """{
    "tips": [
        "Tip 1",
        "Tip 2"
    ],
    "motivation_message": "Good job planning ahead!"
}"""

    mock_response = MagicMock()
    mock_response.text = mock_response_text
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_response_text

    # Patch the client's generate_content method
    agent = OutputFormatterAgent(api_key="test_key")
    monkeypatch.setattr(agent.client.models, "generate_content", lambda **kwargs: mock_response)

    # Act
    output = await agent.format_output(formatting_input)

    # Assert - should accept fewer tips
    assert isinstance(output, FormattingOutput)
    assert len(output.tips) == 2
    assert output.tips[0] == "Tip 1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

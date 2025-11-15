"""
Unit tests for MealSuggesterAgent with mocked Gemini responses.

This test suite verifies the agent implementation without making real
API calls. All Gemini responses are mocked using pytest-mock.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date, timedelta

from agents.discount_optimizer.agents.meal_suggester_agent import (
    MealSuggesterAgent,
    MealSuggestionInput,
    MealSuggestionOutput,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_gemini_json_response() -> str:
    """Fixture providing a valid JSON response from Gemini."""
    return """{
    "suggested_meals": [
        "Breakfast Quesadillas with Spicy Ground Beef",
        "Lunchtime Taco Salad Bowls",
        "Ground Beef Tortilla Pinwheels"
    ],
    "reasoning": "These meals prioritize products expiring soon and offer diverse meal types.",
    "urgency_notes": "Use tortillas and ground beef first (expire in 1 day)"
}"""


@pytest.fixture
def mock_gemini_dict_response() -> str:
    """Fixture providing a response with meal objects (dict format)."""
    return """{
    "suggested_meals": [
        {"meal": "Taco Tuesday", "ingredients": ["tortillas", "beef", "cheese"]},
        {"meal_name": "Pasta Carbonara", "ingredients": ["pasta", "cheese"]},
        {"name": "Grøntsagssuppe", "ingredients": ["vegetables"]}
    ],
    "reasoning": "Meals use available products efficiently",
    "urgency_notes": ""
}"""


@pytest.fixture
def mock_gemini_text_response() -> str:
    """Fixture providing a plain text response (fallback parsing)."""
    return """1. Breakfast Burrito
2. Taco Salad
3. Quesadillas"""


@pytest.fixture
def basic_input() -> MealSuggestionInput:
    """Fixture providing basic input data."""
    return MealSuggestionInput(
        available_products=["tortillas", "hakket oksekød", "ost", "salat"],
        num_meals=3,
        user_preferences="quick and easy meals"
    )


@pytest.fixture
def input_with_urgency() -> MealSuggestionInput:
    """Fixture providing input with expiration urgency."""
    today = date.today()
    return MealSuggestionInput(
        available_products=["tortillas", "hakket oksekød", "ost"],
        num_meals=2,
        product_details=[
            {
                "name": "tortillas",
                "expiration_date": (today + timedelta(days=1)).isoformat(),
                "discount_percent": 30
            },
            {
                "name": "hakket oksekød",
                "expiration_date": (today + timedelta(days=1)).isoformat(),
                "discount_percent": 25
            },
            {
                "name": "ost",
                "expiration_date": (today + timedelta(days=7)).isoformat(),
                "discount_percent": 20
            }
        ]
    )


# ============================================================================
# Test: Agent Initialization
# ============================================================================

def test_agent_initialization_with_api_key():
    """Test that agent initializes correctly with explicit API key."""
    agent = MealSuggesterAgent(api_key="test_api_key_123")
    
    assert agent.client is not None
    assert "gemini" in agent.model.lower()


def test_agent_initialization_without_api_key_raises_error(monkeypatch):
    """Test that agent raises ValueError when no API key is provided."""
    # Patch settings to return None for API key
    from agents.discount_optimizer import config
    
    # Create a mock SecretStr that returns None
    mock_secret = MagicMock()
    mock_secret.get_secret_value.return_value = None
    
    monkeypatch.setattr(config.settings, "google_api_key", mock_secret)
    
    with pytest.raises(ValueError, match="Google API key is required"):
        MealSuggesterAgent()


# ============================================================================
# Test: Input Validation
# ============================================================================

def test_input_validation_valid():
    """Test that valid input is accepted."""
    input_data = MealSuggestionInput(
        available_products=["product1", "product2"],
        num_meals=5
    )
    
    assert len(input_data.available_products) == 2
    assert input_data.num_meals == 5


def test_input_validation_num_meals_too_high():
    """Test that num_meals > 10 is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        MealSuggestionInput(
            available_products=["product1"],
            num_meals=15  # Max is 10
        )


def test_input_validation_empty_products():
    """Test that empty products list is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        MealSuggestionInput(
            available_products=[],  # Min length is 1
            num_meals=3
        )


def test_input_validation_num_meals_zero():
    """Test that num_meals = 0 is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        MealSuggestionInput(
            available_products=["product1"],
            num_meals=0  # Min is 1
        )


# ============================================================================
# Test: Output Validation
# ============================================================================

def test_output_validation_valid():
    """Test that valid output is accepted."""
    output = MealSuggestionOutput(
        suggested_meals=["Taco", "Pasta", "Salad"],
        reasoning="These meals use available products efficiently",
        urgency_notes="Use tortillas first"
    )
    
    assert len(output.suggested_meals) == 3
    assert output.reasoning != ""


def test_output_validation_empty_meals():
    """Test that empty meals list is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        MealSuggestionOutput(
            suggested_meals=[],  # Min length is 1
            reasoning="No meals"
        )


# ============================================================================
# Test: JSON Parsing (Valid JSON)
# ============================================================================

@pytest.mark.asyncio
async def test_suggest_meals_parses_valid_json(
    monkeypatch,
    basic_input: MealSuggestionInput,
    mock_gemini_json_response: str
):
    """Test that agent correctly parses valid JSON response from Gemini."""
    # Mock the Gemini API response
    mock_response = MagicMock()
    mock_response.text = mock_gemini_json_response
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_gemini_json_response
    
    # Patch the client's generate_content method
    agent = MealSuggesterAgent(api_key="test_key")
    monkeypatch.setattr(
        agent.client.models,
        'generate_content',
        lambda **kwargs: mock_response
    )
    
    # Act
    output = await agent.suggest_meals(basic_input)
    
    # Assert
    assert isinstance(output, MealSuggestionOutput)
    assert len(output.suggested_meals) == 3
    assert output.suggested_meals[0] == "Breakfast Quesadillas with Spicy Ground Beef"
    assert output.suggested_meals[1] == "Lunchtime Taco Salad Bowls"
    assert output.suggested_meals[2] == "Ground Beef Tortilla Pinwheels"
    assert "prioritize products expiring soon" in output.reasoning
    assert "tortillas and ground beef first" in output.urgency_notes


# ============================================================================
# Test: JSON Parsing (Dict Format)
# ============================================================================

@pytest.mark.asyncio
async def test_suggest_meals_parses_dict_format(
    monkeypatch,
    basic_input: MealSuggestionInput,
    mock_gemini_dict_response: str
):
    """Test that agent handles meal objects (dict format) in response."""
    # Mock the Gemini API response
    mock_response = MagicMock()
    mock_response.text = mock_gemini_dict_response
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_gemini_dict_response
    
    # Patch the client's generate_content method
    agent = MealSuggesterAgent(api_key="test_key")
    monkeypatch.setattr(
        agent.client.models,
        'generate_content',
        lambda **kwargs: mock_response
    )
    
    # Act
    output = await agent.suggest_meals(basic_input)
    
    # Assert
    assert isinstance(output, MealSuggestionOutput)
    assert len(output.suggested_meals) == 3
    # Should extract meal names from different dict keys
    assert output.suggested_meals[0] == "Taco Tuesday"
    assert output.suggested_meals[1] == "Pasta Carbonara"
    assert output.suggested_meals[2] == "Grøntsagssuppe"


# ============================================================================
# Test: Text Parsing (Fallback)
# ============================================================================

@pytest.mark.asyncio
async def test_suggest_meals_fallback_text_parsing(
    monkeypatch,
    basic_input: MealSuggestionInput,
    mock_gemini_text_response: str
):
    """Test that agent falls back to text parsing when JSON parsing fails."""
    # Mock the Gemini API response (plain text, not JSON)
    mock_response = MagicMock()
    mock_response.text = mock_gemini_text_response
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_gemini_text_response
    
    # Patch the client's generate_content method
    agent = MealSuggesterAgent(api_key="test_key")
    monkeypatch.setattr(
        agent.client.models,
        'generate_content',
        lambda **kwargs: mock_response
    )
    
    # Act
    output = await agent.suggest_meals(basic_input)
    
    # Assert
    assert isinstance(output, MealSuggestionOutput)
    assert len(output.suggested_meals) == 3
    assert "Breakfast Burrito" in output.suggested_meals
    assert "Taco Salad" in output.suggested_meals
    assert "Quesadillas" in output.suggested_meals


# ============================================================================
# Test: Expiration Urgency Formatting
# ============================================================================

@pytest.mark.asyncio
async def test_format_products_with_urgency(
    monkeypatch,
    input_with_urgency: MealSuggestionInput,
    mock_gemini_json_response: str
):
    """Test that products with expiration dates are formatted with urgency markers."""
    # Mock the Gemini API response
    mock_response = MagicMock()
    mock_response.text = mock_gemini_json_response
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_gemini_json_response
    
    # Capture the prompt
    captured_prompt = {}
    
    def mock_generate(**kwargs):
        captured_prompt['contents'] = kwargs.get('contents', '')
        return mock_response
    
    # Patch the client's generate_content method
    agent = MealSuggesterAgent(api_key="test_key")
    monkeypatch.setattr(
        agent.client.models,
        'generate_content',
        mock_generate
    )
    
    # Act
    await agent.suggest_meals(input_with_urgency)
    
    # Assert - check that the prompt contains urgency markers
    prompt = captured_prompt['contents']
    
    assert "[URGENT - expires in 1 days]" in prompt or "[URGENT - expires in 1 day]" in prompt
    assert "30% off" in prompt
    assert "25% off" in prompt


# ============================================================================
# Test: Fallback Suggestions
# ============================================================================

@pytest.mark.asyncio
async def test_fallback_suggestions_on_api_error(
    monkeypatch,
    basic_input: MealSuggestionInput
):
    """Test that agent provides fallback suggestions when Gemini API fails."""
    # Mock the Gemini API to raise an exception
    def mock_generate_error(**kwargs):
        raise Exception("API Error")
    
    agent = MealSuggesterAgent(api_key="test_key")
    monkeypatch.setattr(
        agent.client.models,
        'generate_content',
        mock_generate_error
    )
    
    # Act
    output = await agent.run(basic_input)
    
    # Assert - should get fallback suggestions
    assert isinstance(output, MealSuggestionOutput)
    assert len(output.suggested_meals) > 0
    assert "fallback" in output.reasoning.lower() or "unavailable" in output.reasoning.lower()


@pytest.mark.asyncio
async def test_fallback_suggestions_contain_relevant_meals():
    """Test that fallback suggestions are relevant to available products."""
    agent = MealSuggesterAgent(api_key="test_key")
    
    # Test with tortilla products
    input_tortilla = MealSuggestionInput(
        available_products=["tortillas", "hakket oksekød"],
        num_meals=3
    )
    output = agent._fallback_suggestions(input_tortilla)
    
    assert "Taco" in output.suggested_meals
    
    # Test with pasta products
    input_pasta = MealSuggestionInput(
        available_products=["pasta", "tomatsauce"],
        num_meals=3
    )
    output = agent._fallback_suggestions(input_pasta)
    
    assert "Pasta Bolognese" in output.suggested_meals


# ============================================================================
# Test: Dietary Restrictions
# ============================================================================

@pytest.mark.asyncio
async def test_dietary_restrictions_in_prompt(
    monkeypatch,
    mock_gemini_json_response: str
):
    """Test that dietary restrictions are included in the prompt."""
    # Create input with dietary restrictions
    input_data = MealSuggestionInput(
        available_products=["pasta", "tomatsauce", "ost"],
        num_meals=2,
        excluded_ingredients=["kylling", "fisk"],
        user_preferences="vegetarian meals"
    )
    
    # Mock the Gemini API response
    mock_response = MagicMock()
    mock_response.text = mock_gemini_json_response
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_gemini_json_response
    
    # Capture the prompt
    captured_prompt = {}
    
    def mock_generate(**kwargs):
        captured_prompt['contents'] = kwargs.get('contents', '')
        return mock_response
    
    # Patch the client's generate_content method
    agent = MealSuggesterAgent(api_key="test_key")
    monkeypatch.setattr(
        agent.client.models,
        'generate_content',
        mock_generate
    )
    
    # Act
    await agent.suggest_meals(input_data)
    
    # Assert - check that the prompt contains dietary restrictions
    prompt = captured_prompt['contents']
    
    assert "kylling" in prompt
    assert "fisk" in prompt
    assert "vegetarian meals" in prompt


# ============================================================================
# Test: Meal Type Filtering
# ============================================================================

@pytest.mark.asyncio
async def test_meal_type_filtering_in_prompt(
    monkeypatch,
    mock_gemini_json_response: str
):
    """Test that meal type filters are included in the prompt."""
    # Create input with specific meal types
    input_data = MealSuggestionInput(
        available_products=["pasta", "tomatsauce"],
        num_meals=2,
        meal_types=["lunch", "dinner"]  # Only lunch and dinner
    )
    
    # Mock the Gemini API response
    mock_response = MagicMock()
    mock_response.text = mock_gemini_json_response
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_gemini_json_response
    
    # Capture the prompt
    captured_prompt = {}
    
    def mock_generate(**kwargs):
        captured_prompt['contents'] = kwargs.get('contents', '')
        return mock_response
    
    # Patch the client's generate_content method
    agent = MealSuggesterAgent(api_key="test_key")
    monkeypatch.setattr(
        agent.client.models,
        'generate_content',
        mock_generate
    )
    
    # Act
    await agent.suggest_meals(input_data)
    
    # Assert - check that the prompt contains meal type filter
    prompt = captured_prompt['contents']
    
    assert "lunch, dinner" in prompt or ("lunch" in prompt and "dinner" in prompt)


# ============================================================================
# Test: System Instruction
# ============================================================================

def test_system_instruction_content():
    """Test that system instruction contains key elements."""
    agent = MealSuggesterAgent(api_key="test_key")
    system_instruction = agent._get_system_instruction()
    
    assert "creative chef" in system_instruction.lower()
    assert "reduce food waste" in system_instruction.lower()
    assert "expiring soon" in system_instruction.lower()
    assert "dietary" in system_instruction.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

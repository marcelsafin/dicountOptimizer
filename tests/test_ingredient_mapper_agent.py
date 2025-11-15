"""
Unit tests for IngredientMapperAgent with mocked Gemini responses.

This test suite verifies the agent implementation without making real
API calls. All Gemini responses are mocked using pytest-mock.
"""

import pytest
from unittest.mock import MagicMock

from agents.discount_optimizer.agents.ingredient_mapper_agent import (
    IngredientMapperAgent,
    IngredientMappingInput,
    IngredientMappingOutput,
    IngredientMapping,
    ProductMatch,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_products() -> list[dict]:
    """Fixture providing sample product data."""
    return [
        {
            "name": "Tortillas 8 stk",
            "store_name": "Føtex",
            "discount_percent": 30.0,
            "discount_price": 14.95,
            "price": 14.95
        },
        {
            "name": "Hakket oksekød 8-12%",
            "store_name": "Netto",
            "discount_percent": 25.0,
            "discount_price": 35.00,
            "price": 35.00
        },
        {
            "name": "Ost - Cheddar skiver",
            "store_name": "Føtex",
            "discount_percent": 20.0,
            "discount_price": 22.50,
            "price": 22.50
        },
        {
            "name": "Salat - Iceberg",
            "store_name": "Bilka",
            "discount_percent": 15.0,
            "discount_price": 8.50,
            "price": 8.50
        }
    ]


@pytest.fixture
def basic_input(sample_products: list[dict]) -> IngredientMappingInput:
    """Fixture providing basic input data."""
    return IngredientMappingInput(
        meal_name="Taco Tuesday",
        ingredients=["tortillas", "ground beef", "cheese", "lettuce"],
        available_products=sample_products,
        match_threshold=0.6
    )


@pytest.fixture
def mock_gemini_json_response() -> str:
    """Fixture providing a valid JSON response from Gemini."""
    return """{
    "mappings": [
        {
            "ingredient": "tortillas",
            "matches": [
                {
                    "product_name": "Tortillas 8 stk",
                    "store_name": "Føtex",
                    "confidence": 0.95,
                    "discount_percent": 30.0,
                    "price": 14.95
                }
            ]
        },
        {
            "ingredient": "ground beef",
            "matches": [
                {
                    "product_name": "Hakket oksekød 8-12%",
                    "store_name": "Netto",
                    "confidence": 0.88,
                    "discount_percent": 25.0,
                    "price": 35.00
                }
            ]
        },
        {
            "ingredient": "cheese",
            "matches": [
                {
                    "product_name": "Ost - Cheddar skiver",
                    "store_name": "Føtex",
                    "confidence": 0.82,
                    "discount_percent": 20.0,
                    "price": 22.50
                }
            ]
        },
        {
            "ingredient": "lettuce",
            "matches": [
                {
                    "product_name": "Salat - Iceberg",
                    "store_name": "Bilka",
                    "confidence": 0.90,
                    "discount_percent": 15.0,
                    "price": 8.50
                }
            ]
        }
    ]
}"""


@pytest.fixture
def mock_gemini_partial_response() -> str:
    """Fixture providing a response with some unmapped ingredients."""
    return """{
    "mappings": [
        {
            "ingredient": "tortillas",
            "matches": [
                {
                    "product_name": "Tortillas 8 stk",
                    "store_name": "Føtex",
                    "confidence": 0.95,
                    "discount_percent": 30.0,
                    "price": 14.95
                }
            ]
        },
        {
            "ingredient": "ground beef",
            "matches": []
        },
        {
            "ingredient": "cheese",
            "matches": []
        },
        {
            "ingredient": "lettuce",
            "matches": []
        }
    ]
}"""


# ============================================================================
# Test: Agent Initialization
# ============================================================================

def test_agent_initialization_with_api_key():
    """Test that agent initializes correctly with explicit API key."""
    agent = IngredientMapperAgent(api_key="test_api_key_123")
    
    assert agent.client is not None
    assert "gemini" in agent.model.lower()


def test_agent_initialization_without_api_key_raises_error(monkeypatch):
    """Test that agent raises ValueError when no API key is provided."""
    from agents.discount_optimizer import config
    
    # Create a mock SecretStr that returns None
    mock_secret = MagicMock()
    mock_secret.get_secret_value.return_value = None
    
    monkeypatch.setattr(config.settings, "google_api_key", mock_secret)
    
    with pytest.raises(ValueError, match="Google API key is required"):
        IngredientMapperAgent()


# ============================================================================
# Test: Input Validation
# ============================================================================

def test_input_validation_valid():
    """Test that valid input is accepted."""
    input_data = IngredientMappingInput(
        meal_name="Pasta Carbonara",
        ingredients=["pasta", "bacon", "eggs"],
        available_products=[
            {"name": "Pasta", "store_name": "Netto", "discount_percent": 20, "price": 10}
        ]
    )
    
    assert input_data.meal_name == "Pasta Carbonara"
    assert len(input_data.ingredients) == 3


def test_input_validation_empty_ingredients():
    """Test that empty ingredients list is rejected."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        IngredientMappingInput(
            meal_name="Test Meal",
            ingredients=[],  # Min length is 1
            available_products=[]
        )


def test_input_validation_empty_strings_filtered():
    """Test that empty strings in ingredients are filtered out."""
    input_data = IngredientMappingInput(
        meal_name="Test Meal",
        ingredients=["pasta", "", "  ", "cheese"],
        available_products=[]
    )
    
    # Should filter out empty strings
    assert len(input_data.ingredients) == 2
    assert "pasta" in input_data.ingredients
    assert "cheese" in input_data.ingredients


def test_input_validation_match_threshold_range():
    """Test that match_threshold must be between 0.0 and 1.0."""
    # Valid threshold
    input_valid = IngredientMappingInput(
        meal_name="Test",
        ingredients=["pasta"],
        available_products=[],
        match_threshold=0.7
    )
    assert input_valid.match_threshold == 0.7
    
    # Invalid threshold (too high)
    with pytest.raises(Exception):  # Pydantic ValidationError
        IngredientMappingInput(
            meal_name="Test",
            ingredients=["pasta"],
            available_products=[],
            match_threshold=1.5
        )


# ============================================================================
# Test: Output Validation
# ============================================================================

def test_output_validation_valid():
    """Test that valid output is accepted."""
    output = IngredientMappingOutput(
        meal_name="Taco Tuesday",
        mappings=[],
        total_ingredients=4,
        ingredients_with_matches=3,
        coverage_percent=75.0,
        unmapped_ingredients=["lettuce"]
    )
    
    assert output.total_ingredients == 4
    assert output.coverage_percent == 75.0


def test_product_match_validation():
    """Test ProductMatch model validation."""
    match = ProductMatch(
        product_name="Hakket oksekød",
        store_name="Netto",
        match_score=0.85,
        discount_percent=25.0,
        price=35.00
    )
    
    assert match.match_score == 0.85
    assert match.discount_percent == 25.0


# ============================================================================
# Test: JSON Parsing (Valid JSON)
# ============================================================================

@pytest.mark.asyncio
async def test_map_ingredients_parses_valid_json(
    monkeypatch,
    basic_input: IngredientMappingInput,
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
    agent = IngredientMapperAgent(api_key="test_key")
    monkeypatch.setattr(
        agent.client.models,
        'generate_content',
        lambda **kwargs: mock_response
    )
    
    # Act
    output = await agent.map_ingredients(basic_input)
    
    # Assert
    assert isinstance(output, IngredientMappingOutput)
    assert output.meal_name == "Taco Tuesday"
    assert output.total_ingredients == 4
    assert output.ingredients_with_matches == 4
    assert output.coverage_percent == 100.0
    assert len(output.unmapped_ingredients) == 0
    
    # Check specific mappings
    tortilla_mapping = next(m for m in output.mappings if m.ingredient == "tortillas")
    assert tortilla_mapping.has_matches
    assert len(tortilla_mapping.matched_products) == 1
    assert tortilla_mapping.best_match.product_name == "Tortillas 8 stk"
    assert tortilla_mapping.best_match.match_score == 0.95
    
    # Verify multi-language mapping: "ground beef" → "Hakket oksekød"
    beef_mapping = next(m for m in output.mappings if m.ingredient == "ground beef")
    assert beef_mapping.has_matches
    assert beef_mapping.best_match.product_name == "Hakket oksekød 8-12%"
    assert beef_mapping.best_match.match_score == 0.88


# ============================================================================
# Test: Partial Matches
# ============================================================================

@pytest.mark.asyncio
async def test_map_ingredients_partial_matches(
    monkeypatch,
    basic_input: IngredientMappingInput,
    mock_gemini_partial_response: str
):
    """Test handling of partial matches (some ingredients unmapped)."""
    # Mock the Gemini API response
    mock_response = MagicMock()
    mock_response.text = mock_gemini_partial_response
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_gemini_partial_response
    
    # Patch the client's generate_content method
    agent = IngredientMapperAgent(api_key="test_key")
    monkeypatch.setattr(
        agent.client.models,
        'generate_content',
        lambda **kwargs: mock_response
    )
    
    # Act
    output = await agent.map_ingredients(basic_input)
    
    # Assert
    assert output.total_ingredients == 4
    assert output.ingredients_with_matches == 1  # Only tortillas matched
    assert output.coverage_percent == 25.0
    assert len(output.unmapped_ingredients) == 3
    assert "ground beef" in output.unmapped_ingredients
    assert "cheese" in output.unmapped_ingredients
    assert "lettuce" in output.unmapped_ingredients


# ============================================================================
# Test: Fallback on API Error
# ============================================================================

@pytest.mark.asyncio
async def test_fallback_on_api_error(
    monkeypatch,
    basic_input: IngredientMappingInput
):
    """Test that agent provides fallback mappings when Gemini API fails."""
    # Mock the Gemini API to raise an exception
    def mock_generate_error(**kwargs):
        raise Exception("API Error")
    
    agent = IngredientMapperAgent(api_key="test_key")
    monkeypatch.setattr(
        agent.client.models,
        'generate_content',
        mock_generate_error
    )
    
    # Act
    output = await agent.run(basic_input)
    
    # Assert - should get fallback empty mappings
    assert isinstance(output, IngredientMappingOutput)
    assert output.ingredients_with_matches == 0
    assert output.coverage_percent == 0.0
    assert len(output.unmapped_ingredients) == 4


# ============================================================================
# Test: Prompt Generation
# ============================================================================

@pytest.mark.asyncio
async def test_prompt_includes_all_ingredients(
    monkeypatch,
    basic_input: IngredientMappingInput,
    mock_gemini_json_response: str
):
    """Test that prompt includes all ingredients and products."""
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
    agent = IngredientMapperAgent(api_key="test_key")
    monkeypatch.setattr(
        agent.client.models,
        'generate_content',
        mock_generate
    )
    
    # Act
    await agent.map_ingredients(basic_input)
    
    # Assert - check that the prompt contains all ingredients
    prompt = captured_prompt['contents']
    
    assert "tortillas" in prompt
    assert "ground beef" in prompt
    assert "cheese" in prompt
    assert "lettuce" in prompt
    
    # Check that products are included
    assert "Tortillas 8 stk" in prompt
    assert "Hakket oksekød" in prompt
    assert "Ost - Cheddar" in prompt
    assert "Salat - Iceberg" in prompt
    
    # Check that meal name is included
    assert "Taco Tuesday" in prompt


# ============================================================================
# Test: System Instruction
# ============================================================================

def test_system_instruction_content():
    """Test that system instruction contains key elements."""
    agent = IngredientMapperAgent(api_key="test_key")
    system_instruction = agent._get_system_instruction()
    
    assert "expert" in system_instruction.lower()
    assert "multi-language" in system_instruction.lower()
    assert "confidence" in system_instruction.lower()
    assert "danish" in system_instruction.lower()


# ============================================================================
# Test: Coverage Calculation
# ============================================================================

@pytest.mark.asyncio
async def test_coverage_calculation_full(
    monkeypatch,
    mock_gemini_json_response: str
):
    """Test coverage calculation when all ingredients match."""
    agent = IngredientMapperAgent(api_key="test_key")
    
    input_data = IngredientMappingInput(
        meal_name="Simple Meal",
        ingredients=["pasta", "cheese"],
        available_products=[
            {"name": "Pasta", "store_name": "Netto", "discount_percent": 20, "price": 10},
            {"name": "Cheese", "store_name": "Føtex", "discount_percent": 25, "price": 15}
        ],
        match_threshold=0.6
    )
    
    # Mock response with full coverage
    mock_response_text = """{
        "mappings": [
            {
                "ingredient": "pasta",
                "matches": [
                    {
                        "product_name": "Pasta",
                        "store_name": "Netto",
                        "confidence": 0.95,
                        "discount_percent": 20.0,
                        "price": 10.0
                    }
                ]
            },
            {
                "ingredient": "cheese",
                "matches": [
                    {
                        "product_name": "Cheese",
                        "store_name": "Føtex",
                        "confidence": 0.90,
                        "discount_percent": 25.0,
                        "price": 15.0
                    }
                ]
            }
        ]
    }"""
    
    mock_response = MagicMock()
    mock_response.text = mock_response_text
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_response_text
    
    monkeypatch.setattr(
        agent.client.models,
        'generate_content',
        lambda **kwargs: mock_response
    )
    
    output = await agent.map_ingredients(input_data)
    
    assert output.total_ingredients == 2
    assert output.ingredients_with_matches == 2
    assert output.coverage_percent == 100.0


# ============================================================================
# Test: Multi-Language Support
# ============================================================================

@pytest.mark.asyncio
async def test_multi_language_mapping(
    monkeypatch,
    mock_gemini_json_response: str
):
    """Test that Gemini can map English ingredients to Danish products."""
    agent = IngredientMapperAgent(api_key="test_key")
    
    # English ingredients, Danish products
    input_data = IngredientMappingInput(
        meal_name="Test",
        ingredients=["ground beef", "cheese"],
        available_products=[
            {"name": "Hakket oksekød 8-12%", "store_name": "Netto", "discount_percent": 25, "price": 35},
            {"name": "Ost - Cheddar", "store_name": "Føtex", "discount_percent": 20, "price": 22}
        ],
        match_threshold=0.6
    )
    
    # Mock response showing successful multi-language mapping
    mock_response_text = """{
        "mappings": [
            {
                "ingredient": "ground beef",
                "matches": [
                    {
                        "product_name": "Hakket oksekød 8-12%",
                        "store_name": "Netto",
                        "confidence": 0.88,
                        "discount_percent": 25.0,
                        "price": 35.0
                    }
                ]
            },
            {
                "ingredient": "cheese",
                "matches": [
                    {
                        "product_name": "Ost - Cheddar",
                        "store_name": "Føtex",
                        "confidence": 0.85,
                        "discount_percent": 20.0,
                        "price": 22.0
                    }
                ]
            }
        ]
    }"""
    
    mock_response = MagicMock()
    mock_response.text = mock_response_text
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_response_text
    
    monkeypatch.setattr(
        agent.client.models,
        'generate_content',
        lambda **kwargs: mock_response
    )
    
    output = await agent.map_ingredients(input_data)
    
    # Verify that English "ground beef" was mapped to Danish "Hakket oksekød"
    beef_mapping = next(m for m in output.mappings if m.ingredient == "ground beef")
    assert beef_mapping.has_matches
    assert "Hakket oksekød" in beef_mapping.best_match.product_name
    assert beef_mapping.best_match.match_score >= 0.8
    
    # Verify that English "cheese" was mapped to Danish "Ost"
    cheese_mapping = next(m for m in output.mappings if m.ingredient == "cheese")
    assert cheese_mapping.has_matches
    assert "Ost" in cheese_mapping.best_match.product_name


# ============================================================================
# Test: Run Method (End-to-End)
# ============================================================================

@pytest.mark.asyncio
async def test_run_method_success(
    monkeypatch,
    basic_input: IngredientMappingInput,
    mock_gemini_json_response: str
):
    """Test the run method executes successfully."""
    # Mock the Gemini API response
    mock_response = MagicMock()
    mock_response.text = mock_gemini_json_response
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].text = mock_gemini_json_response
    
    agent = IngredientMapperAgent(api_key="test_key")
    monkeypatch.setattr(
        agent.client.models,
        'generate_content',
        lambda **kwargs: mock_response
    )
    
    output = await agent.run(basic_input)
    
    assert isinstance(output, IngredientMappingOutput)
    assert output.meal_name == basic_input.meal_name
    assert output.total_ingredients == len(basic_input.ingredients)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


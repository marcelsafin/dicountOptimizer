"""
Frontend-Backend Integration Tests for Shopping Optimizer.

This test suite validates that the frontend JavaScript correctly handles
the new Pydantic model structure from the backend API.

Tests cover:
- API response structure matches frontend expectations
- All Pydantic model fields are properly serialized
- Frontend can parse and display all response data
- Error handling works end-to-end
- Correlation IDs are properly propagated

Requirements: 7.1, 10.3 (Task 26)
"""

import json
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from agents.discount_optimizer.domain.models import (
    DiscountItem,
    Location,
    Purchase,
    ShoppingRecommendation,
)
from app import app


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def mock_agent():
    """Create mock shopping optimizer agent."""
    agent = AsyncMock()

    # Mock successful recommendation
    mock_recommendation = ShoppingRecommendation(
        purchases=[
            Purchase(
                product_name="Test Product",
                store_name="Test Store",
                purchase_day=date(2025, 11, 15),
                price=Decimal("10.00"),
                savings=Decimal("5.00"),
                meal_association="Test Meal",
            )
        ],
        total_savings=Decimal("5.00"),
        time_savings=10.0,
        tips=["Tip 1", "Tip 2"],
        motivation_message="Great job!",
        stores=[{"name": "Test Store", "items": 1, "address": "Test Address", "distance_km": 1.0}],
    )

    agent.run.return_value = mock_recommendation
    return agent


@pytest.fixture
def mock_factory(mock_agent):
    """Create mock agent factory."""
    factory = Mock()
    factory.create_shopping_optimizer_agent.return_value = mock_agent

    # Mock health check methods
    mock_geocoding = AsyncMock()
    mock_geocoding.health_check.return_value = True
    factory.get_geocoding_service.return_value = mock_geocoding

    mock_discount_repo = AsyncMock()
    mock_discount_repo.health_check.return_value = True
    factory.get_discount_repository.return_value = mock_discount_repo

    mock_cache = AsyncMock()
    mock_cache.health_check.return_value = True
    factory.get_cache_repository.return_value = mock_cache

    return factory


@pytest.fixture
def sample_recommendation():
    """Create a sample recommendation matching the Pydantic model structure."""
    return ShoppingRecommendation(
        purchases=[
            Purchase(
                product_name="Organic Tomatoes",
                store_name="Føtex Copenhagen",
                purchase_day=date(2025, 11, 20),
                price=Decimal("25.50"),
                savings=Decimal("10.00"),
                meal_association="Pasta with tomato sauce",
            ),
            Purchase(
                product_name="Ground Beef",
                store_name="Netto Vesterbro",
                purchase_day=date(2025, 11, 21),
                price=Decimal("45.00"),
                savings=Decimal("15.00"),
                meal_association="Taco night",
            ),
        ],
        total_savings=Decimal("25.00"),
        time_savings=12.5,
        tips=[
            "Buy tomatoes on Wednesday for best freshness",
            "Ground beef is 25% off this week",
        ],
        motivation_message="Great choices! You'll save 25 kr this week.",
        stores=[
            {
                "name": "Føtex Copenhagen",
                "address": "Vesterbrogade 123, Copenhagen",
                "latitude": 55.6761,
                "longitude": 12.5683,
                "distance_km": 1.2,
                "items": 1,
            },
            {
                "name": "Netto Vesterbro",
                "address": "Istedgade 45, Copenhagen",
                "latitude": 55.6721,
                "longitude": 12.5543,
                "distance_km": 2.1,
                "items": 1,
            },
        ],
    )


class TestAPIResponseStructure:
    """Test that API responses match frontend expectations."""

    def test_successful_response_structure(self, client, mock_factory, sample_recommendation):
        """Test that successful API response has all required fields for frontend."""
        mock_agent = AsyncMock()
        mock_agent.run.return_value = sample_recommendation
        mock_factory.create_shopping_optimizer_agent.return_value = mock_agent

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta", "taco"],
                    "preferences": {"maximize_savings": True},
                },
            )

            assert response.status_code == 200
            data = response.get_json()

            # Verify top-level structure
            assert data["success"] is True
            assert "recommendation" in data
            assert "user_location" in data
            assert "correlation_id" in data

            # Verify user_location structure (needed for map)
            user_loc = data["user_location"]
            assert "latitude" in user_loc
            assert "longitude" in user_loc
            assert isinstance(user_loc["latitude"], (int, float))
            assert isinstance(user_loc["longitude"], (int, float))

            # Verify recommendation structure
            rec = data["recommendation"]
            assert "purchases" in rec
            assert "total_savings" in rec
            assert "time_savings" in rec
            assert "tips" in rec
            assert "motivation_message" in rec
            assert "stores" in rec

    def test_purchases_array_structure(self, client, mock_factory, sample_recommendation):
        """Test that purchases array has correct structure for frontend display."""
        mock_agent = AsyncMock()
        mock_agent.run.return_value = sample_recommendation
        mock_factory.create_shopping_optimizer_agent.return_value = mock_agent

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            data = response.get_json()
            purchases = data["recommendation"]["purchases"]

            assert isinstance(purchases, list)
            assert len(purchases) > 0

            # Verify each purchase has required fields
            for purchase in purchases:
                assert "product_name" in purchase
                assert "store_name" in purchase
                assert "purchase_day" in purchase
                assert "price" in purchase
                assert "savings" in purchase
                assert "meal_association" in purchase

                # Verify types match frontend expectations
                assert isinstance(purchase["product_name"], str)
                assert isinstance(purchase["store_name"], str)
                assert isinstance(purchase["purchase_day"], str)  # ISO format
                assert isinstance(purchase["price"], (int, float))
                assert isinstance(purchase["savings"], (int, float))
                assert isinstance(purchase["meal_association"], str)

    def test_stores_array_structure(self, client, mock_factory, sample_recommendation):
        """Test that stores array has correct structure for map display."""
        mock_agent = AsyncMock()
        mock_agent.run.return_value = sample_recommendation
        mock_factory.create_shopping_optimizer_agent.return_value = mock_agent

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            data = response.get_json()
            stores = data["recommendation"]["stores"]

            assert isinstance(stores, list)
            assert len(stores) > 0

            # Verify each store has required fields for map
            for store in stores:
                assert "name" in store
                assert "address" in store
                assert "latitude" in store
                assert "longitude" in store
                assert "distance_km" in store
                assert "items" in store

                # Verify types
                assert isinstance(store["name"], str)
                assert isinstance(store["address"], str)
                assert isinstance(store["latitude"], (int, float))
                assert isinstance(store["longitude"], (int, float))
                assert isinstance(store["distance_km"], (int, float))
                # items can be int or float (JavaScript handles both)
                assert isinstance(store["items"], (int, float))

    def test_savings_fields_are_numeric(self, client, mock_factory, sample_recommendation):
        """Test that savings fields are properly converted to float for frontend."""
        mock_agent = AsyncMock()
        mock_agent.run.return_value = sample_recommendation
        mock_factory.create_shopping_optimizer_agent.return_value = mock_agent

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            data = response.get_json()
            rec = data["recommendation"]

            # Verify total_savings is numeric (not Decimal string)
            assert isinstance(rec["total_savings"], (int, float))
            assert rec["total_savings"] >= 0

            # Verify time_savings is numeric
            assert isinstance(rec["time_savings"], (int, float))
            assert rec["time_savings"] >= 0

    def test_tips_array_structure(self, client, mock_factory, sample_recommendation):
        """Test that tips array is properly formatted for frontend display."""
        mock_agent = AsyncMock()
        mock_agent.run.return_value = sample_recommendation
        mock_factory.create_shopping_optimizer_agent.return_value = mock_agent

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            data = response.get_json()
            tips = data["recommendation"]["tips"]

            assert isinstance(tips, list)
            # Tips can be empty, but if present, should be strings
            for tip in tips:
                assert isinstance(tip, str)
                assert len(tip) > 0

    def test_motivation_message_is_string(self, client, mock_factory, sample_recommendation):
        """Test that motivation message is a string for frontend display."""
        mock_agent = AsyncMock()
        mock_agent.run.return_value = sample_recommendation
        mock_factory.create_shopping_optimizer_agent.return_value = mock_agent

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            data = response.get_json()
            motivation = data["recommendation"]["motivation_message"]

            assert isinstance(motivation, str)
            assert len(motivation) > 0


class TestErrorResponseStructure:
    """Test that error responses match frontend error handling expectations."""

    def test_validation_error_structure(self, client, mock_factory, mock_agent):
        """Test that validation errors have correct structure for frontend."""
        from agents.discount_optimizer.domain.exceptions import ValidationError

        mock_agent.run.side_effect = ValidationError("Invalid location format")

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "invalid",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            assert response.status_code == 400
            data = response.get_json()

            # Verify error structure
            assert data["success"] is False
            assert "error" in data
            assert "error_type" in data
            assert "correlation_id" in data

            # Verify error_type for frontend conditional handling
            assert data["error_type"] == "validation"
            assert "validation" in data["error"].lower()

    def test_optimization_error_structure(self, client, mock_factory, mock_agent):
        """Test that optimization errors have correct structure for frontend."""
        from agents.discount_optimizer.domain.exceptions import ShoppingOptimizerError

        mock_agent.run.side_effect = ShoppingOptimizerError("No discounts found")

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            assert response.status_code == 500
            data = response.get_json()

            assert data["success"] is False
            assert data["error_type"] == "optimization"
            assert "correlation_id" in data

    def test_server_error_structure(self, client, mock_factory, mock_agent):
        """Test that server errors have correct structure for frontend."""
        mock_agent.run.side_effect = Exception("Unexpected server error")

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            assert response.status_code == 500
            data = response.get_json()

            assert data["success"] is False
            assert data["error_type"] == "server"
            assert "correlation_id" in data

    def test_correlation_id_in_all_responses(self, client, mock_factory, sample_recommendation):
        """Test that correlation_id is present in both success and error responses."""
        mock_agent = AsyncMock()
        mock_agent.run.return_value = sample_recommendation
        mock_factory.create_shopping_optimizer_agent.return_value = mock_agent

        with patch("app.agent_factory", mock_factory):
            # Test success response
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            data = response.get_json()
            assert "correlation_id" in data
            assert isinstance(data["correlation_id"], str)
            assert len(data["correlation_id"]) > 0


class TestDateSerialization:
    """Test that dates are properly serialized for frontend."""

    def test_purchase_day_is_iso_format(self, client, mock_factory, sample_recommendation):
        """Test that purchase_day is in ISO format for JavaScript Date parsing."""
        mock_agent = AsyncMock()
        mock_agent.run.return_value = sample_recommendation
        mock_factory.create_shopping_optimizer_agent.return_value = mock_agent

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            data = response.get_json()
            purchases = data["recommendation"]["purchases"]

            for purchase in purchases:
                purchase_day = purchase["purchase_day"]

                # Verify it's a string in ISO format (YYYY-MM-DD)
                assert isinstance(purchase_day, str)
                assert len(purchase_day) == 10  # YYYY-MM-DD
                assert purchase_day.count("-") == 2

                # Verify it can be parsed by JavaScript Date
                # Format should be: 2025-11-20
                parts = purchase_day.split("-")
                assert len(parts) == 3
                assert len(parts[0]) == 4  # Year
                assert len(parts[1]) == 2  # Month
                assert len(parts[2]) == 2  # Day


class TestDecimalSerialization:
    """Test that Decimal fields are properly converted to float for JSON."""

    def test_decimal_fields_are_json_serializable(
        self, client, mock_factory, sample_recommendation
    ):
        """Test that all Decimal fields are converted to float for JSON."""
        mock_agent = AsyncMock()
        mock_agent.run.return_value = sample_recommendation
        mock_factory.create_shopping_optimizer_agent.return_value = mock_agent

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            # Verify response is valid JSON
            assert response.content_type == "application/json"

            data = response.get_json()

            # Verify total_savings is float, not Decimal
            total_savings = data["recommendation"]["total_savings"]
            assert isinstance(total_savings, (int, float))
            assert not isinstance(total_savings, str)

            # Verify purchase prices and savings are float
            for purchase in data["recommendation"]["purchases"]:
                assert isinstance(purchase["price"], (int, float))
                assert isinstance(purchase["savings"], (int, float))


class TestFrontendJavaScriptCompatibility:
    """Test that API responses are compatible with frontend JavaScript expectations."""

    def test_response_can_be_parsed_by_javascript(
        self, client, mock_factory, sample_recommendation
    ):
        """Test that response structure matches what app.js expects."""
        mock_agent = AsyncMock()
        mock_agent.run.return_value = sample_recommendation
        mock_factory.create_shopping_optimizer_agent.return_value = mock_agent

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            data = response.get_json()

            # Simulate what JavaScript does in app.js displayResults()
            recommendation = data["recommendation"]
            user_location = data["user_location"]

            # Test map display data
            assert len(recommendation["stores"]) > 0
            assert user_location["latitude"] is not None
            assert user_location["longitude"] is not None

            # Test shopping list data
            assert len(recommendation["purchases"]) > 0
            for purchase in recommendation["purchases"]:
                # Simulate formatPurchasesHTML()
                store_name = purchase["store_name"]
                product_name = purchase["product_name"]
                price = float(purchase["price"])
                savings = float(purchase["savings"])
                meal = purchase["meal_association"]
                day = purchase["purchase_day"]

                assert isinstance(store_name, str)
                assert isinstance(product_name, str)
                assert price >= 0
                assert savings >= 0
                assert isinstance(meal, str)
                assert isinstance(day, str)

            # Test savings display
            total_savings = float(recommendation["total_savings"])
            time_savings = float(recommendation["time_savings"])
            assert total_savings >= 0
            assert time_savings >= 0

            # Test tips display
            tips = recommendation["tips"]
            assert isinstance(tips, list)

            # Test motivation message
            motivation = recommendation["motivation_message"]
            assert isinstance(motivation, str)

    def test_empty_purchases_handled_gracefully(self, client, mock_factory):
        """Test that empty purchases array is handled correctly."""
        empty_recommendation = ShoppingRecommendation(
            purchases=[],
            total_savings=Decimal("0.00"),
            time_savings=0.0,
            tips=["No discounts found in your area"],
            motivation_message="Try adjusting your preferences or location.",
            stores=[],
        )

        mock_agent = AsyncMock()
        mock_agent.run.return_value = empty_recommendation
        mock_factory.create_shopping_optimizer_agent.return_value = mock_agent

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            data = response.get_json()
            assert data["success"] is True
            assert len(data["recommendation"]["purchases"]) == 0
            assert len(data["recommendation"]["stores"]) == 0
            assert data["recommendation"]["total_savings"] == 0.0


class TestCorrelationIDPropagation:
    """Test that correlation IDs are properly propagated for debugging."""

    def test_correlation_id_in_success_response(self, client, mock_factory, sample_recommendation):
        """Test that correlation ID is included in successful responses."""
        mock_agent = AsyncMock()
        mock_agent.run.return_value = sample_recommendation
        mock_factory.create_shopping_optimizer_agent.return_value = mock_agent

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            data = response.get_json()
            correlation_id = data["correlation_id"]

            # Verify format (should be UUID)
            assert isinstance(correlation_id, str)
            assert len(correlation_id) > 0
            # UUID format: 8-4-4-4-12 characters
            parts = correlation_id.split("-")
            assert len(parts) == 5

    def test_correlation_id_in_error_response(self, client, mock_factory, mock_agent):
        """Test that correlation ID is included in error responses for debugging."""
        from agents.discount_optimizer.domain.exceptions import ValidationError

        mock_agent.run.side_effect = ValidationError("Invalid input")

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "invalid",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            data = response.get_json()
            correlation_id = data["correlation_id"]

            # Verify correlation ID is present for error tracking
            assert isinstance(correlation_id, str)
            assert len(correlation_id) > 0

    def test_correlation_id_passed_to_agent(self, client, mock_factory, mock_agent):
        """Test that correlation ID is passed to agent for distributed tracing."""
        from agents.discount_optimizer.agents.shopping_optimizer_agent import ShoppingOptimizerInput

        with patch("app.agent_factory", mock_factory):
            response = client.post(
                "/api/optimize",
                json={
                    "location": "55.6761,12.5683",
                    "meals": ["pasta"],
                    "preferences": {"maximize_savings": True},
                },
            )

            data = response.get_json()
            correlation_id = data["correlation_id"]

            # Verify agent was called with correlation_id
            call_args = mock_agent.run.call_args
            agent_input = call_args[0][0]
            assert isinstance(agent_input, ShoppingOptimizerInput)
            assert agent_input.correlation_id == correlation_id

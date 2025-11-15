"""
Integration tests for Flask API endpoints.

This module tests the Flask API integration with the agent architecture
using mocked dependencies to avoid live API calls.

Requirements: 10.1, 10.3
"""

import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from app import app
from agents.discount_optimizer.domain.models import (
    ShoppingRecommendation,
    Purchase,
)
from agents.discount_optimizer.domain.exceptions import ValidationError, ShoppingOptimizerError


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config['TESTING'] = True
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
                meal_association="Test Meal"
            )
        ],
        total_savings=Decimal("5.00"),
        time_savings=10.0,
        tips=["Tip 1", "Tip 2"],
        motivation_message="Great job!",
        stores=[{"name": "Test Store", "items": 1, "address": "Test Address", "distance_km": 1.0}]
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


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_basic_health_check(self, client):
        """Test /health endpoint returns healthy status."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'shopping-optimizer'
        assert 'environment' in data
    
    def test_detailed_health_check_all_healthy(self, client, mock_factory):
        """Test /health/detailed endpoint when all dependencies are healthy."""
        with patch('app.agent_factory', mock_factory):
            response = client.get('/health/detailed')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'healthy'
            assert 'dependencies' in data
            assert 'correlation_id' in data
            assert 'timestamp' in data
            
            # Check all dependencies
            assert data['dependencies']['geocoding_service']['status'] == 'healthy'
            assert data['dependencies']['discount_repository']['status'] == 'healthy'
            assert data['dependencies']['cache_repository']['status'] == 'healthy'
    
    def test_detailed_health_check_degraded(self, client, mock_factory):
        """Test /health/detailed endpoint when some dependencies are unhealthy."""
        # Make geocoding service unhealthy
        mock_geocoding = AsyncMock()
        mock_geocoding.health_check.return_value = False
        mock_factory.get_geocoding_service.return_value = mock_geocoding
        
        with patch('app.agent_factory', mock_factory):
            response = client.get('/health/detailed')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'degraded'
            assert data['dependencies']['geocoding_service']['status'] == 'unhealthy'
    
    def test_detailed_health_check_all_unhealthy(self, client, mock_factory):
        """Test /health/detailed endpoint when all dependencies are unhealthy."""
        # Make all services unhealthy
        mock_geocoding = AsyncMock()
        mock_geocoding.health_check.return_value = False
        mock_factory.get_geocoding_service.return_value = mock_geocoding
        
        mock_discount_repo = AsyncMock()
        mock_discount_repo.health_check.return_value = False
        mock_factory.get_discount_repository.return_value = mock_discount_repo
        
        mock_cache = AsyncMock()
        mock_cache.health_check.return_value = False
        mock_factory.get_cache_repository.return_value = mock_cache
        
        with patch('app.agent_factory', mock_factory):
            response = client.get('/health/detailed')
            
            assert response.status_code == 503
            data = response.get_json()
            assert data['status'] == 'unhealthy'


class TestOptimizeEndpoint:
    """Test /api/optimize endpoint."""
    
    def test_optimize_success_with_coordinates(self, client, mock_factory):
        """Test successful optimization with coordinates."""
        with patch('app.agent_factory', mock_factory):
            response = client.post(
                '/api/optimize',
                json={
                    'location': '55.6761,12.5683',
                    'meals': ['taco'],
                    'preferences': {'maximize_savings': True}
                }
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'recommendation' in data
            assert 'correlation_id' in data
            assert 'user_location' in data
            assert data['user_location']['latitude'] == 55.6761
            assert data['user_location']['longitude'] == 12.5683
            
            # Verify recommendation structure
            rec = data['recommendation']
            assert 'purchases' in rec
            assert 'total_savings' in rec
            assert 'time_savings' in rec
            assert 'tips' in rec
            assert 'motivation_message' in rec
            assert 'stores' in rec
    
    def test_optimize_success_with_address(self, client, mock_factory):
        """Test successful optimization with address."""
        with patch('app.agent_factory', mock_factory):
            response = client.post(
                '/api/optimize',
                json={
                    'location': 'Copenhagen',
                    'meals': ['pasta'],
                    'preferences': {'maximize_savings': True}
                }
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'correlation_id' in data
    
    def test_optimize_no_data(self, client):
        """Test /api/optimize with no data returns 400."""
        response = client.post(
            '/api/optimize',
            data='null',
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
        assert 'correlation_id' in data
    
    def test_optimize_no_location(self, client):
        """Test /api/optimize with no location returns 400."""
        response = client.post(
            '/api/optimize',
            json={
                'meals': ['taco'],
                'preferences': {'maximize_savings': True}
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'location' in data['error'].lower()
        assert 'correlation_id' in data
    
    def test_optimize_validation_error(self, client, mock_factory, mock_agent):
        """Test /api/optimize handles ValidationError correctly."""
        # Make agent raise ValidationError
        mock_agent.run.side_effect = ValidationError("Invalid input")
        
        with patch('app.agent_factory', mock_factory):
            response = client.post(
                '/api/optimize',
                json={
                    'location': '55.6761,12.5683',
                    'meals': ['taco'],
                    'preferences': {'maximize_savings': True}
                }
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['success'] is False
            assert 'validation' in data['error'].lower()
            assert data['error_type'] == 'validation'
            assert 'correlation_id' in data
    
    def test_optimize_optimizer_error(self, client, mock_factory, mock_agent):
        """Test /api/optimize handles ShoppingOptimizerError correctly."""
        # Make agent raise ShoppingOptimizerError
        mock_agent.run.side_effect = ShoppingOptimizerError("Optimization failed")
        
        with patch('app.agent_factory', mock_factory):
            response = client.post(
                '/api/optimize',
                json={
                    'location': '55.6761,12.5683',
                    'meals': ['taco'],
                    'preferences': {'maximize_savings': True}
                }
            )
            
            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'optimization' in data['error'].lower()
            assert data['error_type'] == 'optimization'
            assert 'correlation_id' in data
    
    def test_optimize_generic_error(self, client, mock_factory, mock_agent):
        """Test /api/optimize handles generic exceptions correctly."""
        # Make agent raise generic exception
        mock_agent.run.side_effect = Exception("Unexpected error")
        
        with patch('app.agent_factory', mock_factory):
            response = client.post(
                '/api/optimize',
                json={
                    'location': '55.6761,12.5683',
                    'meals': ['taco'],
                    'preferences': {'maximize_savings': True}
                }
            )
            
            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'server error' in data['error'].lower()
            assert data['error_type'] == 'server'
            assert 'correlation_id' in data
    
    def test_optimize_with_all_parameters(self, client, mock_factory):
        """Test /api/optimize with all optional parameters."""
        with patch('app.agent_factory', mock_factory):
            response = client.post(
                '/api/optimize',
                json={
                    'location': '55.6761,12.5683',
                    'meals': ['taco', 'pasta'],
                    'preferences': {
                        'maximize_savings': True,
                        'minimize_stores': True,
                        'prefer_organic': False
                    },
                    'num_meals': 5,
                    'search_radius_km': 10.0,
                    'timeframe': 'next 3 days'
                }
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'correlation_id' in data
    
    def test_optimize_correlation_id_propagation(self, client, mock_factory, mock_agent):
        """Test that correlation IDs are properly propagated through the system."""
        with patch('app.agent_factory', mock_factory):
            response = client.post(
                '/api/optimize',
                json={
                    'location': '55.6761,12.5683',
                    'meals': ['taco'],
                    'preferences': {'maximize_savings': True}
                }
            )
            
            assert response.status_code == 200
            data = response.get_json()
            correlation_id = data['correlation_id']
            
            # Verify correlation ID was passed to agent
            call_args = mock_agent.run.call_args
            agent_input = call_args[0][0]
            assert agent_input.correlation_id == correlation_id


class TestAgentFactoryIntegration:
    """Test agent factory integration."""
    
    def test_factory_creates_agent(self, mock_factory):
        """Test that factory can create agent instances."""
        with patch('app.agent_factory', mock_factory):
            agent = mock_factory.create_shopping_optimizer_agent()
            assert agent is not None
            mock_factory.create_shopping_optimizer_agent.assert_called_once()
    
    def test_factory_provides_services(self, mock_factory):
        """Test that factory provides all required services."""
        with patch('app.agent_factory', mock_factory):
            geocoding = mock_factory.get_geocoding_service()
            discount_repo = mock_factory.get_discount_repository()
            cache = mock_factory.get_cache_repository()
            
            assert geocoding is not None
            assert discount_repo is not None
            assert cache is not None

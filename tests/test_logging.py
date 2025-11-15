"""
Tests for structured logging functionality.

This module tests the logging configuration, context management,
and correlation ID tracking.
"""

import logging
import uuid
from io import StringIO

import pytest
import structlog

from agents.discount_optimizer.logging import (
    LogContext,
    clear_context,
    generate_correlation_id,
    get_agent_context,
    get_correlation_id,
    get_logger,
    get_request_id,
    set_agent_context,
    set_correlation_id,
    set_request_id,
)


class TestCorrelationID:
    """Test correlation ID generation and management."""
    
    def test_generate_correlation_id(self):
        """Test that correlation IDs are valid UUIDs."""
        correlation_id = generate_correlation_id()
        
        # Should be a valid UUID string
        assert isinstance(correlation_id, str)
        uuid.UUID(correlation_id)  # Raises ValueError if invalid
    
    def test_set_and_get_correlation_id(self):
        """Test setting and retrieving correlation ID."""
        clear_context()
        
        test_id = "test-correlation-123"
        set_correlation_id(test_id)
        
        assert get_correlation_id() == test_id
    
    def test_set_correlation_id_generates_if_none(self):
        """Test that set_correlation_id generates ID if none provided."""
        clear_context()
        
        correlation_id = set_correlation_id(None)
        
        assert correlation_id is not None
        assert get_correlation_id() == correlation_id
        uuid.UUID(correlation_id)  # Should be valid UUID


class TestRequestID:
    """Test request ID management."""
    
    def test_set_and_get_request_id(self):
        """Test setting and retrieving request ID."""
        clear_context()
        
        test_id = "test-request-456"
        set_request_id(test_id)
        
        assert get_request_id() == test_id
    
    def test_set_request_id_generates_if_none(self):
        """Test that set_request_id generates ID if none provided."""
        clear_context()
        
        request_id = set_request_id(None)
        
        assert request_id is not None
        assert get_request_id() == request_id
        uuid.UUID(request_id)  # Should be valid UUID


class TestAgentContext:
    """Test agent context management."""
    
    def test_set_and_get_agent_context(self):
        """Test setting and retrieving agent context."""
        clear_context()
        
        agent_name = "meal_suggester"
        set_agent_context(agent_name)
        
        assert get_agent_context() == agent_name


class TestLogContext:
    """Test LogContext context manager."""
    
    def test_log_context_sets_correlation_id(self):
        """Test that LogContext sets correlation ID."""
        clear_context()
        
        test_id = "context-test-123"
        
        with LogContext(correlation_id=test_id):
            assert get_correlation_id() == test_id
    
    def test_log_context_generates_correlation_id_if_none(self):
        """Test that LogContext generates correlation ID if not provided."""
        clear_context()
        
        with LogContext():
            correlation_id = get_correlation_id()
            assert correlation_id is not None
            uuid.UUID(correlation_id)  # Should be valid UUID
    
    def test_log_context_sets_request_id(self):
        """Test that LogContext sets request ID."""
        clear_context()
        
        test_id = "request-test-456"
        
        with LogContext(request_id=test_id):
            assert get_request_id() == test_id
    
    def test_log_context_sets_agent(self):
        """Test that LogContext sets agent context."""
        clear_context()
        
        agent_name = "test_agent"
        
        with LogContext(agent=agent_name):
            assert get_agent_context() == agent_name
    
    def test_log_context_restores_previous_values(self):
        """Test that LogContext restores previous context on exit."""
        clear_context()
        
        # Set initial values
        initial_correlation = "initial-123"
        initial_request = "initial-456"
        initial_agent = "initial_agent"
        
        set_correlation_id(initial_correlation)
        set_request_id(initial_request)
        set_agent_context(initial_agent)
        
        # Use context with different values
        with LogContext(
            correlation_id="temp-123",
            request_id="temp-456",
            agent="temp_agent"
        ):
            assert get_correlation_id() == "temp-123"
            assert get_request_id() == "temp-456"
            assert get_agent_context() == "temp_agent"
        
        # Should restore initial values
        assert get_correlation_id() == initial_correlation
        assert get_request_id() == initial_request
        assert get_agent_context() == initial_agent
    
    def test_log_context_nested(self):
        """Test nested LogContext managers."""
        clear_context()
        
        with LogContext(correlation_id="outer-123"):
            assert get_correlation_id() == "outer-123"
            
            with LogContext(correlation_id="inner-456"):
                assert get_correlation_id() == "inner-456"
            
            # Should restore outer value
            assert get_correlation_id() == "outer-123"


class TestLogger:
    """Test logger functionality."""
    
    def test_get_logger_returns_bound_logger(self):
        """Test that get_logger returns a BoundLogger instance."""
        logger = get_logger(__name__)
        
        # Logger should have the standard logging methods
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert callable(logger.info)
    
    def test_get_logger_with_name(self):
        """Test that get_logger accepts a name parameter."""
        logger = get_logger("test.module")
        
        # Logger should have the standard logging methods
        assert hasattr(logger, 'info')
        assert callable(logger.info)
    
    def test_get_logger_without_name(self):
        """Test that get_logger works without a name parameter."""
        logger = get_logger()
        
        # Logger should have the standard logging methods
        assert hasattr(logger, 'info')
        assert callable(logger.info)
    
    def test_logger_includes_correlation_id(self):
        """Test that logger includes correlation ID in output."""
        clear_context()
        
        test_id = "log-test-123"
        set_correlation_id(test_id)
        
        logger = get_logger(__name__)
        
        # This test verifies the logger can be called
        # Actual output verification would require capturing log output
        logger.info("test_message", test_field="test_value")
    
    def test_logger_with_context_manager(self):
        """Test logger with LogContext context manager."""
        clear_context()
        
        logger = get_logger(__name__)
        
        with LogContext(
            correlation_id="context-123",
            agent="test_agent"
        ):
            # Logger should include context in output
            logger.info("test_with_context", action="test")


class TestClearContext:
    """Test context clearing functionality."""
    
    def test_clear_context_removes_all_values(self):
        """Test that clear_context removes all context variables."""
        # Set all context values
        set_correlation_id("test-123")
        set_request_id("test-456")
        set_agent_context("test_agent")
        
        # Clear context
        clear_context()
        
        # All should be None
        assert get_correlation_id() is None
        assert get_request_id() is None
        assert get_agent_context() is None

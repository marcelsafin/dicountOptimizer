"""
Structured logging configuration using structlog.

This module provides enterprise-grade structured logging with:
- Correlation ID generation for request tracing
- JSON formatting for production environments
- Console formatting for development
- Context processors for automatic field injection
- Integration with Python's standard logging

Example:
    >>> from agents.discount_optimizer.logging import get_logger
    >>> logger = get_logger()
    >>> logger.info("user_action", user_id=123, action="login")
"""

import logging
import logging.handlers
import sys
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from .config import settings

# =========================================================================
# Context Variables for Request Tracing
# =========================================================================

# Correlation ID for distributed tracing across agent calls
correlation_id_var: ContextVar[str | None] = ContextVar('correlation_id', default=None)

# Request ID for tracking individual HTTP requests
request_id_var: ContextVar[str | None] = ContextVar('request_id', default=None)

# Agent context for tracking which agent is executing
agent_context_var: ContextVar[str | None] = ContextVar('agent_context', default=None)


# =========================================================================
# Correlation ID Management
# =========================================================================

def generate_correlation_id() -> str:
    """
    Generate a new correlation ID for request tracing.
    
    Returns:
        UUID string for correlation tracking
    """
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str | None = None) -> str:
    """
    Set correlation ID for the current context.
    
    Args:
        correlation_id: Optional correlation ID. If None, generates a new one.
    
    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = generate_correlation_id()
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> str | None:
    """
    Get the current correlation ID.
    
    Returns:
        Current correlation ID or None if not set
    """
    return correlation_id_var.get()


def set_request_id(request_id: str | None = None) -> str:
    """
    Set request ID for the current context.
    
    Args:
        request_id: Optional request ID. If None, generates a new one.
    
    Returns:
        The request ID that was set
    """
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> str | None:
    """
    Get the current request ID.
    
    Returns:
        Current request ID or None if not set
    """
    return request_id_var.get()


def set_agent_context(agent_name: str) -> None:
    """
    Set the current agent context for logging.
    
    Args:
        agent_name: Name of the agent currently executing
    """
    agent_context_var.set(agent_name)


def get_agent_context() -> str | None:
    """
    Get the current agent context.
    
    Returns:
        Current agent name or None if not set
    """
    return agent_context_var.get()


def clear_context() -> None:
    """Clear all context variables."""
    correlation_id_var.set(None)
    request_id_var.set(None)
    agent_context_var.set(None)


# =========================================================================
# Context Processors
# =========================================================================

def add_correlation_id(
    logger: logging.Logger,
    method_name: str,
    event_dict: EventDict
) -> EventDict:
    """
    Add correlation ID to log events.
    
    This processor automatically injects the correlation ID from context
    into every log event, enabling distributed tracing across agent calls.
    """
    correlation_id = get_correlation_id()
    if correlation_id:
        event_dict['correlation_id'] = correlation_id
    return event_dict


def add_request_id(
    logger: logging.Logger,
    method_name: str,
    event_dict: EventDict
) -> EventDict:
    """
    Add request ID to log events.
    
    This processor automatically injects the request ID from context
    into every log event for tracking individual HTTP requests.
    """
    request_id = get_request_id()
    if request_id:
        event_dict['request_id'] = request_id
    return event_dict


def add_agent_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: EventDict
) -> EventDict:
    """
    Add agent context to log events.
    
    This processor automatically injects the current agent name
    into every log event for tracking which agent is executing.
    """
    agent_context = get_agent_context()
    if agent_context:
        event_dict['agent'] = agent_context
    return event_dict


def add_environment(
    logger: logging.Logger,
    method_name: str,
    event_dict: EventDict
) -> EventDict:
    """
    Add environment information to log events.
    
    This processor adds the deployment environment (dev/staging/production)
    to every log event for filtering and analysis.
    """
    event_dict['environment'] = settings.environment
    return event_dict


def add_timestamp(
    logger: logging.Logger,
    method_name: str,
    event_dict: EventDict
) -> EventDict:
    """
    Add ISO 8601 timestamp to log events.
    
    This processor adds a standardized timestamp for log aggregation
    and time-series analysis.
    """
    import datetime
    event_dict['timestamp'] = datetime.datetime.now(datetime.UTC).isoformat()
    return event_dict


# =========================================================================
# Logging Configuration
# =========================================================================

def configure_stdlib_logging() -> None:
    """
    Configure Python's standard logging to work with structlog.
    
    This sets up the root logger and configures handlers based on
    the application settings (file logging, rotation, etc.).
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.get_logging_level())
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler (always present)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.get_logging_level())
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=settings.log_file,
            maxBytes=settings.log_max_bytes,
            backupCount=settings.log_backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(settings.get_logging_level())
        root_logger.addHandler(file_handler)
    
    # Set levels for noisy third-party loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.INFO)


def get_processors() -> list[Processor]:
    """
    Get the list of structlog processors based on configuration.
    
    Returns:
        List of processors for structlog configuration
    """
    processors: list[Processor] = [
        # Add context information
        add_correlation_id,
        add_request_id,
        add_agent_context,
        add_environment,
        add_timestamp,
        
        # Add log level
        structlog.stdlib.add_log_level,
        
        # Add logger name
        structlog.stdlib.add_logger_name,
        
        # Add exception info if present
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        
        # Add call site information in development
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ) if settings.is_development() else structlog.processors.CallsiteParameterAdder(
            parameters=[]
        ),
    ]
    
    # Add renderer based on log format
    if settings.log_format == 'json':
        # JSON format for production (machine-readable)
        processors.append(structlog.processors.JSONRenderer())
    elif settings.log_format == 'console':
        # Console format for development (human-readable with colors)
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        )
    else:
        # Plain text format
        processors.append(structlog.processors.KeyValueRenderer())
    
    return processors


def configure_structlog() -> None:
    """
    Configure structlog with processors and formatters.
    
    This sets up structlog to work with Python's standard logging,
    adds context processors, and configures output formatting based
    on the deployment environment.
    """
    structlog.configure(
        processors=get_processors(),
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def setup_logging() -> None:
    """
    Initialize logging system.
    
    This is the main entry point for logging configuration.
    Call this once at application startup.
    """
    # Configure standard library logging
    configure_stdlib_logging()
    
    # Configure structlog
    configure_structlog()
    
    # Log startup message
    logger = get_logger(__name__)
    logger.info(
        "logging_initialized",
        log_level=settings.log_level,
        log_format=settings.log_format,
        environment=settings.environment,
        structured_logging=settings.enable_structured_logging,
    )


# =========================================================================
# Logger Factory
# =========================================================================

def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__ of the calling module).
              If None, returns the root logger.
    
    Returns:
        Configured structlog logger
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("processing_request", user_id=123, items=5)
    """
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger


# =========================================================================
# Context Manager for Request Tracing
# =========================================================================

class LogContext:
    """
    Context manager for setting logging context.
    
    This ensures correlation IDs and other context are properly set
    and cleaned up for each request or agent execution.
    
    Example:
        >>> with LogContext(correlation_id="abc-123", agent="meal_suggester"):
        ...     logger.info("processing")  # Will include correlation_id and agent
    """
    
    def __init__(
        self,
        correlation_id: str | None = None,
        request_id: str | None = None,
        agent: str | None = None,
        **extra_context: Any
    ):
        """
        Initialize log context.
        
        Args:
            correlation_id: Correlation ID for distributed tracing
            request_id: Request ID for HTTP request tracking
            agent: Agent name for agent execution tracking
            **extra_context: Additional context fields to bind to logger
        """
        self.correlation_id = correlation_id
        self.request_id = request_id
        self.agent = agent
        self.extra_context = extra_context
        self._previous_correlation_id: str | None = None
        self._previous_request_id: str | None = None
        self._previous_agent: str | None = None
    
    def __enter__(self) -> 'LogContext':
        """Enter context and set logging context variables."""
        # Save previous values
        self._previous_correlation_id = get_correlation_id()
        self._previous_request_id = get_request_id()
        self._previous_agent = get_agent_context()
        
        # Set new values
        if self.correlation_id:
            set_correlation_id(self.correlation_id)
        elif self._previous_correlation_id is None:
            # Generate new correlation ID if none exists
            set_correlation_id()
        
        if self.request_id:
            set_request_id(self.request_id)
        
        if self.agent:
            set_agent_context(self.agent)
        
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and restore previous logging context."""
        # Restore previous values
        if self._previous_correlation_id is not None:
            correlation_id_var.set(self._previous_correlation_id)
        else:
            correlation_id_var.set(None)
        
        if self._previous_request_id is not None:
            request_id_var.set(self._previous_request_id)
        else:
            request_id_var.set(None)
        
        if self._previous_agent is not None:
            agent_context_var.set(self._previous_agent)
        else:
            agent_context_var.set(None)


# =========================================================================
# Initialization
# =========================================================================

# Auto-configure logging on module import if structured logging is enabled
if settings.enable_structured_logging:
    setup_logging()

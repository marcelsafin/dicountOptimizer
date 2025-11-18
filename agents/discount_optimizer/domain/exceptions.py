"""Exception hierarchy for the Shopping Optimizer system.

This module defines a hierarchy of exceptions that provide clear error handling
and enable proper error propagation through the agent layers.
"""


class ShoppingOptimizerError(Exception):
    """Base exception for all shopping optimizer errors.

    All custom exceptions in the Shopping Optimizer system inherit from this
    base class, making it easy to catch all system-specific errors.

    Example:
        >>> try:
        ...     # Some operation
        ...     pass
        ... except ShoppingOptimizerError as e:
        ...     # Handle any shopping optimizer error
        ...     print(f"System error: {e}")
    """


class ValidationError(ShoppingOptimizerError):
    """Input validation failed.

    Raised when user input or external data fails validation checks.
    This typically indicates a client error (4xx) rather than a server error.

    Example:
        >>> from .models import Location
        >>> try:
        ...     location = Location(latitude=200, longitude=0)  # Invalid latitude
        ... except ValidationError as e:
        ...     print(f"Invalid input: {e}")
    """


class APIError(ShoppingOptimizerError):
    """External API call failed.

    Raised when an external API (Salling Group, Google Maps, etc.) returns
    an error or is unreachable. This may be temporary and retryable.

    Attributes:
        status_code: HTTP status code if applicable
        response_body: Response body from the API if available

    Example:
        >>> try:
        ...     # API call
        ...     pass
        ... except APIError as e:
        ...     if e.status_code == 429:
        ...         # Handle rate limiting
        ...         pass
    """

    def __init__(
        self, message: str, status_code: int | None = None, response_body: str | None = None
    ):
        """Initialize APIError with optional status code and response body.

        Args:
            message: Error message
            status_code: HTTP status code if applicable
            response_body: Response body from the API if available
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class AgentError(ShoppingOptimizerError):
    """Agent execution failed.

    Raised when an ADK agent fails to execute properly. This could be due to
    model errors, tool execution failures, or internal agent logic issues.

    Example:
        >>> try:
        ...     # Agent execution
        ...     pass
        ... except AgentError as e:
        ...     print(f"Agent failed: {e}")
    """

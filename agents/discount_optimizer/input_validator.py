"""
InputValidator component for Shopping Optimizer.
Validates and sanitizes user inputs according to requirements.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from .google_maps_service import GoogleMapsService
from .models import Location, OptimizationPreferences, Timeframe, UserInput


def get_today() -> date:
    """Get today's date in a timezone-aware manner."""
    return datetime.now(UTC).date()


class ValidationError(Exception):
    """Custom exception for validation errors."""


class InputValidator:
    """Validates and sanitizes user inputs for the Shopping Optimizer."""

    def __init__(self, google_maps_service: GoogleMapsService | None = None):
        """
        Initialize the InputValidator.

        Args:
            google_maps_service: Optional GoogleMapsService instance for geocoding.
                                If not provided, a default instance will be created.
        """
        self.google_maps_service = google_maps_service or GoogleMapsService(use_mock=True)
        # Default location (Copenhagen center) as fallback
        self.default_location = Location(55.6761, 12.5683)

    def validate(self, raw_input: dict[str, Any]) -> UserInput:
        """
        Validate complete user input and return UserInput object.

        Args:
            raw_input: Dictionary containing user input data

        Returns:
            UserInput: Validated user input object

        Raises:
            ValidationError: If any validation fails
        """
        # Validate location
        location = self._validate_location(raw_input.get("location", {}))

        # Validate meal plan
        meal_plan = self._validate_meal_plan(raw_input.get("meal_plan", []))

        # Validate timeframe
        timeframe = self._validate_timeframe(raw_input.get("timeframe", "this week"))

        # Validate preferences
        preferences = self._validate_preferences(raw_input.get("preferences", {}))

        return UserInput(
            location=location, meal_plan=meal_plan, preferences=preferences, timeframe=timeframe
        )

    def _validate_location(self, location_data: dict[str, Any]) -> Location:
        """
        Validate location - accepts either address string or coordinates.
        If address is provided, uses GoogleMapsService to geocode it.

        Args:
            location_data: Dictionary with either:
                          - 'address': string address to geocode
                          - 'latitude' and 'longitude': numeric coordinates

        Returns:
            Location: Validated location object

        Raises:
            ValidationError: If location cannot be determined
        """
        # Check if address is provided
        address = location_data.get("address", "").strip()

        if address:
            # Use geocoding to convert address to coordinates
            try:
                return self.google_maps_service.geocode_address(address)
            except Exception as e:
                # Fallback to default location if geocoding fails
                print(f"Warning: Geocoding failed for address '{address}': {e}")
                print("Using default location (Copenhagen center)")
                return self.default_location

        # Otherwise, try to parse coordinates
        try:
            latitude = float(location_data.get("latitude", 0))
            longitude = float(location_data.get("longitude", 0))
        except (ValueError, TypeError):
            raise ValidationError(
                "Please provide either a valid address or numeric coordinates. "
                "Address example: 'Nørrebrogade 45, København' or coordinates (latitude, longitude)"
            )

        if not self.validate_location_coordinates(latitude, longitude):
            raise ValidationError(
                f"Invalid coordinates: latitude must be between -90 and 90, "
                f"longitude must be between -180 and 180. "
                f"Got latitude={latitude}, longitude={longitude}. "
                f"Alternatively, provide an address string."
            )

        return Location(latitude=latitude, longitude=longitude)

    def validate_location_coordinates(self, lat: float, lon: float) -> bool:
        """
        Validate latitude and longitude ranges.

        Args:
            lat: Latitude value
            lon: Longitude value

        Returns:
            bool: True if coordinates are valid, False otherwise
        """
        return -90 <= lat <= 90 and -180 <= lon <= 180

    def _validate_meal_plan(self, meal_plan: Any) -> list[str]:
        """
        Validate meal plan - now optional (AI will suggest if empty).

        Args:
            meal_plan: Meal plan data (should be a list of strings)

        Returns:
            List[str]: Validated meal plan (can be empty for AI suggestions)

        Raises:
            ValidationError: If meal plan format is invalid
        """
        if not isinstance(meal_plan, list):
            raise ValidationError("Meal plan must be a list")

        # Filter out empty strings and strip whitespace
        return [meal.strip() for meal in meal_plan if isinstance(meal, str) and meal.strip()]

        # Empty meal plan is now OK - AI will suggest meals

    def validate_meal_plan(self, meals: list[str]) -> bool:
        """
        Check if meal plan is non-empty.

        Args:
            meals: List of meal names

        Returns:
            bool: True if meal plan is valid (non-empty), False otherwise
        """
        return isinstance(meals, list) and len(meals) > 0

    def _validate_timeframe(self, timeframe_str: str) -> Timeframe:
        """
        Parse and validate timeframe string.

        Args:
            timeframe_str: Timeframe string (e.g., "this week", "next 7 days")

        Returns:
            Timeframe: Validated timeframe object

        Raises:
            ValidationError: If timeframe cannot be parsed
        """
        try:
            return self.parse_timeframe(timeframe_str)
        except Exception as e:
            raise ValidationError(f"Invalid timeframe: {e!s}")

    def parse_timeframe(self, timeframe: str) -> Timeframe:
        """
        Convert timeframe string to date range.

        Args:
            timeframe: String describing the timeframe

        Returns:
            Timeframe: Object with start_date and end_date

        Raises:
            ValueError: If timeframe format is not recognized
        """
        today = get_today()
        timeframe_lower = timeframe.lower().strip()

        if timeframe_lower in ["this week", "denna vecka"]:
            # Start from today, end 7 days from now
            start_date = today
            end_date = today + timedelta(days=7)
        elif timeframe_lower in ["next week", "nästa vecka"]:
            # Start from next Monday, end 7 days later
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            start_date = today + timedelta(days=days_until_monday)
            end_date = start_date + timedelta(days=7)
        elif "next" in timeframe_lower and "days" in timeframe_lower:
            # Parse "next X days"
            try:
                parts = timeframe_lower.split()
                days_index = parts.index("next") + 1
                num_days = int(parts[days_index])
                start_date = today
                end_date = today + timedelta(days=num_days)
            except (ValueError, IndexError):
                raise ValueError(f"Cannot parse timeframe: {timeframe}")
        elif timeframe_lower in ["today", "idag"]:
            start_date = today
            end_date = today
        elif timeframe_lower in ["tomorrow", "imorgon"]:
            start_date = today + timedelta(days=1)
            end_date = today + timedelta(days=1)
        else:
            # Default to this week if format not recognized
            start_date = today
            end_date = today + timedelta(days=7)

        return Timeframe(start_date=start_date, end_date=end_date)

    def _validate_preferences(self, preferences_data: dict[str, Any]) -> OptimizationPreferences:
        """
        Validate optimization preferences.

        Args:
            preferences_data: Dictionary with preference flags

        Returns:
            OptimizationPreferences: Validated preferences object

        Raises:
            ValidationError: If no preferences are selected
        """
        maximize_savings = bool(preferences_data.get("maximize_savings", False))
        minimize_stores = bool(preferences_data.get("minimize_stores", False))
        prefer_organic = bool(preferences_data.get("prefer_organic", False))

        if not self.validate_preferences(maximize_savings, minimize_stores, prefer_organic):
            raise ValidationError(
                "At least one optimization preference must be selected "
                "(maximize_savings, minimize_stores, or prefer_organic)"
            )

        return OptimizationPreferences(
            maximize_savings=maximize_savings,
            minimize_stores=minimize_stores,
            prefer_organic=prefer_organic,
        )

    def validate_preferences(
        self, maximize_savings: bool, minimize_stores: bool, prefer_organic: bool
    ) -> bool:
        """
        Ensure at least one preference is selected.

        Args:
            maximize_savings: Whether to maximize savings
            minimize_stores: Whether to minimize number of stores
            prefer_organic: Whether to prefer organic products

        Returns:
            bool: True if at least one preference is selected, False otherwise
        """
        return maximize_savings or minimize_stores or prefer_organic

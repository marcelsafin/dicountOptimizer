"""
InputValidation Service - Input validation using Pydantic and geocoding.

This module implements the InputValidation service with:
- Typed validation using Pydantic models
- Address validation via GeocodingService
- Structured logging with agent context
- Comprehensive input validation for all user inputs
- Typed ValidationError responses on failures

Requirements: 1.4, 2.1, 2.3, 4.4
"""

from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel, Field, field_validator, ValidationInfo

from ..config import settings
from ..domain.exceptions import ValidationError as DomainValidationError
from ..domain.models import Location, Timeframe, OptimizationPreferences
from ..domain.protocols import GeocodingService
from ..logging import get_logger, set_agent_context

# Get logger for this module
logger = get_logger(__name__)


class ValidationInput(BaseModel):
    """
    Input model for validation tool.
    
    Attributes:
        address: User's address or location description
        latitude: Optional latitude if coordinates are provided directly
        longitude: Optional longitude if coordinates are provided directly
        meal_plan: List of meal names or descriptions
        timeframe: Shopping timeframe description (e.g., "this week", "next 3 days")
        maximize_savings: Whether to prioritize maximum cost savings
        minimize_stores: Whether to prioritize shopping at fewer stores
        prefer_organic: Whether to prioritize organic products
        search_radius_km: Optional search radius in kilometers
        num_meals: Optional number of meals to suggest
    
    Example:
        >>> input_data = ValidationInput(
        ...     address="Nørrebrogade 20, Copenhagen",
        ...     meal_plan=["Taco Tuesday", "Pasta Night"],
        ...     timeframe="this week",
        ...     maximize_savings=True
        ... )
    """
    address: str | None = Field(
        default=None,
        description="User's address or location description",
        max_length=500
    )
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="Latitude in degrees (if coordinates provided directly)"
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Longitude in degrees (if coordinates provided directly)"
    )
    meal_plan: list[str] = Field(
        default_factory=list,
        description="List of meal names or descriptions",
        max_length=20
    )
    timeframe: str = Field(
        default="this week",
        description="Shopping timeframe description",
        max_length=100
    )
    maximize_savings: bool = Field(
        default=True,
        description="Prioritize maximum cost savings"
    )
    minimize_stores: bool = Field(
        default=False,
        description="Prioritize shopping at fewer stores"
    )
    prefer_organic: bool = Field(
        default=False,
        description="Prioritize organic products"
    )
    search_radius_km: float | None = Field(
        default=None,
        gt=0,
        le=50,
        description="Search radius in kilometers"
    )
    num_meals: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description="Number of meals to suggest"
    )
    
    @field_validator('meal_plan')
    @classmethod
    def validate_meal_plan_items(cls, v: list[str]) -> list[str]:
        """Ensure meal plan items are non-empty strings."""
        if v:
            # Filter out empty strings
            valid_meals = [meal.strip() for meal in v if meal and meal.strip()]
            return valid_meals
        return v


class ValidationOutput(BaseModel):
    """
    Output model from validation tool.
    
    Attributes:
        is_valid: Whether the input passed all validation checks
        location: Validated location with coordinates
        timeframe: Validated timeframe with start and end dates
        preferences: Validated optimization preferences
        search_radius_km: Validated search radius
        num_meals: Validated number of meals to suggest
        meal_plan: Validated meal plan (empty if AI suggestions requested)
        validation_errors: List of validation error messages (if any)
        warnings: List of non-critical warnings
    
    Example:
        >>> output = ValidationOutput(
        ...     is_valid=True,
        ...     location=Location(latitude=55.6761, longitude=12.5683),
        ...     timeframe=Timeframe(start_date=date.today(), end_date=date.today() + timedelta(days=7)),
        ...     preferences=OptimizationPreferences(maximize_savings=True),
        ...     search_radius_km=5.0,
        ...     num_meals=3,
        ...     meal_plan=[],
        ...     validation_errors=[],
        ...     warnings=[]
        ... )
    """
    is_valid: bool = Field(description="Whether input passed all validation checks")
    location: Location | None = Field(
        default=None,
        description="Validated location with coordinates"
    )
    timeframe: Timeframe | None = Field(
        default=None,
        description="Validated timeframe with start and end dates"
    )
    preferences: OptimizationPreferences | None = Field(
        default=None,
        description="Validated optimization preferences"
    )
    search_radius_km: float = Field(
        default=5.0,
        description="Validated search radius in kilometers"
    )
    num_meals: int = Field(
        default=3,
        description="Validated number of meals to suggest"
    )
    meal_plan: list[str] = Field(
        default_factory=list,
        description="Validated meal plan (empty if AI suggestions requested)"
    )
    validation_errors: list[str] = Field(
        default_factory=list,
        description="List of validation error messages"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of non-critical warnings"
    )


class InputValidationService:
    """
    Service for comprehensive input validation.
    
    This service validates all user inputs before processing:
    - Location validation (address geocoding or coordinate validation)
    - Timeframe parsing and validation
    - Optimization preferences validation
    - Meal plan validation
    - Business rule validation (search radius, number of meals, etc.)
    
    The service uses Pydantic validators for type safety and injects a
    GeocodingService for address validation. On validation failures, it
    returns typed ValidationError responses with clear error messages.
    
    The service follows best practices:
    - Uses Pydantic for all data validation
    - Implements dependency injection for external services
    - Includes structured logging
    - Returns typed error responses
    - Validates at service boundaries
    
    Example:
        >>> from agents.discount_optimizer.infrastructure.google_maps_repository import GoogleMapsRepository
        >>> geocoding_service = GoogleMapsRepository()
        >>> service = InputValidationService(geocoding_service=geocoding_service)
        >>> input_data = ValidationInput(
        ...     address="Nørrebrogade 20, Copenhagen",
        ...     timeframe="this week",
        ...     maximize_savings=True
        ... )
        >>> output = await agent.run(input_data)
        >>> if output.is_valid:
        ...     print(f"Location: {output.location}")
    
    Requirements: 1.4, 2.1, 2.3, 4.4
    """
    
    def __init__(self, geocoding_service: GeocodingService):
        """
        Initialize InputValidation service with geocoding service.
        
        Args:
            geocoding_service: Service for address geocoding and distance calculation
        
        Raises:
            TypeError: If geocoding_service doesn't implement GeocodingService protocol
        """
        # Set agent context for logging
        set_agent_context('input_validation')
        
        # Validate that geocoding_service implements the protocol
        if not isinstance(geocoding_service, GeocodingService):
            raise TypeError(
                f"geocoding_service must implement GeocodingService protocol, "
                f"got {type(geocoding_service).__name__}"
            )
        
        self.geocoding_service = geocoding_service
        
        logger.info(
            "input_validation_service_initialized",
            geocoding_service=type(geocoding_service).__name__
        )
    
    async def run(self, input_data: ValidationInput) -> ValidationOutput:
        """
        Run the input validation service with input data.
        
        This is the main entry point for the service. It performs comprehensive
        validation of all user inputs and returns structured output with
        validation results.
        
        Args:
            input_data: User input data to validate
        
        Returns:
            Structured output with validation results and validated data
        
        Requirements: 1.4, 2.1, 2.3, 4.4
        """
        logger.info(
            "input_validation_started",
            has_address=bool(input_data.address),
            has_coordinates=bool(input_data.latitude and input_data.longitude),
            timeframe=input_data.timeframe,
            num_meals_in_plan=len(input_data.meal_plan)
        )
        
        validation_errors: list[str] = []
        warnings: list[str] = []
        
        # Validate location
        location = await self._validate_location(
            input_data,
            validation_errors,
            warnings
        )
        
        # Validate timeframe
        timeframe = self._validate_timeframe(
            input_data.timeframe,
            validation_errors,
            warnings
        )
        
        # Validate preferences
        preferences = self._validate_preferences(
            input_data,
            validation_errors,
            warnings
        )
        
        # Validate search radius
        search_radius_km = self._validate_search_radius(
            input_data.search_radius_km,
            validation_errors,
            warnings
        )
        
        # Validate meal plan
        meal_plan = self._validate_meal_plan(
            input_data.meal_plan,
            validation_errors,
            warnings
        )
        
        # Validate number of meals
        num_meals = self._validate_num_meals(
            input_data.num_meals,
            len(meal_plan),
            validation_errors,
            warnings
        )
        
        # Determine if validation passed
        is_valid = len(validation_errors) == 0
        
        output = ValidationOutput(
            is_valid=is_valid,
            location=location,
            timeframe=timeframe,
            preferences=preferences,
            search_radius_km=search_radius_km,
            num_meals=num_meals,
            meal_plan=meal_plan,
            validation_errors=validation_errors,
            warnings=warnings
        )
        
        if is_valid:
            logger.info(
                "input_validation_completed",
                is_valid=True,
                warnings_count=len(warnings)
            )
        else:
            logger.warning(
                "input_validation_failed",
                is_valid=False,
                errors_count=len(validation_errors),
                warnings_count=len(warnings),
                errors=validation_errors
            )
        
        return output
    
    async def _validate_location(
        self,
        input_data: ValidationInput,
        validation_errors: list[str],
        warnings: list[str]
    ) -> Location | None:
        """
        Validate location from address or coordinates.
        
        Args:
            input_data: User input data
            validation_errors: List to append validation errors to
            warnings: List to append warnings to
        
        Returns:
            Validated Location object or None if validation fails
        
        Requirements: 1.4, 4.4
        """
        # Check if coordinates are provided directly
        if input_data.latitude is not None and input_data.longitude is not None:
            try:
                location = Location(
                    latitude=input_data.latitude,
                    longitude=input_data.longitude
                )
                logger.debug(
                    "location_validated_from_coordinates",
                    latitude=location.latitude,
                    longitude=location.longitude
                )
                return location
            except Exception as e:
                validation_errors.append(
                    f"Invalid coordinates: {str(e)}"
                )
                return None
        
        # Check if address is provided
        if input_data.address:
            try:
                location = await self.geocoding_service.geocode_address(
                    input_data.address
                )
                logger.debug(
                    "location_validated_from_address",
                    address=input_data.address,
                    latitude=location.latitude,
                    longitude=location.longitude
                )
                return location
            except Exception as e:
                validation_errors.append(
                    f"Failed to geocode address '{input_data.address}': {str(e)}"
                )
                return None
        
        # Neither coordinates nor address provided
        validation_errors.append(
            "Location is required: provide either 'address' or both 'latitude' and 'longitude'"
        )
        return None
    
    def _validate_timeframe(
        self,
        timeframe_str: str,
        validation_errors: list[str],
        warnings: list[str]
    ) -> Timeframe | None:
        """
        Validate and parse timeframe string.
        
        Supports common timeframe descriptions:
        - "today"
        - "this week" / "next week"
        - "next 3 days" / "next 7 days"
        - "3 days" / "7 days"
        
        Args:
            timeframe_str: Timeframe description string
            validation_errors: List to append validation errors to
            warnings: List to append warnings to
        
        Returns:
            Validated Timeframe object or None if validation fails
        
        Requirements: 1.4, 4.4
        """
        try:
            today = date.today()
            timeframe_lower = timeframe_str.lower().strip()
            
            # Parse common timeframe patterns
            if timeframe_lower == "today":
                start_date = today
                end_date = today
            elif timeframe_lower in ["this week", "week"]:
                start_date = today
                end_date = today + timedelta(days=7)
            elif timeframe_lower == "next week":
                start_date = today + timedelta(days=7)
                end_date = today + timedelta(days=14)
            elif "next" in timeframe_lower and "day" in timeframe_lower:
                # Extract number of days (e.g., "next 3 days")
                import re
                match = re.search(r'(\d+)\s*day', timeframe_lower)
                if match:
                    days = int(match.group(1))
                    if days > 30:
                        validation_errors.append(
                            f"Timeframe too long: maximum 30 days, got {days} days"
                        )
                        return None
                    start_date = today
                    end_date = today + timedelta(days=days)
                else:
                    # Default to 7 days
                    start_date = today
                    end_date = today + timedelta(days=7)
                    warnings.append(
                        f"Could not parse timeframe '{timeframe_str}', defaulting to 7 days"
                    )
            elif "day" in timeframe_lower:
                # Extract number of days (e.g., "3 days", "7 days")
                import re
                match = re.search(r'(\d+)\s*day', timeframe_lower)
                if match:
                    days = int(match.group(1))
                    if days > 30:
                        validation_errors.append(
                            f"Timeframe too long: maximum 30 days, got {days} days"
                        )
                        return None
                    start_date = today
                    end_date = today + timedelta(days=days)
                else:
                    # Default to 7 days
                    start_date = today
                    end_date = today + timedelta(days=7)
                    warnings.append(
                        f"Could not parse timeframe '{timeframe_str}', defaulting to 7 days"
                    )
            else:
                # Default to 7 days
                start_date = today
                end_date = today + timedelta(days=7)
                warnings.append(
                    f"Could not parse timeframe '{timeframe_str}', defaulting to 7 days"
                )
            
            # Create and validate Timeframe object
            timeframe = Timeframe(start_date=start_date, end_date=end_date)
            
            logger.debug(
                "timeframe_validated",
                timeframe_str=timeframe_str,
                start_date=str(start_date),
                end_date=str(end_date),
                days=(end_date - start_date).days
            )
            
            return timeframe
            
        except Exception as e:
            validation_errors.append(
                f"Failed to parse timeframe '{timeframe_str}': {str(e)}"
            )
            return None
    
    def _validate_preferences(
        self,
        input_data: ValidationInput,
        validation_errors: list[str],
        warnings: list[str]
    ) -> OptimizationPreferences | None:
        """
        Validate optimization preferences.
        
        Args:
            input_data: User input data
            validation_errors: List to append validation errors to
            warnings: List to append warnings to
        
        Returns:
            Validated OptimizationPreferences object or None if validation fails
        
        Requirements: 1.4, 4.4
        """
        try:
            preferences = OptimizationPreferences(
                maximize_savings=input_data.maximize_savings,
                minimize_stores=input_data.minimize_stores,
                prefer_organic=input_data.prefer_organic
            )
            
            logger.debug(
                "preferences_validated",
                maximize_savings=preferences.maximize_savings,
                minimize_stores=preferences.minimize_stores,
                prefer_organic=preferences.prefer_organic
            )
            
            return preferences
            
        except Exception as e:
            validation_errors.append(
                f"Invalid optimization preferences: {str(e)}"
            )
            return None
    
    def _validate_search_radius(
        self,
        search_radius_km: float | None,
        validation_errors: list[str],
        warnings: list[str]
    ) -> float:
        """
        Validate search radius.
        
        Args:
            search_radius_km: User-provided search radius or None
            validation_errors: List to append validation errors to
            warnings: List to append warnings to
        
        Returns:
            Validated search radius in kilometers
        
        Requirements: 1.4, 4.4
        """
        if search_radius_km is None:
            # Use default from settings
            radius = settings.default_search_radius_km
            logger.debug(
                "search_radius_defaulted",
                radius_km=radius
            )
            return radius
        
        # Validate range
        if search_radius_km <= 0:
            validation_errors.append(
                f"Search radius must be positive, got {search_radius_km} km"
            )
            return settings.default_search_radius_km
        
        if search_radius_km > 50:
            warnings.append(
                f"Search radius {search_radius_km} km is very large, "
                f"capping at 50 km"
            )
            return 50.0
        
        logger.debug(
            "search_radius_validated",
            radius_km=search_radius_km
        )
        
        return search_radius_km
    
    def _validate_meal_plan(
        self,
        meal_plan: list[str],
        validation_errors: list[str],
        warnings: list[str]
    ) -> list[str]:
        """
        Validate meal plan.
        
        Args:
            meal_plan: User-provided meal plan
            validation_errors: List to append validation errors to
            warnings: List to append warnings to
        
        Returns:
            Validated meal plan (may be empty if AI suggestions requested)
        
        Requirements: 1.4, 4.4
        """
        if not meal_plan:
            # Empty meal plan means AI suggestions will be used
            logger.debug("meal_plan_empty_ai_suggestions_will_be_used")
            return []
        
        # Validate meal names
        validated_meals = []
        for meal in meal_plan:
            meal_stripped = meal.strip()
            if not meal_stripped:
                warnings.append("Skipping empty meal name in meal plan")
                continue
            
            if len(meal_stripped) > 200:
                warnings.append(
                    f"Meal name too long (max 200 chars): '{meal_stripped[:50]}...'"
                )
                continue
            
            validated_meals.append(meal_stripped)
        
        if len(validated_meals) > 20:
            warnings.append(
                f"Meal plan has {len(validated_meals)} meals, "
                f"limiting to 20 meals"
            )
            validated_meals = validated_meals[:20]
        
        logger.debug(
            "meal_plan_validated",
            num_meals=len(validated_meals)
        )
        
        return validated_meals
    
    def _validate_num_meals(
        self,
        num_meals: int | None,
        meal_plan_length: int,
        validation_errors: list[str],
        warnings: list[str]
    ) -> int:
        """
        Validate number of meals to suggest.
        
        Args:
            num_meals: User-provided number of meals or None
            meal_plan_length: Length of validated meal plan
            validation_errors: List to append validation errors to
            warnings: List to append warnings to
        
        Returns:
            Validated number of meals to suggest
        
        Requirements: 1.4, 4.4
        """
        # If meal plan is provided, use its length
        if meal_plan_length > 0:
            logger.debug(
                "num_meals_from_meal_plan",
                num_meals=meal_plan_length
            )
            return meal_plan_length
        
        # If num_meals is provided, validate it
        if num_meals is not None:
            if num_meals < 1:
                validation_errors.append(
                    f"Number of meals must be at least 1, got {num_meals}"
                )
                return 3  # Default
            
            if num_meals > 10:
                warnings.append(
                    f"Number of meals {num_meals} is very large, capping at 10"
                )
                return 10
            
            logger.debug(
                "num_meals_validated",
                num_meals=num_meals
            )
            return num_meals
        
        # Default to 3 meals
        logger.debug("num_meals_defaulted", num_meals=3)
        return 3

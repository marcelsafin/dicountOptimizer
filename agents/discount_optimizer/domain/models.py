"""Core domain models with Pydantic validation.

This module defines all data models for the Shopping Optimizer system with
comprehensive type safety and validation using Pydantic.
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, ValidationInfo
from datetime import date
from typing import Annotated
from decimal import Decimal


class Location(BaseModel):
    """Geographic location with validated coordinates.
    
    Attributes:
        latitude: Latitude in degrees, must be between -90 and 90
        longitude: Longitude in degrees, must be between -180 and 180
    
    Example:
        >>> location = Location(latitude=55.6761, longitude=12.5683)
        >>> location.latitude
        55.6761
    """
    model_config = ConfigDict(frozen=True)  # Immutable
    
    latitude: Annotated[float, Field(ge=-90, le=90, description="Latitude in degrees")]
    longitude: Annotated[float, Field(ge=-180, le=180, description="Longitude in degrees")]


class Timeframe(BaseModel):
    """Shopping timeframe with validation.
    
    Attributes:
        start_date: Start date of shopping period
        end_date: End date of shopping period (must be after start_date)
    
    Example:
        >>> from datetime import date
        >>> timeframe = Timeframe(
        ...     start_date=date(2025, 11, 14),
        ...     end_date=date(2025, 11, 21)
        ... )
    """
    model_config = ConfigDict(frozen=True)
    
    start_date: date = Field(description="Start date of shopping period")
    end_date: date = Field(description="End date of shopping period")
    
    @field_validator('end_date')
    @classmethod
    def end_after_start(cls, v: date, info: ValidationInfo) -> date:
        """Validate that end_date is after start_date."""
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class OptimizationPreferences(BaseModel):
    """User preferences for optimization.
    
    Attributes:
        maximize_savings: Prioritize maximum cost savings
        minimize_stores: Prioritize shopping at fewer stores
        prefer_organic: Prioritize organic products
    
    At least one preference must be True.
    
    Example:
        >>> prefs = OptimizationPreferences(
        ...     maximize_savings=True,
        ...     minimize_stores=False,
        ...     prefer_organic=False
        ... )
    """
    model_config = ConfigDict(frozen=True)
    
    maximize_savings: bool = Field(default=True, description="Prioritize maximum cost savings")
    minimize_stores: bool = Field(default=False, description="Prioritize shopping at fewer stores")
    prefer_organic: bool = Field(default=False, description="Prioritize organic products")
    
    @model_validator(mode='after')
    def at_least_one_preference(self) -> 'OptimizationPreferences':
        """Validate that at least one preference is True."""
        if not (self.maximize_savings or self.minimize_stores or self.prefer_organic):
            raise ValueError('At least one optimization preference must be True')
        return self


class DiscountItem(BaseModel):
    """Discounted product with full type safety.
    
    Attributes:
        product_name: Name of the product
        store_name: Name of the store offering the discount
        store_location: Geographic location of the store
        original_price: Original price before discount (must be positive)
        discount_price: Discounted price (must be less than original_price)
        discount_percent: Discount percentage (0-100)
        expiration_date: Date when the discount expires
        is_organic: Whether the product is organic
        store_address: Physical address of the store
        travel_distance_km: Distance to store in kilometers
        travel_time_minutes: Estimated travel time to store in minutes
    
    Example:
        >>> from decimal import Decimal
        >>> from datetime import date
        >>> item = DiscountItem(
        ...     product_name="Organic Milk",
        ...     store_name="Føtex",
        ...     store_location=Location(latitude=55.6761, longitude=12.5683),
        ...     original_price=Decimal("25.00"),
        ...     discount_price=Decimal("18.75"),
        ...     discount_percent=25.0,
        ...     expiration_date=date(2025, 11, 20),
        ...     is_organic=True
        ... )
    """
    product_name: str = Field(min_length=1, max_length=200, description="Name of the product")
    store_name: str = Field(min_length=1, max_length=100, description="Name of the store")
    store_location: Location = Field(description="Geographic location of the store")
    original_price: Annotated[Decimal, Field(gt=0, decimal_places=2, description="Original price before discount")]
    discount_price: Annotated[Decimal, Field(gt=0, decimal_places=2, description="Discounted price")]
    discount_percent: Annotated[float, Field(ge=0, le=100, description="Discount percentage")]
    expiration_date: date = Field(description="Date when the discount expires")
    is_organic: bool = Field(description="Whether the product is organic")
    store_address: str = Field(default="", description="Physical address of the store")
    travel_distance_km: Annotated[float, Field(ge=0, description="Distance to store in kilometers")] = 0.0
    travel_time_minutes: Annotated[float, Field(ge=0, description="Estimated travel time in minutes")] = 0.0
    
    @field_validator('discount_price')
    @classmethod
    def discount_less_than_original(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        """Validate that discount_price is less than original_price."""
        if 'original_price' in info.data and v >= info.data['original_price']:
            raise ValueError('discount_price must be less than original_price')
        return v


class Purchase(BaseModel):
    """Recommended purchase with meal association.
    
    Attributes:
        product_name: Name of the product to purchase
        store_name: Name of the store where product should be purchased
        purchase_day: Recommended day to make the purchase
        price: Price of the product
        savings: Amount saved compared to regular price
        meal_association: Name of the meal this purchase is associated with
    
    Example:
        >>> from decimal import Decimal
        >>> from datetime import date
        >>> purchase = Purchase(
        ...     product_name="Organic Milk",
        ...     store_name="Føtex",
        ...     purchase_day=date(2025, 11, 15),
        ...     price=Decimal("18.75"),
        ...     savings=Decimal("6.25"),
        ...     meal_association="Breakfast Smoothie"
        ... )
    """
    product_name: str = Field(min_length=1, description="Name of the product to purchase")
    store_name: str = Field(min_length=1, description="Name of the store")
    purchase_day: date = Field(description="Recommended day to make the purchase")
    price: Annotated[Decimal, Field(gt=0, decimal_places=2, description="Price of the product")]
    savings: Annotated[Decimal, Field(ge=0, decimal_places=2, description="Amount saved")]
    meal_association: str = Field(min_length=1, description="Associated meal name")


class ShoppingRecommendation(BaseModel):
    """Complete shopping recommendation output.
    
    Attributes:
        purchases: List of recommended purchases
        total_savings: Total amount saved across all purchases
        time_savings: Estimated time saved in minutes
        tips: List of helpful shopping tips
        motivation_message: Motivational message for the user
        stores: List of stores to visit with details
    
    Example:
        >>> from decimal import Decimal
        >>> recommendation = ShoppingRecommendation(
        ...     purchases=[],
        ...     total_savings=Decimal("50.00"),
        ...     time_savings=15.0,
        ...     tips=["Shop early in the morning", "Bring reusable bags"],
        ...     motivation_message="Great job planning ahead!",
        ...     stores=[]
        ... )
    """
    purchases: list[Purchase] = Field(description="List of recommended purchases")
    total_savings: Annotated[Decimal, Field(ge=0, decimal_places=2, description="Total amount saved")]
    time_savings: Annotated[float, Field(ge=0, description="Estimated time saved in minutes")]
    tips: list[str] = Field(description="List of helpful shopping tips")
    motivation_message: str = Field(min_length=1, description="Motivational message")
    stores: list[dict[str, str | float]] = Field(description="List of stores with details")

"""
Data models for the Shopping Optimizer system.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Dict


@dataclass
class Location:
    """Represents a geographic location with coordinates."""
    latitude: float
    longitude: float


@dataclass
class Timeframe:
    """Represents a time period for shopping."""
    start_date: date
    end_date: date


@dataclass
class OptimizationPreferences:
    """User preferences for optimization criteria."""
    maximize_savings: bool
    minimize_stores: bool
    prefer_organic: bool


@dataclass
class UserInput:
    """Complete user input for shopping optimization."""
    location: Location
    meal_plan: List[str]
    preferences: OptimizationPreferences
    timeframe: Timeframe


@dataclass
class DiscountItem:
    """Represents a discounted product at a specific store."""
    product_name: str
    store_name: str
    store_location: Location
    original_price: float
    discount_price: float
    discount_percent: float
    expiration_date: date
    is_organic: bool
    store_address: str = ""
    travel_distance_km: float = 0.0
    travel_time_minutes: float = 0.0


@dataclass
class Purchase:
    """Represents a recommended purchase."""
    product_name: str
    store_name: str
    purchase_day: date
    price: float
    savings: float
    meal_association: str


@dataclass
class ShoppingRecommendation:
    """Complete shopping recommendation output."""
    purchases: List[Purchase]
    total_savings: float
    time_savings: float
    tips: List[str]
    motivation_message: str


# Mock discount data with Danish stores near Copenhagen
# Copenhagen coordinates: approximately 55.6761° N, 12.5683° E
MOCK_DISCOUNTS: List[DiscountItem] = [
    # Netto - Nørrebro (North of Copenhagen center)
    DiscountItem(
        product_name="Tortillas",
        store_name="Netto Nørrebro",
        store_location=Location(55.6872, 12.5537),
        original_price=25.0,
        discount_price=18.0,
        discount_percent=28.0,
        expiration_date=date.today() + timedelta(days=5),
        is_organic=False,
        store_address="Nørrebrogade 45, 2200 København N",
        travel_distance_km=1.5,
        travel_time_minutes=8.0
    ),
    DiscountItem(
        product_name="Hakket oksekød",
        store_name="Netto Nørrebro",
        store_location=Location(55.6872, 12.5537),
        original_price=65.0,
        discount_price=49.0,
        discount_percent=25.0,
        expiration_date=date.today() + timedelta(days=3),
        is_organic=False,
        store_address="Nørrebrogade 45, 2200 København N",
        travel_distance_km=1.5,
        travel_time_minutes=8.0
    ),
    DiscountItem(
        product_name="Ost",
        store_name="Netto Nørrebro",
        store_location=Location(55.6872, 12.5537),
        original_price=45.0,
        discount_price=35.0,
        discount_percent=22.0,
        expiration_date=date.today() + timedelta(days=7),
        is_organic=False,
        store_address="Nørrebrogade 45, 2200 København N",
        travel_distance_km=1.5,
        travel_time_minutes=8.0
    ),
    DiscountItem(
        product_name="Salat",
        store_name="Netto Nørrebro",
        store_location=Location(55.6872, 12.5537),
        original_price=20.0,
        discount_price=15.0,
        discount_percent=25.0,
        expiration_date=date.today() + timedelta(days=2),
        is_organic=True,
        store_address="Nørrebrogade 45, 2200 København N",
        travel_distance_km=1.5,
        travel_time_minutes=8.0
    ),
    
    # Føtex - Vesterbro (West of Copenhagen center)
    DiscountItem(
        product_name="Økologisk hakket oksekød",
        store_name="Føtex Vesterbro",
        store_location=Location(55.6692, 12.5515),
        original_price=85.0,
        discount_price=68.0,
        discount_percent=20.0,
        expiration_date=date.today() + timedelta(days=4),
        is_organic=True,
        store_address="Vesterbrogade 89, 1620 København V",
        travel_distance_km=1.2,
        travel_time_minutes=6.0
    ),
    DiscountItem(
        product_name="Creme fraiche",
        store_name="Føtex Vesterbro",
        store_location=Location(55.6692, 12.5515),
        original_price=22.0,
        discount_price=16.0,
        discount_percent=27.0,
        expiration_date=date.today() + timedelta(days=6),
        is_organic=False,
        store_address="Vesterbrogade 89, 1620 København V",
        travel_distance_km=1.2,
        travel_time_minutes=6.0
    ),
    DiscountItem(
        product_name="Salsa",
        store_name="Føtex Vesterbro",
        store_location=Location(55.6692, 12.5515),
        original_price=30.0,
        discount_price=22.0,
        discount_percent=27.0,
        expiration_date=date.today() + timedelta(days=10),
        is_organic=False,
        store_address="Vesterbrogade 89, 1620 København V",
        travel_distance_km=1.2,
        travel_time_minutes=6.0
    ),
    DiscountItem(
        product_name="Tomater",
        store_name="Føtex Vesterbro",
        store_location=Location(55.6692, 12.5515),
        original_price=25.0,
        discount_price=18.0,
        discount_percent=28.0,
        expiration_date=date.today() + timedelta(days=3),
        is_organic=True,
        store_address="Vesterbrogade 89, 1620 København V",
        travel_distance_km=1.2,
        travel_time_minutes=6.0
    ),
    DiscountItem(
        product_name="Pasta",
        store_name="Føtex Vesterbro",
        store_location=Location(55.6692, 12.5515),
        original_price=18.0,
        discount_price=12.0,
        discount_percent=33.0,
        expiration_date=date.today() + timedelta(days=14),
        is_organic=False,
        store_address="Vesterbrogade 89, 1620 København V",
        travel_distance_km=1.2,
        travel_time_minutes=6.0
    ),
    
    # Rema 1000 - Østerbro (East of Copenhagen center)
    DiscountItem(
        product_name="Tortillas",
        store_name="Rema 1000 Østerbro",
        store_location=Location(55.7008, 12.5731),
        original_price=25.0,
        discount_price=20.0,
        discount_percent=20.0,
        expiration_date=date.today() + timedelta(days=6),
        is_organic=False,
        store_address="Østerbrogade 112, 2100 København Ø",
        travel_distance_km=2.8,
        travel_time_minutes=12.0
    ),
    DiscountItem(
        product_name="Tomatpuré",
        store_name="Rema 1000 Østerbro",
        store_location=Location(55.7008, 12.5731),
        original_price=15.0,
        discount_price=10.0,
        discount_percent=33.0,
        expiration_date=date.today() + timedelta(days=30),
        is_organic=False,
        store_address="Østerbrogade 112, 2100 København Ø",
        travel_distance_km=2.8,
        travel_time_minutes=12.0
    ),
    DiscountItem(
        product_name="Økologisk ost",
        store_name="Rema 1000 Østerbro",
        store_location=Location(55.7008, 12.5731),
        original_price=55.0,
        discount_price=42.0,
        discount_percent=24.0,
        expiration_date=date.today() + timedelta(days=8),
        is_organic=True,
        store_address="Østerbrogade 112, 2100 København Ø",
        travel_distance_km=2.8,
        travel_time_minutes=12.0
    ),
    DiscountItem(
        product_name="Løg",
        store_name="Rema 1000 Østerbro",
        store_location=Location(55.7008, 12.5731),
        original_price=12.0,
        discount_price=8.0,
        discount_percent=33.0,
        expiration_date=date.today() + timedelta(days=5),
        is_organic=False,
        store_address="Østerbrogade 112, 2100 København Ø",
        travel_distance_km=2.8,
        travel_time_minutes=12.0
    ),
    
    # Netto - Amager (South of Copenhagen)
    DiscountItem(
        product_name="Gulerødder",
        store_name="Netto Amager",
        store_location=Location(55.6531, 12.5989),
        original_price=15.0,
        discount_price=10.0,
        discount_percent=33.0,
        expiration_date=date.today() + timedelta(days=4),
        is_organic=False,
        store_address="Amagerbrogade 55, 2300 København S",
        travel_distance_km=3.5,
        travel_time_minutes=15.0
    ),
    DiscountItem(
        product_name="Kartofler",
        store_name="Netto Amager",
        store_location=Location(55.6531, 12.5989),
        original_price=20.0,
        discount_price=14.0,
        discount_percent=30.0,
        expiration_date=date.today() + timedelta(days=7),
        is_organic=False,
        store_address="Amagerbrogade 55, 2300 København S",
        travel_distance_km=3.5,
        travel_time_minutes=15.0
    ),
    DiscountItem(
        product_name="Grøntsagsbouillon",
        store_name="Netto Amager",
        store_location=Location(55.6531, 12.5989),
        original_price=18.0,
        discount_price=13.0,
        discount_percent=28.0,
        expiration_date=date.today() + timedelta(days=60),
        is_organic=False,
        store_address="Amagerbrogade 55, 2300 København S",
        travel_distance_km=3.5,
        travel_time_minutes=15.0
    ),
    DiscountItem(
        product_name="Bønner",
        store_name="Netto Amager",
        store_location=Location(55.6531, 12.5989),
        original_price=12.0,
        discount_price=9.0,
        discount_percent=25.0,
        expiration_date=date.today() + timedelta(days=90),
        is_organic=False,
        store_address="Amagerbrogade 55, 2300 København S",
        travel_distance_km=3.5,
        travel_time_minutes=15.0
    ),
    
    # Føtex - City Center
    DiscountItem(
        product_name="Hvidløg",
        store_name="Føtex City",
        store_location=Location(55.6761, 12.5683),
        original_price=10.0,
        discount_price=7.0,
        discount_percent=30.0,
        expiration_date=date.today() + timedelta(days=5),
        is_organic=False,
        store_address="Frederiksberggade 21, 1459 København K",
        travel_distance_km=0.5,
        travel_time_minutes=3.0
    ),
    DiscountItem(
        product_name="Parmesan",
        store_name="Føtex City",
        store_location=Location(55.6761, 12.5683),
        original_price=48.0,
        discount_price=38.0,
        discount_percent=21.0,
        expiration_date=date.today() + timedelta(days=12),
        is_organic=False,
        store_address="Frederiksberggade 21, 1459 København K",
        travel_distance_km=0.5,
        travel_time_minutes=3.0
    ),
    DiscountItem(
        product_name="Selleri",
        store_name="Føtex City",
        store_location=Location(55.6761, 12.5683),
        original_price=18.0,
        discount_price=13.0,
        discount_percent=28.0,
        expiration_date=date.today() + timedelta(days=3),
        is_organic=True,
        store_address="Frederiksberggade 21, 1459 København K",
        travel_distance_km=0.5,
        travel_time_minutes=3.0
    ),
]


# Meal-to-ingredients mapping database
MEAL_INGREDIENTS: Dict[str, List[str]] = {
    "taco": [
        "tortillas",
        "hakket oksekød",
        "ost",
        "creme fraiche",
        "salsa",
        "salat",
        "tomater"
    ],
    "tacos": [
        "tortillas",
        "hakket oksekød",
        "ost",
        "creme fraiche",
        "salsa",
        "salat",
        "tomater"
    ],
    "pasta": [
        "pasta",
        "tomatpuré",
        "hakket oksekød",
        "parmesan",
        "hvidløg",
        "løg"
    ],
    "pasta bolognese": [
        "pasta",
        "tomatpuré",
        "hakket oksekød",
        "parmesan",
        "hvidløg",
        "løg"
    ],
    "grøntsagssuppe": [
        "grøntsagsbouillon",
        "gulerødder",
        "selleri",
        "løg",
        "kartofler",
        "bønner"
    ],
    "veggie soup": [
        "grøntsagsbouillon",
        "gulerødder",
        "selleri",
        "løg",
        "kartofler",
        "bønner"
    ],
    "vegetable soup": [
        "grøntsagsbouillon",
        "gulerødder",
        "selleri",
        "løg",
        "kartofler",
        "bønner"
    ],
}

"""
Unit tests for core Shopping Optimizer components.

Tests cover:
- InputValidator: coordinate validation, location parsing, preferences validation
- DiscountMatcher: Haversine distance calculations, location filtering
- MealSuggester: prompt building, response parsing
- SavingsCalculator: monetary and time savings calculations
- OutputFormatter: grouping, tips generation, formatting logic

Requirements: All requirements
"""

import unittest
from datetime import date, timedelta
from agents.discount_optimizer.input_validator import InputValidator, ValidationError
from agents.discount_optimizer.discount_matcher import DiscountMatcher
from agents.discount_optimizer.meal_suggester import MealSuggester
from agents.discount_optimizer.savings_calculator import SavingsCalculator
from agents.discount_optimizer.output_formatter import OutputFormatter
from agents.discount_optimizer.models import (
    Location, DiscountItem, Purchase, ShoppingRecommendation,
    OptimizationPreferences, Timeframe
)


class TestInputValidator(unittest.TestCase):
    """Test InputValidator component."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = InputValidator()
    
    def test_validate_location_coordinates_valid(self):
        """Test validation of valid coordinates."""
        # Copenhagen coordinates
        self.assertTrue(self.validator.validate_location_coordinates(55.6761, 12.5683))
        
        # Edge cases
        self.assertTrue(self.validator.validate_location_coordinates(90, 180))
        self.assertTrue(self.validator.validate_location_coordinates(-90, -180))
        self.assertTrue(self.validator.validate_location_coordinates(0, 0))
    
    def test_validate_location_coordinates_invalid(self):
        """Test validation of invalid coordinates."""
        # Latitude out of range
        self.assertFalse(self.validator.validate_location_coordinates(91, 12.5683))
        self.assertFalse(self.validator.validate_location_coordinates(-91, 12.5683))
        
        # Longitude out of range
        self.assertFalse(self.validator.validate_location_coordinates(55.6761, 181))
        self.assertFalse(self.validator.validate_location_coordinates(55.6761, -181))
        
        # Both out of range
        self.assertFalse(self.validator.validate_location_coordinates(100, 200))
    
    def test_validate_location_with_coordinates(self):
        """Test location validation with coordinate dict."""
        location_data = {
            'latitude': 55.6761,
            'longitude': 12.5683
        }
        
        location = self.validator._validate_location(location_data)
        
        self.assertIsInstance(location, Location)
        self.assertEqual(location.latitude, 55.6761)
        self.assertEqual(location.longitude, 12.5683)
    
    def test_validate_location_invalid_coordinates(self):
        """Test location validation with invalid coordinates."""
        location_data = {
            'latitude': 100,
            'longitude': 200
        }
        
        with self.assertRaises(ValidationError):
            self.validator._validate_location(location_data)
    
    def test_validate_preferences_all_selected(self):
        """Test preferences validation with all options selected."""
        self.assertTrue(
            self.validator.validate_preferences(
                maximize_savings=True,
                minimize_stores=True,
                prefer_organic=True
            )
        )
    
    def test_validate_preferences_one_selected(self):
        """Test preferences validation with one option selected."""
        self.assertTrue(
            self.validator.validate_preferences(
                maximize_savings=True,
                minimize_stores=False,
                prefer_organic=False
            )
        )
    
    def test_validate_preferences_none_selected(self):
        """Test preferences validation with no options selected."""
        self.assertFalse(
            self.validator.validate_preferences(
                maximize_savings=False,
                minimize_stores=False,
                prefer_organic=False
            )
        )
    
    def test_parse_timeframe_this_week(self):
        """Test parsing 'this week' timeframe."""
        timeframe = self.validator.parse_timeframe("this week")
        
        self.assertIsInstance(timeframe, Timeframe)
        self.assertEqual(timeframe.start_date, date.today())
        self.assertEqual(timeframe.end_date, date.today() + timedelta(days=7))
    
    def test_parse_timeframe_next_week(self):
        """Test parsing 'next week' timeframe."""
        timeframe = self.validator.parse_timeframe("next week")
        
        self.assertIsInstance(timeframe, Timeframe)
        self.assertGreater(timeframe.start_date, date.today())
        self.assertEqual(
            (timeframe.end_date - timeframe.start_date).days,
            7
        )
    
    def test_parse_timeframe_today(self):
        """Test parsing 'today' timeframe."""
        timeframe = self.validator.parse_timeframe("today")
        
        self.assertEqual(timeframe.start_date, date.today())
        self.assertEqual(timeframe.end_date, date.today())
    
    def test_validate_meal_plan_valid(self):
        """Test meal plan validation with valid list."""
        self.assertTrue(self.validator.validate_meal_plan(["taco", "pasta"]))
    
    def test_validate_meal_plan_empty(self):
        """Test meal plan validation with empty list."""
        self.assertFalse(self.validator.validate_meal_plan([]))


class TestDiscountMatcher(unittest.TestCase):
    """Test DiscountMatcher component."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.matcher = DiscountMatcher(use_real_api=False)
        
        # Test locations
        self.copenhagen_center = Location(55.6761, 12.5683)
        self.norrebro = Location(55.6872, 12.5537)
        self.vesterbro = Location(55.6692, 12.5515)
        
        # Test discount items
        self.discount1 = DiscountItem(
            product_name="Test Product 1",
            store_name="Test Store 1",
            store_location=self.norrebro,
            original_price=50.0,
            discount_price=40.0,
            discount_percent=20.0,
            expiration_date=date.today() + timedelta(days=5),
            is_organic=False
        )
        
        self.discount2 = DiscountItem(
            product_name="Test Product 2",
            store_name="Test Store 2",
            store_location=self.vesterbro,
            original_price=30.0,
            discount_price=20.0,
            discount_percent=33.0,
            expiration_date=date.today() + timedelta(days=3),
            is_organic=True
        )
    
    def test_calculate_distance_same_location(self):
        """Test distance calculation for same location."""
        distance = self.matcher.calculate_distance(
            self.copenhagen_center,
            self.copenhagen_center
        )
        
        self.assertAlmostEqual(distance, 0.0, places=2)
    
    def test_calculate_distance_copenhagen_norrebro(self):
        """Test distance calculation between Copenhagen center and Nørrebro."""
        distance = self.matcher.calculate_distance(
            self.copenhagen_center,
            self.norrebro
        )
        
        # Expected distance is approximately 1.5 km
        self.assertGreater(distance, 1.0)
        self.assertLess(distance, 2.5)
    
    def test_calculate_distance_copenhagen_vesterbro(self):
        """Test distance calculation between Copenhagen center and Vesterbro."""
        distance = self.matcher.calculate_distance(
            self.copenhagen_center,
            self.vesterbro
        )
        
        # Expected distance is approximately 1.2 km
        self.assertGreater(distance, 0.5)
        self.assertLess(distance, 2.0)
    
    def test_calculate_distance_symmetry(self):
        """Test that distance calculation is symmetric."""
        distance1 = self.matcher.calculate_distance(
            self.copenhagen_center,
            self.norrebro
        )
        distance2 = self.matcher.calculate_distance(
            self.norrebro,
            self.copenhagen_center
        )
        
        self.assertAlmostEqual(distance1, distance2, places=5)
    
    def test_filter_by_location_within_radius(self):
        """Test filtering discounts within radius."""
        discounts = [self.discount1, self.discount2]
        
        # Filter with 2km radius from Copenhagen center
        filtered = self.matcher.filter_by_location(
            discounts,
            self.copenhagen_center,
            max_distance_km=2.0
        )
        
        # Both stores should be within 2km
        self.assertEqual(len(filtered), 2)
    
    def test_filter_by_location_outside_radius(self):
        """Test filtering discounts outside radius."""
        discounts = [self.discount1, self.discount2]
        
        # Filter with very small radius
        filtered = self.matcher.filter_by_location(
            discounts,
            self.copenhagen_center,
            max_distance_km=0.5
        )
        
        # No stores should be within 0.5km
        self.assertEqual(len(filtered), 0)
    
    def test_filter_by_timeframe_valid(self):
        """Test filtering discounts within timeframe."""
        discounts = [self.discount1, self.discount2]
        
        timeframe = Timeframe(
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7)
        )
        
        filtered = self.matcher.filter_by_timeframe(discounts, timeframe)
        
        # Both discounts expire within timeframe
        self.assertEqual(len(filtered), 2)
    
    def test_filter_by_timeframe_expired(self):
        """Test filtering expired discounts."""
        expired_discount = DiscountItem(
            product_name="Expired Product",
            store_name="Test Store",
            store_location=self.copenhagen_center,
            original_price=50.0,
            discount_price=40.0,
            discount_percent=20.0,
            expiration_date=date.today() - timedelta(days=1),
            is_organic=False
        )
        
        timeframe = Timeframe(
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7)
        )
        
        filtered = self.matcher.filter_by_timeframe([expired_discount], timeframe)
        
        # Expired discount should be filtered out
        self.assertEqual(len(filtered), 0)


class TestMealSuggester(unittest.TestCase):
    """Test MealSuggester component."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Skip if no API key available
        import os
        if not os.getenv('GOOGLE_API_KEY'):
            self.skipTest("GOOGLE_API_KEY not available")
        
        self.suggester = MealSuggester()
    
    def test_create_prompt_basic(self):
        """Test basic prompt creation."""
        products = ["Tortillas", "Hakket oksekød", "Ost"]
        
        prompt = self.suggester._create_prompt(
            products,
            user_preferences="",
            num_meals=3
        )
        
        self.assertIn("Tortillas", prompt)
        self.assertIn("Hakket oksekød", prompt)
        self.assertIn("Ost", prompt)
        self.assertIn("3", prompt)
    
    def test_create_prompt_with_preferences(self):
        """Test prompt creation with user preferences."""
        products = ["Pasta", "Tomater"]
        preferences = "vegetarian meals"
        
        prompt = self.suggester._create_prompt(
            products,
            user_preferences=preferences,
            num_meals=2
        )
        
        self.assertIn("vegetarian meals", prompt)
    
    def test_create_prompt_with_product_details(self):
        """Test prompt creation with detailed product information."""
        products = ["Tortillas", "Hakket oksekød"]
        product_details = [
            {
                'name': 'Tortillas',
                'expiration_date': date.today() + timedelta(days=1),
                'discount_percent': 30
            },
            {
                'name': 'Hakket oksekød',
                'expiration_date': date.today() + timedelta(days=5),
                'discount_percent': 25
            }
        ]
        
        prompt = self.suggester._create_prompt(
            products,
            user_preferences="",
            num_meals=2,
            product_details=product_details
        )
        
        self.assertIn("URGENT", prompt)
        self.assertIn("30%", prompt)
    
    def test_parse_response_simple(self):
        """Test parsing simple meal list response."""
        response = """1. Taco Tuesday
2. Pasta Bolognese
3. Grøntsagssuppe"""
        
        meals = self.suggester._parse_response(response)
        
        self.assertEqual(len(meals), 3)
        self.assertIn("Taco Tuesday", meals)
        self.assertIn("Pasta Bolognese", meals)
        self.assertIn("Grøntsagssuppe", meals)
    
    def test_parse_response_with_bullets(self):
        """Test parsing response with bullet points."""
        response = """• Morgenmad Burrito
• Hurtig Pasta
• Vegetar Wrap"""
        
        meals = self.suggester._parse_response(response)
        
        self.assertEqual(len(meals), 3)
        self.assertIn("Morgenmad Burrito", meals)
    
    def test_parse_response_mixed_format(self):
        """Test parsing response with mixed formatting."""
        response = """1. Taco
- Pasta
* Suppe"""
        
        meals = self.suggester._parse_response(response)
        
        self.assertEqual(len(meals), 3)
    
    def test_fallback_suggestions(self):
        """Test fallback meal suggestions."""
        products = ["tortillas", "hakket oksekød", "pasta"]
        
        meals = self.suggester._fallback_suggestions(products, num_meals=3)
        
        self.assertEqual(len(meals), 3)
        self.assertIsInstance(meals[0], str)


class TestSavingsCalculator(unittest.TestCase):
    """Test SavingsCalculator component."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = SavingsCalculator()
        
        self.purchase1 = Purchase(
            product_name="Product 1",
            store_name="Store 1",
            purchase_day=date.today(),
            price=40.0,
            savings=10.0,
            meal_association="Taco"
        )
        
        self.purchase2 = Purchase(
            product_name="Product 2",
            store_name="Store 2",
            purchase_day=date.today(),
            price=20.0,
            savings=5.0,
            meal_association="Pasta"
        )
    
    def test_calculate_monetary_savings_single(self):
        """Test monetary savings calculation with single purchase."""
        savings = self.calculator.calculate_monetary_savings([self.purchase1])
        
        self.assertEqual(savings, 10.0)
    
    def test_calculate_monetary_savings_multiple(self):
        """Test monetary savings calculation with multiple purchases."""
        savings = self.calculator.calculate_monetary_savings(
            [self.purchase1, self.purchase2]
        )
        
        self.assertEqual(savings, 15.0)
    
    def test_calculate_monetary_savings_empty(self):
        """Test monetary savings calculation with no purchases."""
        savings = self.calculator.calculate_monetary_savings([])
        
        self.assertEqual(savings, 0.0)
    
    def test_calculate_time_savings_returns_float(self):
        """Test that time savings calculation returns a float."""
        copenhagen = Location(55.6761, 12.5683)
        
        time_savings = self.calculator.calculate_time_savings(
            [self.purchase1],
            copenhagen
        )
        
        self.assertIsInstance(time_savings, float)


class TestOutputFormatter(unittest.TestCase):
    """Test OutputFormatter component."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.formatter = OutputFormatter()
        
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        self.purchase1 = Purchase(
            product_name="Tortillas",
            store_name="Netto",
            purchase_day=today,
            price=18.0,
            savings=7.0,
            meal_association="Taco"
        )
        
        self.purchase2 = Purchase(
            product_name="Pasta",
            store_name="Føtex",
            purchase_day=today,
            price=12.0,
            savings=6.0,
            meal_association="Pasta"
        )
        
        self.purchase3 = Purchase(
            product_name="Ost",
            store_name="Netto",
            purchase_day=tomorrow,
            price=35.0,
            savings=10.0,
            meal_association="Taco"
        )
    
    def test_group_by_store_and_day(self):
        """Test grouping purchases by store and day."""
        purchases = [self.purchase1, self.purchase2, self.purchase3]
        
        grouped = self.formatter.group_by_store_and_day(purchases)
        
        # Should have 2 stores
        self.assertEqual(len(grouped), 2)
        self.assertIn("Netto", grouped)
        self.assertIn("Føtex", grouped)
        
        # Netto should have 2 days
        self.assertEqual(len(grouped["Netto"]), 2)
        
        # Føtex should have 1 day
        self.assertEqual(len(grouped["Føtex"]), 1)
    
    def test_generate_tips_time_sensitive(self):
        """Test tip generation for time-sensitive products."""
        today = date.today()
        
        urgent_purchase = Purchase(
            product_name="Salat",
            store_name="Netto",
            purchase_day=today,
            price=15.0,
            savings=5.0,
            meal_association="Taco"
        )
        
        tips = self.formatter.generate_tips([urgent_purchase])
        
        self.assertGreater(len(tips), 0)
        self.assertLessEqual(len(tips), 3)
    
    def test_generate_tips_organic(self):
        """Test tip generation for organic products."""
        purchase = Purchase(
            product_name="Økologisk ost",
            store_name="Føtex",
            purchase_day=date.today() + timedelta(days=5),
            price=42.0,
            savings=13.0,
            meal_association="Taco"
        )
        
        tips = self.formatter.generate_tips([purchase])
        
        # Should generate tip for organic product with good savings
        self.assertGreater(len(tips), 0)
    
    def test_generate_tips_max_three(self):
        """Test that tips are limited to maximum 3."""
        purchases = [
            Purchase(
                product_name=f"Product {i}",
                store_name=f"Store {i}",
                purchase_day=date.today(),
                price=20.0,
                savings=5.0,
                meal_association="Meal"
            )
            for i in range(10)
        ]
        
        tips = self.formatter.generate_tips(purchases)
        
        self.assertLessEqual(len(tips), 3)
    
    def test_generate_motivation_high_savings(self):
        """Test motivation message for high savings."""
        motivation = self.formatter.generate_motivation(
            total_savings=150.0,
            time_savings=1.5
        )
        
        self.assertIn("150", motivation)
        self.assertIn("kr", motivation)
        self.assertIsInstance(motivation, str)
        self.assertGreater(len(motivation), 10)
    
    def test_generate_motivation_low_savings(self):
        """Test motivation message for low savings."""
        motivation = self.formatter.generate_motivation(
            total_savings=30.0,
            time_savings=0.2
        )
        
        self.assertIn("30", motivation)
        self.assertIsInstance(motivation, str)
    
    def test_format_recommendation_complete(self):
        """Test complete recommendation formatting."""
        recommendation = ShoppingRecommendation(
            purchases=[self.purchase1, self.purchase2],
            total_savings=13.0,
            time_savings=0.5,
            tips=["Tip 1", "Tip 2"],
            motivation_message="Great job!"
        )
        
        output = self.formatter.format_recommendation(recommendation)
        
        # Check for key sections
        self.assertIn("SHOPPING", output)
        self.assertIn("SAVINGS", output)
        self.assertIn("TIPS", output)
        self.assertIn("Netto", output)
        self.assertIn("Føtex", output)
        self.assertIn("13", output)
        self.assertIn("Great job!", output)
    
    def test_format_recommendation_structure(self):
        """Test that formatted output has proper structure."""
        recommendation = ShoppingRecommendation(
            purchases=[self.purchase1],
            total_savings=7.0,
            time_savings=0.3,
            tips=["Tip 1"],
            motivation_message="Well done!"
        )
        
        output = self.formatter.format_recommendation(recommendation)
        
        # Should have multiple lines
        lines = output.split('\n')
        self.assertGreater(len(lines), 10)
        
        # Should have separators
        self.assertIn("=" * 60, output)


if __name__ == '__main__':
    unittest.main()

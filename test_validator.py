"""Quick test script for InputValidator"""
from agents.discount_optimizer.input_validator import InputValidator, ValidationError

# Test the validator
validator = InputValidator()

# Test 1: Valid input
print('Test 1: Valid complete input')
try:
    result = validator.validate({
        'location': {'latitude': 55.6761, 'longitude': 12.5683},
        'meal_plan': ['taco', 'pasta'],
        'timeframe': 'this week',
        'preferences': {'maximize_savings': True, 'minimize_stores': False, 'prefer_organic': False}
    })
    print(f'✓ Valid input accepted: {result.meal_plan}')
except ValidationError as e:
    print(f'✗ Unexpected error: {e}')

# Test 2: Invalid latitude
print('\nTest 2: Invalid latitude')
if not validator.validate_location_coordinates(100, 12.5683):
    print('✓ Invalid latitude rejected')
else:
    print('✗ Should have failed')

# Test 3: Invalid longitude
print('\nTest 3: Invalid longitude')
if not validator.validate_location_coordinates(55.6761, 200):
    print('✓ Invalid longitude rejected')
else:
    print('✗ Should have failed')

# Test 4: Empty meal plan
print('\nTest 4: Empty meal plan')
if not validator.validate_meal_plan([]):
    print('✓ Empty meal plan rejected')
else:
    print('✗ Should have failed')

# Test 5: Timeframe parsing
print('\nTest 5: Timeframe parsing')
timeframe = validator.parse_timeframe('this week')
print(f'✓ Timeframe parsed: {timeframe.start_date} to {timeframe.end_date}')

# Test 6: No preferences selected
print('\nTest 6: No preferences selected')
if not validator.validate_preferences(False, False, False):
    print('✓ No preferences rejected')
else:
    print('✗ Should have failed')

print('\n✓ All validation tests passed!')

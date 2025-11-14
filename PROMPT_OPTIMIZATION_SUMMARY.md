# Gemini Prompt Optimization Summary

## Task 13: Optimize Gemini prompt for better meal suggestions

### Requirements Addressed
- **3.1, 3.2**: Enhanced Gemini API integration with structured prompts
- **7.3**: Prioritization of products expiring soonest

### Improvements Implemented

#### 1. Diverse Meal Types
The optimized prompt now explicitly encourages diverse meal suggestions across different categories:
- **Breakfast** options (e.g., "Morgenmad Burrito")
- **Lunch** ideas
- **Dinner** suggestions
- **Snacks** and light meals
- **Desserts** when appropriate

**Implementation**: Added explicit diversity requirement in prompt with examples spanning different meal times.

#### 2. Dietary Restriction Considerations
The prompt now includes guidance for common dietary needs:
- Vegetarian options (when no meat products are required)
- Quick meals (under 30 minutes)
- Family-friendly options
- Budget-conscious combinations

**Implementation**: Added "Common dietary considerations" section in prompt template.

#### 3. Expiration Date Prioritization
Products are now marked with urgency levels based on expiration dates:
- **[URGENT - expires in X days]**: Products expiring within 2 days
- **[expires soon - X days]**: Products expiring within 5 days
- Regular products: No special marker

**Implementation**: 
- Added `product_details` parameter to `suggest_meals()` method
- Enhanced `_create_prompt()` to calculate days until expiration
- Automatic urgency marker generation based on expiration dates
- Explicit instruction to prioritize urgent products in meal suggestions

#### 4. Enhanced Creativity Instructions
The prompt now includes:
- Clear role definition: "You are a creative chef helping reduce food waste"
- Explicit creativity requirement: "Think beyond obvious combinations"
- Encouragement for inventive flavors and cuisines
- Practical constraints to ensure realistic meal suggestions

#### 5. Discount Visibility
Product discount percentages are now displayed in the prompt:
- Format: `- Hakket oksekød (40% off) [URGENT - expires in 1 days]`
- Helps AI understand which products offer best value
- Encourages suggestions that maximize savings

#### 6. User Preference Integration
Enhanced handling of user preferences:
- Preferences are now explicitly called out in the requirements section
- Better integration with dietary and meal type considerations
- Maintains backward compatibility when no preferences provided

### Code Changes

#### `meal_suggester.py`
1. Added `product_details` optional parameter to `suggest_meals()`
2. Enhanced `_create_prompt()` with:
   - Expiration date parsing and urgency calculation
   - Discount percentage display
   - Structured requirements section
   - Dietary considerations guidance
   - Diverse meal type examples

#### `agent.py`
1. Updated meal suggestion workflow to pass detailed product information:
   - Expiration dates
   - Discount percentages
   - Organic status
   - Store names
2. Maintains backward compatibility with existing code

### Testing

#### Validation Tests
Created `test_prompt_structure.py` to validate:
- ✓ Diverse meal types mentioned in prompt
- ✓ Urgency prioritization included
- ✓ Expiration info displayed
- ✓ Dietary considerations present
- ✓ Creativity encouraged
- ✓ Discount percentages shown
- ✓ Product list properly formatted
- ✓ User preferences integrated
- ✓ Backward compatibility maintained

#### Integration Tests
Created `test_optimized_prompt.py` to test:
- Expiration prioritization with real dates
- Dietary preference handling
- Diverse meal type generation
- Backward compatibility without product details

### Example Prompt Output

```
You are a creative chef helping reduce food waste by suggesting meals using discounted products.

Available products:
- Hakket oksekød (40% off) [URGENT - expires in 1 days]
- Tomater (35% off) [URGENT - expires in 2 days]
- Salat (30% off) [URGENT - expires in 1 days]
- Pasta (15% off)

Task: Suggest 5 diverse and creative meal ideas using these products.

Requirements:
1. DIVERSITY: Include different meal types - breakfast, lunch, dinner, snacks, or desserts
2. URGENCY: Prioritize products marked as URGENT or expiring soon in your meal suggestions
3. CREATIVITY: Think beyond obvious combinations - be inventive with flavors and cuisines
4. PRACTICALITY: Suggest meals that can realistically be made with available products

Common dietary considerations to keep in mind:
- Vegetarian options (if no meat products are needed)
- Quick meals (under 30 minutes)
- Family-friendly options
- Budget-conscious combinations

Output format: Return ONLY 5 meal names, one per line.
Examples: "Morgenmad Burrito", "Hurtig Pasta Carbonara", "Grøntsagssuppe med Brød", "Taco Tuesday"

Meals:
```

### Benefits

1. **Better Food Waste Reduction**: Urgent products are prioritized, reducing waste
2. **More Creative Suggestions**: Diverse meal types and creative combinations
3. **User-Friendly**: Considers dietary needs and preferences
4. **Value Optimization**: Discount visibility helps maximize savings
5. **Backward Compatible**: Works with existing code without breaking changes

### Future Enhancements

Potential improvements for future iterations:
- Add cuisine type preferences (Italian, Asian, Mexican, etc.)
- Include allergen warnings and exclusions
- Add cooking skill level considerations
- Suggest meal prep and batch cooking options
- Include nutritional information when available

# 🤖 AI-Powered Meal Suggestions

## Overview

Shopping Optimizer now uses **Gemini 2.5 Flash** (the latest and most advanced model) to intelligently suggest meals based on current discount campaigns!

## How It Works

### 1. **Scrape Discount Data**
The system loads all available discount products from Danish stores (Netto, Føtex, Rema 1000).

### 2. **AI Meal Generation**
Gemini 2.5 Flash analyzes the discounted products and creates meal suggestions that:
- Use 3-4 of the available discount products
- Match user preferences (if provided)
- Are practical and easy to prepare
- Consider Danish cuisine preferences

### 3. **Optimization**
The suggested meals are then optimized using the multi-criteria optimizer to find the best shopping plan.

## Usage

### Option 1: Let AI Decide (Recommended for Demo!)
Leave the "What do you want to eat?" field **empty** and AI will suggest meals based on current discounts.

```
Location: 55.6761,12.5683
What do you want to eat: [LEAVE EMPTY]
Sliders: Set your preferences
```

### Option 2: Give AI Hints
Describe what you're craving and AI will suggest meals matching your preferences:

```
What do you want to eat: Something healthy and quick
What do you want to eat: Comfort food for the weekend
What do you want to eat: Vegetarian meals
```

### Option 3: Specific Meals (Old Way)
You can still specify exact meals:

```
What do you want to eat: 
Taco
Pasta
Grøntsagssuppe
```

## Technical Implementation

### Components

**MealSuggester** (`agents/discount_optimizer/meal_suggester.py`)
- Uses Gemini 2.5 Flash API (latest model)
- Temperature: 0.7 for creative suggestions
- Max tokens: 500
- Fallback logic if API fails

**Integration** (`agents/discount_optimizer/agent.py`)
- Stage 2.5: AI Meal Suggestion (new!)
- Runs after discount matching, before ingredient mapping
- Extracts available products from discounts
- Calls Gemini with smart prompt
- Falls back to user input if provided

### Prompt Engineering

The system uses a carefully crafted prompt:
```
You are a creative meal planning assistant for a Danish grocery shopping app.

Available products on discount this week:
- Tortillas
- Hakket oksekød
- Ost
- ...

Task: Suggest 3 delicious meals using these discounted products.

User preferences: [if provided]

Requirements:
- Use 3-4 available products per meal
- Practical and easy to prepare
- Consider Danish cuisine
- Return only meal names, one per line
```

## Demo Script for Hackathon

**Show the AI Power:**

1. Open http://localhost:3000
2. Click 📍 to get Copenhagen location
3. **Leave "What do you want to eat?" EMPTY**
4. Set sliders (e.g., Cost: 4.0, Time: 3.0, Quality: 2.0)
5. Click "Optimize My Shopping"
6. **Explain**: "Gemini just analyzed all discount products and suggested these meals!"
7. Show the shopping list with savings

**Alternative Demo:**
1. Type: "Something healthy for the week"
2. Watch Gemini suggest healthy meals using discount products
3. Show optimized shopping plan

## Why This Is Impressive

✅ **Real AI Integration** - Not just keyword matching, actual Gemini API
✅ **Context-Aware** - Suggestions based on actual available discounts
✅ **User-Friendly** - Works with no input, vague input, or specific input
✅ **Production-Ready** - Has fallback logic for reliability
✅ **Hackathon Gold** - Shows advanced use of Google Cloud AI

## API Key Setup

Make sure your `.env` file has:
```
GOOGLE_API_KEY=your_api_key_here
```

## Testing

Test the meal suggester directly:
```python
from agents.discount_optimizer.meal_suggester import MealSuggester

suggester = MealSuggester()
meals = suggester.suggest_meals(
    available_products=["Tortillas", "Hakket oksekød", "Ost", "Salat"],
    user_preferences="Something quick and easy",
    num_meals=3
)
print(meals)
```

## Future Enhancements

- Real-time scraping of actual store websites
- Nutritional analysis of suggested meals
- Dietary restrictions (vegan, gluten-free, etc.)
- Recipe generation with step-by-step instructions
- Image generation of suggested meals

# Frontend Integration Guide

## Overview

The frontend interaction logic has been fully implemented for the Shopping Optimizer. The system now includes:

1. **Flask Backend API** (`app.py`)
2. **Interactive JavaScript** (`static/js/app.js`)
3. **Complete Form Validation**
4. **Real-time Results Display**

## How It Works

### User Flow

1. User enters location (coordinates or city name)
2. User enters meal plan (one meal per line)
3. User selects optimization preferences (Cost, Time, Quality)
4. User clicks "Optimize My Shopping"
5. System validates inputs and shows loading spinner
6. Backend processes optimization
7. Results are displayed with:
   - Shopping list organized by store and day
   - Monetary and time savings
   - Actionable tips
   - Motivational message

### API Endpoint

**POST** `/api/optimize`

**Request Body:**
```json
{
  "location": "55.6761,12.5683",
  "meals": ["taco", "pasta"],
  "preferences": {
    "maximize_savings": true,
    "minimize_stores": true,
    "prefer_organic": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "recommendation": "formatted text...",
  "total_savings": 81.0,
  "time_savings": -1.47,
  "num_purchases": 12
}
```

## Running the Application

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Edit `.env` file and add your Google AI API key:
```
GOOGLE_API_KEY=your_actual_api_key_here
```

### 3. Start the Server

```bash
python3 app.py
```

### 4. Open Browser

Navigate to: http://127.0.0.1:8000

## Testing

### Test Backend Only
```bash
python3 test_agent.py
```

### Test API Integration
```bash
python3 test_api.py
```

## Features Implemented

### Client-Side Validation
- Location field required
- Meal plan required (at least one meal)
- At least one preference must be selected
- Clear error messages displayed for 5 seconds

### Loading States
- Button disabled during processing
- Animated spinner with message
- Results hidden until ready

### Results Display
- Formatted shopping list with store grouping
- Savings summary with monetary and time values
- Tips section with actionable recommendations
- Motivation message
- Smooth scroll to results
- Input values preserved after optimization

### Error Handling
- Network errors caught and displayed
- Server errors shown to user
- Validation errors prevent submission
- Auto-hiding error messages

## Code Structure

### `app.py`
- Flask application setup
- `/` route serves the HTML
- `/api/optimize` POST endpoint handles optimization
- Location parsing (coordinates or city name)
- Input validation
- Calls `optimize_shopping()` function

### `static/js/app.js`
- Form submission handler
- Client-side validation
- API communication with fetch
- Results parsing and display
- HTML formatting with XSS protection
- Tips and motivation extraction
- Loading and error state management

## Next Steps

To complete the full application, implement:
- Task 11: CSS styling enhancements
- Task 12: Integration and end-to-end testing

The core functionality is now complete and ready for testing!

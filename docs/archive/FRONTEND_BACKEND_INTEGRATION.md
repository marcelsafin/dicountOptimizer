# Frontend-Backend Integration Guide

## Overview

The Shopping Optimizer frontend (static/js/app.js) is fully integrated with the modernized backend API that uses Pydantic models and async agent architecture.

## API Response Structure

### Success Response

```json
{
  "success": true,
  "recommendation": {
    "purchases": [
      {
        "product_name": "Organic Tomatoes",
        "store_name": "Føtex Copenhagen",
        "purchase_day": "2025-11-20",
        "price": 25.50,
        "savings": 10.00,
        "meal_association": "Pasta with tomato sauce"
      }
    ],
    "total_savings": 25.00,
    "time_savings": 12.5,
    "tips": [
      "Buy tomatoes on Wednesday for best freshness",
      "Ground beef is 25% off this week"
    ],
    "motivation_message": "Great choices! You'll save 25 kr this week.",
    "stores": [
      {
        "name": "Føtex Copenhagen",
        "address": "Vesterbrogade 123, Copenhagen",
        "latitude": 55.6761,
        "longitude": 12.5683,
        "distance_km": 1.2,
        "items": 1
      }
    ]
  },
  "user_location": {
    "latitude": 55.6761,
    "longitude": 12.5683
  },
  "correlation_id": "uuid-string"
}
```

### Error Response

```json
{
  "success": false,
  "error": "Validation error: Invalid location format",
  "error_type": "validation",
  "correlation_id": "uuid-string"
}
```

Error types:
- `validation`: Input validation errors (400)
- `optimization`: Optimization process errors (500)
- `server`: Unexpected server errors (500)

## Frontend Data Handling

### Date Serialization

Backend dates are serialized to ISO format (YYYY-MM-DD) for JavaScript Date parsing:

```javascript
const date = new Date(purchase.purchase_day); // "2025-11-20"
```

### Decimal Conversion

Backend Decimal fields are automatically converted to float for JSON:

```javascript
const price = parseFloat(recommendation.total_savings); // 25.00
```

### Store Map Display

The frontend uses Leaflet.js to display stores on a map:

```javascript
function displayStoreMap(stores, userLocation) {
  // Creates map centered on user location
  // Adds markers for each store with distance and item count
  // Fits bounds to show all markers
}
```

### Shopping List Grouping

Purchases are grouped by store for better UX:

```javascript
function formatPurchasesHTML(purchases, stores) {
  // Groups purchases by store_name
  // Displays store info (name, distance)
  // Lists products with price and savings
}
```

## Error Handling

The frontend discriminates error types for better user feedback:

```javascript
if (result.error_type === 'validation') {
  errorMessage = `Input validation error: ${result.error}`;
} else if (result.error_type === 'optimization') {
  errorMessage = `Optimization error: ${result.error}`;
} else if (result.error_type === 'server') {
  errorMessage = `Server error: ${result.error}`;
}
```

Correlation IDs are logged for debugging:

```javascript
if (result.correlation_id) {
  console.error('Error correlation ID:', result.correlation_id);
  errorMessage += ` (ID: ${result.correlation_id.substring(0, 8)})`;
}
```

## Form Data Mapping

Frontend form data is mapped to backend API format:

```javascript
{
  location: "55.6761,12.5683" or "Copenhagen",
  meals: ["taco", "pasta"],
  meal_types: ["breakfast", "lunch", "dinner", "snacks"],
  excluded_ingredients: ["nuts", "dairy"],
  preferences: {
    maximize_savings: true,
    minimize_stores: false,
    prefer_organic: false
  },
  preference_weights: {
    cost: 3.5,
    time: 2.0,
    quality: 4.0
  }
}
```

## Testing

Comprehensive integration tests verify:

1. **API Response Structure** (6 tests)
   - All required fields present
   - Correct data types
   - Proper serialization

2. **Error Response Structure** (4 tests)
   - Error types correctly set
   - Correlation IDs present
   - Proper HTTP status codes

3. **Date Serialization** (1 test)
   - ISO format (YYYY-MM-DD)
   - JavaScript Date compatible

4. **Decimal Serialization** (1 test)
   - Decimal → float conversion
   - JSON serializable

5. **Frontend Compatibility** (2 tests)
   - JavaScript parsing works
   - Empty results handled

6. **Correlation ID Propagation** (3 tests)
   - Present in all responses
   - Passed to agent
   - UUID format

Run tests:
```bash
pytest tests/test_frontend_backend_integration.py -v
```

## Compatibility Notes

### Browser Support

- Modern browsers with ES6+ support
- Geolocation API for location detection
- Fetch API for HTTP requests
- Leaflet.js for map display

### API Compatibility

The frontend is compatible with:
- Flask async endpoints (ASGI via WsgiToAsgi)
- Pydantic model serialization
- Structured error responses
- Correlation ID tracing

### Future Enhancements

Potential improvements:
- WebSocket support for real-time updates
- Progressive Web App (PWA) features
- Offline mode with service workers
- Enhanced map features (routing, clustering)

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Ensure Flask CORS is configured if frontend is on different domain
   - Check browser console for specific CORS errors

2. **Date Parsing Issues**
   - Verify dates are in ISO format (YYYY-MM-DD)
   - Check timezone handling if needed

3. **Map Not Displaying**
   - Verify Leaflet.js is loaded
   - Check that stores have latitude/longitude
   - Ensure user_location is valid

4. **Error Messages Not Showing**
   - Check error_type field is present
   - Verify correlation_id is logged
   - Check browser console for JavaScript errors

### Debug Mode

Enable debug logging in browser console:

```javascript
// In app.js, add:
console.log('API Response:', result);
console.log('Recommendation:', result.recommendation);
console.log('Correlation ID:', result.correlation_id);
```

## Requirements Satisfied

- **7.1**: Frontend properly displays all Pydantic model fields
- **10.3**: Error handling with correlation IDs for debugging
- **Task 26**: Complete frontend-backend integration verified with tests

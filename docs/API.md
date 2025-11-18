# API Reference

Base URL: `/api`

## Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/optimize` | **Main Endpoint**. Generates meal plans based on location & preferences. |
| `GET` | `/health` | Basic health check. Returns `200 OK` if alive. |
| `GET` | `/health/detailed` | Checks connections to Salling API, Google Maps, and Cache. |
| `GET` | `/metrics` | Prometheus metrics for monitoring. |

## `/api/optimize`

**Request Body (JSON):**
```json
{
  "address": "Nørrebrogade 10, 2200 København",
  "search_radius_km": 2.0,
  "num_meals": 3,
  "preferences": {
    "maximize_savings": true,
    "minimize_stores": false
  }
}
```

**Response (JSON):**
```json
{
  "recommendations": [
    {
      "store_name": "Netto Nørrebrogade",
      "saved_amount": 45.50,
      "meals": [
        {
          "name": "Spicy Root Vegetable Soup",
          "ingredients": ["Carrots (3kr)", "Potatoes (5kr)"]
        }
      ]
    }
  ]
}
```

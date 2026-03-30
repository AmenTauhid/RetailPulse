# API Specification

Base URL: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs` (Swagger UI)

## Endpoints

### Health

#### `GET /api/v1/health`
Returns API status and whether the ML model is loaded.

**Response:**
```json
{ "status": "healthy", "model_loaded": true }
```

---

### Stores

#### `GET /api/v1/stores`
List all retail stores.

**Response:** Array of store objects.
```json
[
  {
    "id": 1,
    "store_code": "CTC-001",
    "name": "Canadian Tire - Yonge & Eglinton",
    "city": "Toronto",
    "province": "ON",
    "latitude": 43.7066,
    "longitude": -79.3985,
    "store_type": "standard",
    "opened_date": "2018-03-15"
  }
]
```

#### `GET /api/v1/stores/{store_id}`
Get a single store. Returns 404 if not found.

---

### Categories

#### `GET /api/v1/categories`
List all product categories.

**Response:**
```json
[
  {
    "id": 1,
    "name": "Winter Tires",
    "department": "Automotive",
    "is_seasonal": true,
    "peak_season": "winter"
  }
]
```

#### `GET /api/v1/categories/{category_id}/products`
List products in a category.

---

### Historical Data

#### `GET /api/v1/historical/{store_id}/{category_id}`
Daily demand time series.

**Query params:**
- `start_date` (optional, default: 90 days ago)
- `end_date` (optional, default: today)

**Response:**
```json
{
  "store_id": 1,
  "category_id": 1,
  "start_date": "2025-10-01",
  "end_date": "2025-12-31",
  "data": [
    { "date": "2025-10-01", "total_quantity": 8, "total_revenue": 1520.50, "transaction_count": 5 }
  ]
}
```

#### `GET /api/v1/weather/{store_id}`
Recent weather data for a store location.

**Query params:**
- `start_date`, `end_date` (optional)
- `limit` (default: 30, max: 365)

---

### Forecasts

#### `GET /api/v1/forecasts/{store_id}/{category_id}`
Demand forecast with confidence intervals.

**Query params:**
- `days` (default: 14, max: 90)

**Response:**
```json
{
  "store_id": 1,
  "category_id": 1,
  "model_type": "xgboost",
  "forecasts": [
    { "date": "2026-03-29", "predicted_quantity": 2.5, "lower_bound": 0.0, "upper_bound": 4.97 }
  ],
  "model_metrics": { "rmse": 1.6454, "mae": 1.0984, "mape": 48.32, "r2": 0.7461 },
  "feature_importance": { "is_weekend": 0.2068, "rolling_7d_qty": 0.1844 }
}
```

#### `GET /api/v1/model/info`
Model metadata, metrics, and feature importance.

---

### Anomalies

#### `GET /api/v1/anomalies`
Demand anomalies detected by the model.

**Query params:**
- `store_id` (optional)
- `category_id` (optional)
- `severity` (optional: `low`, `medium`, `high`)
- `days` (default: 30, lookback period)
- `limit` (default: 50, max: 200)

**Response:**
```json
{
  "total": 120,
  "anomalies": [
    {
      "store_id": 1,
      "category_id": 8,
      "date": "2025-12-22",
      "actual_quantity": 25,
      "predicted_quantity": 8.5,
      "residual": 16.5,
      "severity": "high",
      "z_score": 3.45,
      "store_name": "Canadian Tire - Yonge & Eglinton",
      "category_name": "Christmas Decor"
    }
  ]
}
```

---

### Insights

#### `GET /api/v1/insights/top-movers`
Categories with biggest demand changes vs prior period.

**Query params:**
- `days` (default: 14, comparison period)
- `limit` (default: 10, max: 50)

#### `GET /api/v1/insights/weather-impact`
Temperature-demand correlation by category.

**Query params:**
- `store_id` (default: 1)

---

### Chat

#### `POST /api/v1/chat`
Conversational AI powered by Claude with tool use.

**Request body:**
```json
{
  "message": "What should I stock more of this weekend?",
  "history": []
}
```

**Response:**
```json
{
  "response": "Based on the data, Winter Tires and Snow Blowers are trending up...",
  "tools_used": ["get_top_categories", "get_weather"]
}
```

---

## Error Responses

All errors follow this shape:
```json
{ "detail": "Store 999 not found" }
```

HTTP status codes: 404 (not found), 422 (validation error), 503 (model not loaded).

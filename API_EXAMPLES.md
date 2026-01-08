# API Usage Examples

## Using cURL

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. Estimate Weight
```bash
curl -X POST "http://localhost:8000/estimate-weight" \
  -H "Content-Type: application/json" \
  -d '{"offer_id": "624730890959"}'
```

## Using Python Requests

```python
import requests
import json

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Estimate weight
response = requests.post(
    "http://localhost:8000/estimate-weight",
    json={"offer_id": "624730890959"}
)

result = response.json()
print(json.dumps(result, indent=2))
```

## Using JavaScript/Node.js

```javascript
// Using fetch
async function estimateWeight(offerId) {
  const response = await fetch('http://localhost:8000/estimate-weight', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ offer_id: offerId })
  });
  
  const data = await response.json();
  console.log(data);
}

estimateWeight('624730890959');
```

## Using Postman

1. **Method**: POST
2. **URL**: `http://localhost:8000/estimate-weight`
3. **Headers**: 
   - Key: `Content-Type`
   - Value: `application/json`
4. **Body** (raw JSON):
```json
{
  "offer_id": "624730890959"
}
```

## Response Structure

```json
{
  "success": true,
  "offer_id": "624730890959",
  "estimated_weights": [
    {
      "skus": [
        {
          "sku_id": "4423361457251",
          "length_cm": 27.28,
          "width_cm": 22.19,
          "height_cm": 6.42,
          "weight_g": 471.4
        }
      ]
    }
  ],
  "preprocessing_stats": {
    "total_skus_before": 10,
    "total_skus_after": 5,
    "skus_removed": 5,
    "duplicate_removal_applied": true
  },
  "model_api_stats": {
    "api_calls_count": 1,
    "input_tokens": 1250,
    "output_tokens": 350,
    "total_tokens": 1600,
    "processing_time_seconds": 2.34,
    "model_name": "claude-sonnet-4-5"
  },
  "raw_data_size_chars": 15420,
  "preprocessed_data_size_chars": 8230
}
```

## Error Responses

### Offer Not Found (404)
```json
{
  "detail": "No product found with offer ID: 123456"
}
```

### Invalid Offer ID (400)
```json
{
  "detail": "Validation error: Invalid offer ID format: abc123"
}
```

### Internal Server Error (500)
```json
{
  "detail": "Internal server error: Connection to database failed"
}
```

## Interactive API Documentation

FastAPI automatically generates interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

You can test the API directly from these interfaces!

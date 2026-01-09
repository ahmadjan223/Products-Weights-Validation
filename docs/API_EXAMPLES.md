# API Usage Guide - Postman

## 1. Single Request (Instant Results - Full Price)

**Endpoint**: `POST /estimate-weight`

### Setup:
- Method: `POST`
- URL: `http://192.168.18.149:8000/estimate-weight`
- Headers: `Content-Type: application/json`

### Request Body:
```json
{
  "offer_id": "624730890959",
  "model_name": "claude-haiku-4-5",
  "drop_similar_skus": true
}
```

### Response:
```json
{
  "success": true,
  "offer_id": "624730890959",
  "skus_were_identical": false,
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
    "model_name": "claude-haiku-4-5"
  },
  "raw_data_size_chars": 15420,
  "preprocessed_data_size_chars": 8230
}
```

---

## 2. Batch Processing (50% Cheaper - Async)

### Step 1: Submit Batch Job

**Endpoint**: `POST /batch-submit`

### Setup:
- Method: `POST`
- URL: `http://192.168.18.149:8000/batch-submit`
- Headers: `Content-Type: application/json`

### Request Body:
```json
{
  "offer_ids": [
    "824023039251",
    "587874692986",
    "598615967048",
    "737556902735",
    "640832010181"
  ],
  "model_name": "claude-haiku-4-5",
  "drop_similar_skus": true
}
```

### Response:
```json
{
  "success": true,
  "batch_id": "msgbatch_01Bm9q5kzNiF4X4QCoa7za42",
  "total_requests": 5,
  "message": "Batch job submitted successfully. 0 offers failed preprocessing.",
  "model_name": "claude-haiku-4-5",
  "drop_similar_skus": true
}
```

**Save the `batch_id` - you'll need it for next steps!**

---

### Step 2: Check Batch Status

**Endpoint**: `GET /batch-status/{batch_id}`

### Setup:
- Method: `GET`
- URL: `http://192.168.18.149:8000/batch-status/msgbatch_01Bm9q5kzNiF4X4QCoa7za42`

### Response:
```json
{
  "success": true,
  "batch_id": "msgbatch_01Bm9q5kzNiF4X4QCoa7za42",
  "status": "ended",
  "request_counts": {
    "processing": 0,
    "succeeded": 5,
    "errored": 0,
    "canceled": 0,
    "expired": 0
  },
  "ended_at": "2026-01-09T10:23:45.123456",
  "expires_at": "2026-02-08T10:22:30.987654"
}
```

**Status values:**
- `queued` - Waiting to process (keep checking)
- `in_progress` - Processing (keep checking)
- `ended` - ✅ Ready! Proceed to Step 3

**Poll every 10-15 seconds until status = "ended"**

---

### Step 3: Get Batch Results

**Endpoint**: `GET /batch-results/{batch_id}`

### Setup:
- Method: `GET`
- URL: `http://192.168.18.149:8000/batch-results/msgbatch_01Bm9q5kzNiF4X4QCoa7za42`

### Response:
```json
{
  "success": true,
  "batch_id": "msgbatch_01Bm9q5kzNiF4X4QCoa7za42",
  "total_offers": 5,
  "successful_offers": 5,
  "failed_offers": 0,
  "results": [
    {
      "success": true,
      "offer_id": "824023039251",
      "estimated_weights": [
        {
          "skus": [
            {
              "skuId": "4847563456789",
              "length_cm": 25.5,
              "width_cm": 18.2,
              "height_cm": 5.8,
              "weight_g": 420.0
            }
          ]
        }
      ],
      "usage": {
        "input_tokens": 1150,
        "output_tokens": 320
      }
    },
    {
      "success": true,
      "offer_id": "587874692986",
      "estimated_weights": [
        {
          "skus": [
            {
              "skuId": "5623451234567",
              "length_cm": 30.0,
              "width_cm": 20.0,
              "height_cm": 8.0,
              "weight_g": 550.0
            }
          ]
        }
      ],
      "usage": {
        "input_tokens": 1200,
        "output_tokens": 340
      }
    }
  ]
}
```

---

## Error Responses

### Offer Not Found (404):
```json
{
  "detail": "No product found with offer ID: 123456"
}
```

### Batch Still Processing (409):
```json
{
  "detail": "Batch is not finished yet (status=in_progress). Retry after it ends."
}
```

### Another Batch Running (409):
```json
{
  "detail": "Another batch is running (batch_id=msgbatch_xxx, status=in_progress). Wait until it ends."
}
```

---

## Notes

- **Single processing**: Use for instant results
- **Batch processing**: Use for bulk (5+ offers) to save 50% on API costs
- **Only one batch** can run at a time
- **Batch timing**: Typically takes 30-90 seconds to complete
- **Valid model names**: `claude-haiku-4-5`, `claude-sonnet-4-5`

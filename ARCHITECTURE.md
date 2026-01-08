# Weight Estimation API - Architecture Overview

## 🎯 System Flow

```
┌─────────────┐
│   Client    │
│  (Request)  │
└──────┬──────┘
       │
       │ POST /estimate-weight
       │ {"offer_id": "624730890959"}
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                     FastAPI Server                       │
│                      (main.py)                          │
└──────┬──────────────────────────────────────────────────┘
       │
       │ Step 1: Data Retrieval
       ▼
┌─────────────────────────────────────────────────────────┐
│           DataRetriever Module                          │
│      (app/modules/data_retrieval.py)                   │
│                                                          │
│  ┌────────────────────────────────────────┐            │
│  │ • Connect to MongoDB                    │            │
│  │ • Query by offer_id                     │            │
│  │ • Return raw product document           │            │
│  └────────────────────────────────────────┘            │
└──────┬──────────────────────────────────────────────────┘
       │
       │ Raw Data (JSON)
       │
       │ Step 2: Preprocessing
       ▼
┌─────────────────────────────────────────────────────────┐
│          DataPreprocessor Module                        │
│       (app/modules/preprocessing.py)                    │
│                                                          │
│  ┌────────────────────────────────────────┐            │
│  │ • Filter relevant fields                │            │
│  │ • Extract SKU attributes                │            │
│  │ • Remove duplicate SKUs                 │            │
│  │ • Track statistics                      │            │
│  └────────────────────────────────────────┘            │
└──────┬──────────────────────────────────────────────────┘
       │
       │ Cleaned Data + Stats
       │
       │ Step 3: Model API Call
       ▼
┌─────────────────────────────────────────────────────────┐
│           ModelAPIClient Module                         │
│        (app/modules/model_api.py)                       │
│                                                          │
│  ┌────────────────────────────────────────┐            │
│  │ • Prepare data format                   │            │
│  │ • Call Claude API                       │            │
│  │ • Parse response                        │            │
│  │ • Track token usage & timing            │            │
│  └────────────────────────────────────────┘            │
└──────┬──────────────────────────────────────────────────┘
       │
       │ Estimated Weights + API Stats
       │
       │ Step 4: Response Building
       ▼
┌─────────────────────────────────────────────────────────┐
│         ResponseBuilder Module                          │
│     (app/modules/response_builder.py)                   │
│                                                          │
│  ┌────────────────────────────────────────┐            │
│  │ • Combine all data                      │            │
│  │ • Add metadata                          │            │
│  │ • Format response                       │            │
│  │ • Validate with Pydantic                │            │
│  └────────────────────────────────────────┘            │
└──────┬──────────────────────────────────────────────────┘
       │
       │ Complete Response
       ▼
┌─────────────────────────────────────────────────────────┐
│                   JSON Response                         │
│                                                          │
│  {                                                       │
│    "success": true,                                      │
│    "offer_id": "624730890959",                          │
│    "estimated_weights": [...],                          │
│    "preprocessing_stats": {...},                        │
│    "model_api_stats": {...},                            │
│    "raw_data_size_chars": 15420,                        │
│    "preprocessed_data_size_chars": 8230                 │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
```

## 🏗️ Module Responsibilities

### 1. Data Retrieval Layer
**File**: `app/modules/data_retrieval.py`

- ✅ MongoDB connection management
- ✅ Query by offer ID
- ✅ Error handling for database issues
- ✅ Connection pooling

**Input**: Offer ID (string)  
**Output**: Raw product document (dict)

---

### 2. Preprocessing Layer
**File**: `app/modules/preprocessing.py`

- ✅ Extract relevant fields (categories, name, SKUs)
- ✅ Parse nested MongoDB structures
- ✅ Remove duplicate SKUs (identical dimensions)
- ✅ Track preprocessing statistics

**Input**: Raw MongoDB document  
**Output**: Cleaned product list + statistics

---

### 3. Model API Layer
**File**: `app/modules/model_api.py`

- ✅ Format data for Claude API
- ✅ Call AI model with system prompt
- ✅ Parse and validate response
- ✅ Track token usage and timing

**Input**: Cleaned product data  
**Output**: Weight estimations + API statistics

---

### 4. Response Building Layer
**File**: `app/modules/response_builder.py`

- ✅ Combine all data and metadata
- ✅ Calculate data sizes
- ✅ Format with Pydantic models
- ✅ Handle error responses

**Input**: All previous outputs  
**Output**: Final API response

---

## 📊 Data Flow Example

### Input Request
```json
{
  "offer_id": "624730890959"
}
```

### After Data Retrieval
```json
{
  "_id": {"$oid": "68f9d701766c2f8a29a2665b"},
  "offerId": 624730890959,
  "name": "2020 New Men's Hooded Sports Set",
  "categories": [...],
  "productSkuInfos": [
    {
      "skuId": {"$numberLong": "4423361457251"},
      "skuAttributes": [...],
      "skuShippingDetail": {
        "length": 27.28,
        "width": 22.19,
        "height": 6.42,
        "weight": 0.4714
      }
    }
  ]
}
```

### After Preprocessing
```json
[{
  "id": "68f9d701766c2f8a29a2665b",
  "name": "2020 New Men's Hooded Sports Set",
  "categories": [...],
  "Product info": {
    "length": 27.28,
    "weight": 0.4714,
    "height": 6.42,
    "width": 22.19
  },
  "skus": [
    {
      "skuId": "4423361457251",
      "skuAttributes": [...],
      "length": 27.28,
      "width": 22.19,
      "height": 6.42,
      "weight": 0.4714
    }
  ]
}]
```

### After Model API
```json
[{
  "skus": [
    {
      "skuId": "4423361457251",
      "length_cm": 27.28,
      "width_cm": 22.19,
      "height_cm": 6.42,
      "weight_g": 471.4
    }
  ]
}]
```

### Final Response
```json
{
  "success": true,
  "offer_id": "624730890959",
  "estimated_weights": [...],
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
  }
}
```

## 🔧 Configuration Flow

```
.env file
   ↓
config.py (Settings class)
   ↓
main.py (get_settings())
   ↓
Individual Modules
```

## 📝 Logging Flow

```
Module operations
   ↓
Python logging
   ↓
Console Handler → Terminal output
   ↓
File Handler → logs/app.log (with rotation)
```

## 🔐 Security Layers

1. **Environment Variables**: Sensitive data in .env
2. **Input Validation**: Pydantic models validate requests
3. **Error Handling**: Graceful error messages (no sensitive data)
4. **Connection Management**: Proper connection closing
5. **Logging**: No sensitive data in logs

## 🚀 Scalability Points

1. **Data Retrieval**: Can add connection pooling
2. **Preprocessing**: Stateless, can parallelize
3. **Model API**: Can batch multiple products
4. **Response**: Can add caching layer

## 📈 Monitoring Points

- **Request count**: Track via middleware
- **Processing time**: Already tracked per request
- **Token usage**: Tracked in model_api_stats
- **Error rate**: Check logs/app.log
- **Database health**: /health endpoint

## 🔄 Update Process

```
1. Modify module file
   ↓
2. Update schemas if needed
   ↓
3. Test module independently
   ↓
4. Test via API endpoint
   ↓
5. Check logs for issues
   ↓
6. Deploy changes
```

## 📚 Key Files Reference

| File | Purpose | When to Modify |
|------|---------|----------------|
| `main.py` | API endpoints | Add/modify endpoints |
| `app/config.py` | Settings | Add configuration |
| `app/models/schemas.py` | Data models | Change response structure |
| `app/modules/data_retrieval.py` | Data source | Change database |
| `app/modules/preprocessing.py` | Data cleaning | Add preprocessing steps |
| `app/modules/model_api.py` | AI model | Change AI provider |
| `app/modules/response_builder.py` | Response format | Add metadata fields |
| `.env` | Credentials | Update secrets |
| `requirements.txt` | Dependencies | Add libraries |

## 🎓 Learning Path

1. **Understand flow**: Read this document
2. **Run API**: Use `python main.py`
3. **Test endpoints**: Use `python test_api.py`
4. **Read modules**: Start with data_retrieval.py
5. **Modify gradually**: Change one module at a time
6. **Check logs**: Monitor logs/app.log
7. **Review docs**: Read /docs endpoint

## 💡 Common Tasks

### Add new preprocessing step
→ Modify `app/modules/preprocessing.py`

### Change AI model
→ Modify `app/modules/model_api.py`

### Add response field
→ Modify `app/models/schemas.py` + `app/modules/response_builder.py`

### Change data source
→ Modify `app/modules/data_retrieval.py`

### Add new endpoint
→ Modify `main.py`

### Update configuration
→ Modify `app/config.py` + `.env`

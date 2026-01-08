# Weight Estimation API

A modular FastAPI application for estimating product weights using AI (Claude API) with comprehensive preprocessing and metadata tracking.

## 🏗️ Architecture

The application is built with a modular architecture for easy maintenance and upgrades:

```
weight estimation/
├── app/
│   ├── modules/
│   │   ├── data_retrieval.py    # MongoDB data fetching
│   │   ├── preprocessing.py     # Data cleaning & filtering
│   │   ├── model_api.py         # Claude API integration
│   │   └── response_builder.py  # Response formatting
│   ├── models/
│   │   └── schemas.py           # Pydantic models
│   ├── utils/
│   │   └── helpers.py           # Utility functions
│   └── config.py                # Configuration management
├── main.py                      # FastAPI application
├── requirements.txt             # Python dependencies
└── .env                         # Environment variables
```

## 🚀 Features

- **Modular Design**: Each component (data retrieval, preprocessing, model API) is independent
- **Comprehensive Metadata**: Returns preprocessing stats, token usage, processing time
- **Error Handling**: Robust error handling with detailed logging
- **Health Checks**: Monitor MongoDB and API connectivity
- **Debugging Friendly**: Structured logging with rotation

## 📋 Prerequisites

- Python 3.8+
- MongoDB access
- Anthropic API key (Claude)

## 🔧 Installation

1. **Clone or navigate to the project directory**

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux/Mac
   # or
   venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

   Required variables in `.env`:
   ```
   MONGODB_CONNECTION_STRING=mongodb://...
   MONGODB_DATABASE_NAME=markazmongodbprod
   MONGODB_COLLECTION_NAME=productsV2
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ```

## 🎯 Usage

### Start the API server

```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API Endpoints

#### 1. Estimate Weight
**POST** `/estimate-weight`

Request body:
```json
{
  "offer_id": "624730890959"
}
```

Response:
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

#### 2. Health Check
**GET** `/health`

Returns service health status and component connectivity.

#### 3. Root
**GET** `/`

Basic health check endpoint.

## 📦 Module Details

### 1. Data Retrieval (`app/modules/data_retrieval.py`)
- Establishes MongoDB connection
- Fetches product data by offer ID
- Handles connection errors gracefully

### 2. Preprocessing (`app/modules/preprocessing.py`)
- Filters and structures product data
- Extracts SKU attributes and dimensions
- Removes duplicate SKUs with identical physical properties
- Tracks preprocessing statistics

### 3. Model API Client (`app/modules/model_api.py`)
- Integrates with Claude API (Anthropic)
- Prepares data in required format
- Handles API errors and rate limiting
- Tracks token usage and timing

### 4. Response Builder (`app/modules/response_builder.py`)
- Constructs standardized API responses
- Includes all metadata (preprocessing stats, API stats)
- Handles error responses

## 🔍 Logging

Logs are stored in `logs/app.log` with automatic rotation:
- Max file size: 10MB
- Backup count: 5 files
- Format: timestamp, logger name, level, message

## 🛠️ Development

### Running in development mode
```bash
# Enable auto-reload
uvicorn main:app --reload
```

### Testing the API
```bash
# Using curl
curl -X POST "http://localhost:8000/estimate-weight" \
  -H "Content-Type: application/json" \
  -d '{"offer_id": "624730890959"}'

# Using Python requests
import requests
response = requests.post(
    "http://localhost:8000/estimate-weight",
    json={"offer_id": "624730890959"}
)
print(response.json())
```

## 🔄 Upgrading Modules

Each module is independent and can be upgraded separately:

1. **Data Retrieval**: Modify `app/modules/data_retrieval.py` to change data source
2. **Preprocessing**: Update `app/modules/preprocessing.py` to add new cleaning logic
3. **Model API**: Replace `app/modules/model_api.py` to use different AI model
4. **Response Format**: Adjust `app/models/schemas.py` to change response structure

## 📊 Monitoring

Check application health:
```bash
curl http://localhost:8000/health
```

Monitor logs in real-time:
```bash
tail -f logs/app.log
```

## ⚠️ Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid offer ID format)
- `404`: Offer ID not found
- `500`: Internal server error

All errors include descriptive messages in the response.

## 🔒 Security Notes

- Never commit `.env` file to version control
- Use environment variables for all sensitive data
- Consider adding authentication for production use
- Implement rate limiting for API endpoints

## 📝 License

[Add your license here]

## 👥 Contributors

[Add contributors here]

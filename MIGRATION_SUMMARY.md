# Migration Summary: Anthropic Claude → Vertex AI Gemini

## Changes Made

### ✅ Single Request Processing: Now uses **Vertex AI Gemini**
- Default model: `gemini-1.5-flash`
- Supports: `gemini-1.5-flash`, `gemini-2.0-flash`, `gemini-2.0-pro`, etc.
- Uses Application Default Credentials (ADC) for authentication

### ✅ Batch Processing: Still uses **Anthropic Claude**
- Unchanged batch API implementation
- Maintains 50% cost savings for batch operations
- Uses Anthropic API key for authentication

## Configuration Updates

### Environment Variables Required (.env file)

```env
# MongoDB
MONGODB_CONNECTION_STRING=your_connection_string
MONGODB_DATABASE_NAME=markazmongodbprod
MONGODB_COLLECTION_NAME=productsV2

# Vertex AI (for single requests)
GOOGLE_PROJECT_ID=markazqa-36bbe
GOOGLE_LOCATION=us-central1

# Anthropic (for batch processing)
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=False
```

### Authentication Setup

**For Vertex AI (required for single requests):**
```bash
# Install gcloud CLI
sudo snap install google-cloud-cli --classic

# Authenticate
gcloud auth application-default login
```

## Installation

```bash
# Install new dependencies
pip install -r requirements.txt

# This installs google-cloud-aiplatform for Vertex AI
```

## API Usage

### Single Request (Uses Gemini)
```bash
POST /estimate-weight
{
  "offer_id": "123456",
  "model_name": "gemini-1.5-flash",  # Changed from claude-sonnet-4-5
  "drop_similar_skus": true
}
```

### Batch Request (Still uses Claude)
```bash
POST /batch-estimate
{
  "offer_ids": ["123456", "789012"],
  "model_name": "claude-haiku-4-5",  # Unchanged
  "drop_similar_skus": true
}
```

## Files Modified

1. **app/config.py** - Added Vertex AI settings
2. **app/modules/model_api.py** - Dual API support (Gemini + Claude)
3. **app/models/schemas.py** - Updated default model name
4. **main.py** - Updated single request endpoint initialization
5. **requirements.txt** - Added google-cloud-aiplatform
6. **.env.example** - Added Vertex AI configuration

## Testing

Test the changes:
```bash
# Start the server
python main.py

# Or with uvicorn
uvicorn main:app --reload

# Test single request (now uses Gemini)
python test_api.py
```

## Important Notes

⚠️ **Make sure to:**
1. Run `gcloud auth application-default login` before starting the server
2. Update your `.env` file with `GOOGLE_PROJECT_ID` and `GOOGLE_LOCATION`
3. Keep `ANTHROPIC_API_KEY` for batch processing

✅ **Benefits:**
- Single requests now use Vertex AI Gemini (potentially lower cost/faster)
- Batch processing still uses Anthropic Claude (50% discount maintained)
- Flexible architecture allows easy switching between providers

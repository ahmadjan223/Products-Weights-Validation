# Module Upgrade Guide

This guide explains how to modify or upgrade each module independently.

## 📁 Project Structure

```
weight estimation/
├── app/
│   ├── modules/           # Core business logic modules
│   │   ├── data_retrieval.py
│   │   ├── preprocessing.py
│   │   ├── model_api.py
│   │   └── response_builder.py
│   ├── models/
│   │   └── schemas.py     # Pydantic models for validation
│   ├── utils/
│   │   └── helpers.py     # Utility functions
│   └── config.py          # Configuration management
├── main.py                # FastAPI application
└── logs/                  # Application logs
```

## 🔧 Modifying Individual Modules

### 1. Data Retrieval Module (`app/modules/data_retrieval.py`)

**Purpose**: Fetch data from MongoDB by offer ID

**To modify**:
```python
class DataRetriever:
    def fetch_by_offer_id(self, offer_id: str):
        # Current: Fetches from MongoDB
        # To change data source:
        # 1. Replace MongoDB client with your data source
        # 2. Keep the same return type (Dict)
        # 3. Maintain error handling
        pass
```

**Example - Switch to PostgreSQL**:
```python
import psycopg2

class DataRetriever:
    def __init__(self, connection_string: str, ...):
        self.conn = psycopg2.connect(connection_string)
    
    def fetch_by_offer_id(self, offer_id: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM products WHERE offer_id = %s",
            (offer_id,)
        )
        return cursor.fetchone()
```

**Example - Switch to REST API**:
```python
import requests

class DataRetriever:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
    
    def fetch_by_offer_id(self, offer_id: str):
        response = requests.get(
            f"{self.api_url}/products/{offer_id}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()
```

---

### 2. Preprocessing Module (`app/modules/preprocessing.py`)

**Purpose**: Clean, filter, and transform data

**To modify**:
```python
class DataPreprocessor:
    @staticmethod
    def preprocess_pipeline(raw_product: Dict):
        # Current pipeline:
        # 1. filter_product_data() - Extract relevant fields
        # 2. remove_duplicate_skus() - Remove duplicates
        
        # To add new preprocessing steps:
        # 1. Create new static method
        # 2. Add to pipeline
        # 3. Update stats dictionary
        pass
```

**Example - Add validation step**:
```python
@staticmethod
def validate_dimensions(data: List[Dict]) -> Tuple[List[Dict], Dict]:
    """Validate that dimensions are within acceptable ranges"""
    validated_data = []
    stats = {"invalid_skus_removed": 0}
    
    for product in data:
        valid_skus = []
        for sku in product.get('skus', []):
            # Check if dimensions are reasonable
            if (sku.get('length', 0) > 0 and 
                sku.get('width', 0) > 0 and 
                sku.get('height', 0) > 0):
                valid_skus.append(sku)
            else:
                stats["invalid_skus_removed"] += 1
        
        product['skus'] = valid_skus
        validated_data.append(product)
    
    return validated_data, stats

@classmethod
def preprocess_pipeline(cls, raw_product: Dict):
    # Step 1: Filter
    filtered = cls.filter_product_data(raw_product)
    
    # Step 2: Remove duplicates
    cleaned_data, dup_stats = cls.remove_duplicate_skus([filtered])
    
    # Step 3: Validate (NEW)
    validated_data, val_stats = cls.validate_dimensions(cleaned_data)
    
    # Combine stats
    stats = {**dup_stats, **val_stats}
    
    return validated_data, stats
```

---

### 3. Model API Client Module (`app/modules/model_api.py`)

**Purpose**: Call AI model for weight estimation

**To modify**:
```python
class ModelAPIClient:
    def estimate_weights(self, products: List[Dict]):
        # Current: Uses Claude API
        # To switch models:
        # 1. Replace API client
        # 2. Adjust prompt format
        # 3. Update response parsing
        # 4. Keep stats structure consistent
        pass
```

**Example - Switch to OpenAI**:
```python
from openai import OpenAI

class ModelAPIClient:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-4"
    
    def estimate_weights(self, products: List[Dict]):
        prepared_data = self.prepare_product_data(products)
        
        start_time = time.time()
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(prepared_data)}
            ]
        )
        
        processing_time = time.time() - start_time
        
        result = json.loads(response.choices[0].message.content)
        
        stats = {
            "api_calls_count": 1,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "processing_time_seconds": round(processing_time, 2),
            "model_name": self.model_name
        }
        
        return result, stats
```

**Example - Use local model**:
```python
import torch
from transformers import AutoModel, AutoTokenizer

class ModelAPIClient:
    def __init__(self, model_path: str):
        self.model = AutoModel.from_pretrained(model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model_name = "local-model"
    
    def estimate_weights(self, products: List[Dict]):
        # Your local inference logic here
        pass
```

---

### 4. Response Builder Module (`app/modules/response_builder.py`)

**Purpose**: Format API responses with metadata

**To modify**:
```python
class ResponseBuilder:
    @staticmethod
    def build_success_response(...):
        # To add new fields to response:
        # 1. Update schemas.py first
        # 2. Add field calculation here
        # 3. Update documentation
        pass
```

**Example - Add confidence scores**:

First, update [schemas.py](app/models/schemas.py):
```python
class ModelAPIStats(BaseModel):
    # ... existing fields ...
    average_confidence: Optional[float] = None  # NEW
```

Then update response_builder.py:
```python
@staticmethod
def build_success_response(..., confidence_scores: List[float] = None):
    # Calculate average confidence
    avg_confidence = None
    if confidence_scores:
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
    
    model_stats = ModelAPIStats(
        # ... existing fields ...
        average_confidence=avg_confidence  # NEW
    )
    # ... rest of the function
```

---

## 🔄 Adding New Endpoints

To add a new endpoint to [main.py](main.py):

```python
@app.post("/batch-estimate")
async def batch_estimate_weights(offer_ids: List[str]):
    """Process multiple offer IDs at once"""
    results = []
    
    for offer_id in offer_ids:
        try:
            # Use existing modules
            raw_data = data_retriever.fetch_by_offer_id(offer_id)
            preprocessed, stats = DataPreprocessor.preprocess_pipeline(raw_data)
            estimated, api_stats = model_client.estimate_weights(preprocessed)
            
            result = ResponseBuilder.build_success_response(
                offer_id, raw_data, preprocessed, 
                estimated, stats, api_stats
            )
            results.append(result)
        except Exception as e:
            results.append({"offer_id": offer_id, "error": str(e)})
    
    return {"results": results}
```

---

## 🎨 Modifying Response Schema

Update [schemas.py](app/models/schemas.py) to change response structure:

```python
# Add new field
class WeightEstimationResponse(BaseModel):
    # ... existing fields ...
    processing_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the processing completed"
    )
    data_source: str = Field(
        default="mongodb",
        description="Source of the data"
    )
```

---

## 📝 Configuration Changes

Modify [config.py](app/config.py) to add new settings:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Add new configuration
    max_skus_per_product: int = 100
    enable_caching: bool = False
    cache_ttl_seconds: int = 3600
```

---

## 🧪 Testing Your Changes

After modifying a module:

1. **Unit test the module**:
```python
# Test data_retrieval
retriever = DataRetriever(connection_string, db_name, collection_name)
result = retriever.fetch_by_offer_id("624730890959")
assert result is not None
```

2. **Test integration**:
```bash
python test_api.py
```

3. **Check logs**:
```bash
tail -f logs/app.log
```

---

## 🐛 Debugging Tips

### Enable detailed logging
```python
# In app/utils/helpers.py
setup_logging("logs/app.log", level=logging.DEBUG)
```

### Add debug endpoints
```python
@app.get("/debug/config")
async def debug_config():
    """View current configuration"""
    settings = get_settings()
    return {
        "mongodb_database": settings.mongodb_database_name,
        "api_port": settings.api_port,
        # Don't expose sensitive data like API keys!
    }
```

### Module isolation
Test each module independently in a Python REPL:
```python
from app.modules.data_retrieval import DataRetriever
retriever = DataRetriever(...)
data = retriever.fetch_by_offer_id("624730890959")
print(data)
```

---

## 📚 Best Practices

1. **Keep interfaces consistent**: When modifying a module, maintain its input/output structure
2. **Update tests**: Add tests for new functionality
3. **Document changes**: Update README.md and docstrings
4. **Version control**: Commit each module change separately
5. **Backwards compatibility**: Deprecate old features gradually
6. **Error handling**: Maintain consistent error handling patterns
7. **Logging**: Add appropriate log statements for debugging

---

## 🚀 Deployment Considerations

When deploying with modified modules:

1. **Environment variables**: Update .env with production values
2. **Dependencies**: Run `pip freeze > requirements.txt` after adding libraries
3. **Database connections**: Use connection pooling for production
4. **API keys**: Rotate and secure all API keys
5. **Monitoring**: Add health checks for new modules
6. **Rate limiting**: Implement rate limiting for API endpoints
7. **Caching**: Consider caching frequently accessed data

---

## 📞 Need Help?

- Check [README.md](README.md) for general information
- Review [API_EXAMPLES.md](API_EXAMPLES.md) for usage examples
- Check logs in `logs/app.log` for errors
- Test endpoints at http://localhost:8000/docs

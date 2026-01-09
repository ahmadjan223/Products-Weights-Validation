# Copilot Instructions - Weight Estimation API

## Architecture Overview

This is a **modular FastAPI application** that estimates product dimensions and weights using Claude AI. Data flows through 4 independent modules in sequence:

```
MongoDB → DataRetriever → DataPreprocessor → ModelAPIClient → ResponseBuilder → JSON Response
```

Each module is self-contained with clear inputs/outputs, allowing independent modification without affecting others (see [MODULE_UPGRADE_GUIDE.md](../MODULE_UPGRADE_GUIDE.md)).

### Key Architectural Principle: Module Independence
- Each module in `app/modules/` has a single responsibility
- Modules communicate only through return values, never shared state
- To swap data sources or AI models, modify only the relevant module
- Example: Switch from MongoDB to PostgreSQL by editing only `data_retrieval.py`

## Critical Development Workflows

### Starting the Server
```bash
# Standard approach (auto-reload in debug mode)
python main.py

# Production with multiple workers
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Testing
```bash
# Quick test with sample offer ID
python test_api.py

# Interactive API docs (FastAPI auto-generated)
# Start server, then visit: http://localhost:8000/docs
```

### Environment Configuration
Required `.env` variables (loaded via pydantic-settings):
```env
MONGODB_CONNECTION_STRING=mongodb://...
MONGODB_DATABASE_NAME=markazmongodbprod
MONGODB_COLLECTION_NAME=productsV2
ANTHROPIC_API_KEY=sk-ant-api03-...
```

Configuration lives in `app/config.py` using `@lru_cache()` for singleton pattern.

## MongoDB Data Structure Specifics

Products in MongoDB have **nested SKU arrays** with inconsistent field presence:
- Top-level `productSkuInfos[]` contains variants
- Each SKU has `skuShippingDetail` with dimensions (often null)
- IDs stored as `{$oid: "..."}` or `{$numberLong: "..."}` objects, not primitives
- Query by `offerId` (integer), not `_id`

**Critical preprocessing pattern** (see `preprocessing.py:filter_product_data`):
1. Extract nested MongoDB objects: `raw_id.get('$oid')` for IDs
2. Handle null SKU lists: always check `isinstance(sku_infos, list)`
3. Remove duplicate SKUs with identical weight (non-null, non-zero) before sending to AI

## AI Model Integration Pattern

The Claude API system prompt (see `model_api.py:SYSTEM_PROMPT`) is **engineered for logistics data cleaning**, not general Q&A:
- Input: JSON list of products with messy/missing dimensions
- Output: Standardized dimensions in cm/g with imputation statistics
- Prompt instructs Claude to use product categories + SKU attributes to detect unit errors (e.g., "3kg for a phone case")

**When modifying the AI logic:**
- Don't alter the strict JSON output format - ResponseBuilder expects specific field names
- Preserve the 4-step reasoning process in the system prompt
- Model name configurable per-request via `WeightEstimationRequest.model_name` (default: `claude-sonnet-4-5`)

## Pydantic Validation Patterns

All requests/responses validated via `app/models/schemas.py`:
- Field aliases handle API naming inconsistencies: `sku_id` ↔ `skuId`
- Custom validators convert types: SKU IDs auto-stringified from integers
- Config setting: `protected_namespaces = ()` to allow `model_name` field

**When adding new fields:**
```python
# Use Field aliases for API compatibility
new_field: str = Field(..., alias="newField")

# Add validator for type coercion if needed
@field_validator('new_field', mode='before')
@classmethod
def coerce_type(cls, v):
    return str(v) if v else None
```

## Logging and Debugging

Structured logging configured in `app/utils/helpers.py:setup_logging()`:
- Console + rotating file logs (10MB max, 5 backups)
- Logs stored in `logs/app.log`
- Emoji markers in logs: ✅ success, ❌ errors, 🔍 operations

**Log level for modules:** Each module has `logger = logging.getLogger(__name__)` for namespaced logs.

## Common Pitfalls

1. **Don't use `python -c` for testing Python snippets** - use the workspace's configured Python environment via the Python tools
2. **MongoDB ObjectId handling** - Always extract via `.get('$oid')`, never access directly
3. **Lifespan context manager** - Global instances (`data_retriever`) initialized in `main.py:lifespan()`, not at module level
4. **Null SKU data** - Preprocessing must handle missing/null values at every level before AI sees data

## Key Files to Reference

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Visual data flow diagrams
- [MODULE_UPGRADE_GUIDE.md](../MODULE_UPGRADE_GUIDE.md) - Examples for swapping databases, AI models
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Production configuration with Gunicorn
- `batch_api_test.ipynb` - Notebook for testing multiple offer IDs in parallel

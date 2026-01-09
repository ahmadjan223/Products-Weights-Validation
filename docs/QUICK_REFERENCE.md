# ⚡ Quick Reference Card

## 🚀 Start/Stop Server

```bash
# Start server
python main.py

# Stop server
CTRL + C

# Start with auto-reload (development)
uvicorn main:app --reload
```

## 🔌 API Endpoints

### Estimate Weight
```bash
POST http://localhost:8000/estimate-weight
Body: {"offer_id": "624730890959"}
```

### Health Check
```bash
GET http://localhost:8000/health
```

### Root / Status
```bash
GET http://localhost:8000/
```

### Documentation
```bash
GET http://localhost:8000/docs      # Swagger UI
GET http://localhost:8000/redoc     # ReDoc
```

## 🧪 Testing

```bash
# Run test script
python test_api.py

# Quick curl test
curl -X POST "http://localhost:8000/estimate-weight" \
  -H "Content-Type: application/json" \
  -d '{"offer_id": "624730890959"}'
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI endpoints |
| `app/modules/data_retrieval.py` | MongoDB |
| `app/modules/preprocessing.py` | Data cleaning |
| `app/modules/model_api.py` | AI model |
| `app/modules/response_builder.py` | Response format |
| `app/models/schemas.py` | Data models |
| `app/config.py` | Settings |
| `.env` | Credentials |
| `logs/app.log` | Application logs |

## 🔧 Quick Edits

### Change MongoDB Connection
Edit `.env`:
```
MONGODB_CONNECTION_STRING=mongodb://...
```

### Change AI Model
Edit `app/modules/model_api.py`:
```python
self.model_name = "your-model"
```

### Add Preprocessing Step
Edit `app/modules/preprocessing.py`:
```python
@staticmethod
def your_new_step(data):
    # Your logic here
    return processed_data, stats
```

### Add Response Field
1. Edit `app/models/schemas.py`
2. Edit `app/modules/response_builder.py`

## 📊 Monitoring

### Check Logs
```bash
# View logs
tail -f logs/app.log

# View last 50 lines
tail -n 50 logs/app.log

# Search logs
grep "ERROR" logs/app.log
```

### Check Health
```bash
curl http://localhost:8000/health
```

## 🐛 Debugging

### Enable Debug Mode
Edit `.env`:
```
API_DEBUG=True
```

### Check Module Independently
```python
from app.modules.data_retrieval import DataRetriever

retriever = DataRetriever(
    connection_string="...",
    database_name="markazmongodbprod",
    collection_name="productsV2"
)
data = retriever.fetch_by_offer_id("624730890959")
print(data)
```

### Common Issues

**Port already in use:**
```bash
# Find process
lsof -i :8000
# Kill process
kill -9 <PID>
```

**MongoDB connection failed:**
- Check `.env` connection string
- Verify network access to MongoDB

**API key error:**
- Check `.env` ANTHROPIC_API_KEY
- Verify key is valid

## 📦 Dependencies

### Install
```bash
pip install -r requirements.txt
```

### Update
```bash
pip install --upgrade package-name
pip freeze > requirements.txt
```

## 🔒 Security Checklist

- ✅ Credentials in `.env`, not code
- ✅ `.env` in `.gitignore`
- ✅ No API keys in logs
- ✅ Input validation with Pydantic
- ⚠️ Add authentication for production
- ⚠️ Add rate limiting for production

## 📚 Documentation Links

- [README.md](README.md) - Full setup guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [MODULE_UPGRADE_GUIDE.md](MODULE_UPGRADE_GUIDE.md) - Customization
- [API_EXAMPLES.md](API_EXAMPLES.md) - Code examples
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Complete overview

## 🎯 Common Tasks

### Add New Endpoint
In `main.py`:
```python
@app.post("/your-endpoint")
async def your_function(request: YourModel):
    # Your logic
    return response
```

### Change Data Source
Edit `app/modules/data_retrieval.py`

### Change AI Provider
Edit `app/modules/model_api.py`

### Add Preprocessing Logic
Edit `app/modules/preprocessing.py`

### Modify Response Structure
Edit `app/models/schemas.py` + `app/modules/response_builder.py`

## 💡 Tips

1. **Always check logs** when debugging
2. **Test modules independently** before integration
3. **Use /docs endpoint** for API exploration
4. **Keep .env backed up** but never commit it
5. **Read error messages** - they're detailed!

## 🔄 Update Workflow

```
1. Modify code
2. Save file
3. Restart server (or use --reload)
4. Test with test_api.py
5. Check logs for errors
6. Verify in /docs
```

## 📞 Quick Help

**Can't start server?**
→ Check logs/app.log

**Wrong response?**
→ Check /docs for expected format

**Database error?**
→ Verify .env credentials

**Model API error?**
→ Check ANTHROPIC_API_KEY

**Need examples?**
→ See API_EXAMPLES.md

---

**Save this file for quick reference! 📌**

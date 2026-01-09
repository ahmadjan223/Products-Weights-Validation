# Deployment Guide

## Production Deployment Checklist

### 1. Environment Setup
- Ensure `.env` file is present with production credentials
- Verify MongoDB connection string is valid
- Verify Anthropic API key is active
- Set `API_DEBUG=False` for production

### 2. Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the Application

#### Option A: Direct Python
```bash
python main.py
```

#### Option B: Using Uvicorn directly
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Option C: Production with Gunicorn
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 4. Health Checks
- Root: `GET http://localhost:8000/`
- Health: `GET http://localhost:8000/health`

### 5. API Endpoints

#### Weight Estimation
```bash
curl -X POST http://localhost:8000/estimate-weight \
  -H "Content-Type: application/json" \
  -d '{"offer_id": "your_offer_id"}'
```

#### With Optional Parameters
```bash
curl -X POST http://localhost:8000/estimate-weight \
  -H "Content-Type: application/json" \
  -d '{
    "offer_id": "your_offer_id",
    "model_name": "claude-sonnet-4-5",
    "drop_similar_skus": true
  }'
```

### 6. Monitoring

#### Logs
- Application logs: `logs/app.log`
- Logs rotate automatically (10MB, 5 backups)

#### Log Levels
- Production: INFO (default)
- Debug: Set logging level to DEBUG in `app/utils/helpers.py`

### 7. Security Considerations

✅ **Already Configured:**
- Environment variables for sensitive data
- `.env` file in `.gitignore`
- No hardcoded credentials

⚠️ **Recommended for Production:**
- Add HTTPS/SSL certificate
- Add rate limiting (e.g., using slowapi)
- Add authentication (API keys, JWT, etc.)
- Use reverse proxy (Nginx, Apache)
- Configure CORS if needed

### 8. Docker Deployment (Optional)

Create `Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t weight-estimation-api .
docker run -d -p 8000:8000 --env-file .env weight-estimation-api
```

### 9. Performance Optimization

Current Configuration:
- Async/await for I/O operations
- MongoDB connection pooling
- Single model client per request
- Structured logging

Scaling Options:
- Increase worker count for Gunicorn
- Use Redis for caching frequent requests
- Implement request queuing for high loads
- Add CDN for static documentation

### 10. Troubleshooting

#### MongoDB Connection Issues
```python
# Check connection in health endpoint
curl http://localhost:8000/health
```

#### Model API Issues
- Verify API key in `.env`
- Check token limits (8000 max)
- Review logs for detailed errors

#### High Memory Usage
- Reduce worker count
- Implement request rate limiting
- Clear logs periodically

### 11. Production Environment Variables

```bash
# .env file for production
MONGODB_CONNECTION_STRING=mongodb://user:pass@host:port/db?authSource=db
MONGODB_DATABASE_NAME=markazmongodbprod
MONGODB_COLLECTION_NAME=products
ANTHROPIC_API_KEY=your-production-api-key
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=False
```

### 12. Backup and Recovery

- MongoDB: Regular backups of product collection
- Logs: Archive old logs periodically
- Configuration: Version control for `.env.example`

## Quick Production Start

```bash
# 1. Clone and setup
cd /path/to/project
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with production credentials

# 3. Start application
python main.py
```

## API Documentation

Once running, access interactive documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

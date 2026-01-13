# Deployment Guide

## Production Deployment Checklist

### 1. Environment Setup
- Ensure `.env` file is present with production credentials
- Verify MongoDB connection string is valid
- Verify Gemini API key is active
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
    "model_name": "gemini-2.5-flash",
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

The project includes a `Dockerfile` configured for production:

```bash
# Build locally
docker build -t weight-estimation-api .

# Run locally
docker run -d -p 8080:8080 --env-file .env weight-estimation-api
```

### 9. Google Cloud Run Deployment

#### Prerequisites
- Google Cloud Project with billing enabled
- `gcloud` CLI installed and authenticated
- `.env` file with production credentials

#### Quick Deploy
```bash
# Make deployment script executable
chmod +x deploy-cloud-run.sh

# Set your GCP project ID
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"  # Optional, defaults to us-central1
export SERVICE_NAME="weight-estimation-api"  # Optional

# Deploy to Cloud Run
./deploy-cloud-run.sh
```

#### Manual Deployment Steps

1. **Enable Required APIs:**
```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com
```

2. **Build Docker Image:**
```bash
PROJECT_ID="your-project-id"
IMAGE_NAME="gcr.io/${PROJECT_ID}/weight-estimation-api"
gcloud builds submit --tag $IMAGE_NAME --project=$PROJECT_ID
```

3. **Deploy to Cloud Run:**
```bash
gcloud run deploy weight-estimation-api \
  --image $IMAGE_NAME \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars "MONGODB_CONNECTION_STRING=your_connection_string" \
  --set-env-vars "MONGODB_DATABASE_NAME=your_database" \
  --set-env-vars "MONGODB_COLLECTION_NAME=your_collection" \
  --set-env-vars "GEMINI_API_KEY=your_api_key"
```

4. **Configure Custom Domain (Optional):**
```bash
gcloud run domain-mappings create --service weight-estimation-api --domain your-domain.com
```

#### Cloud Run Configuration Options

- **Memory**: 2Gi (adjust based on your needs)
- **CPU**: 2 vCPUs (increase for higher concurrency)
- **Timeout**: 300 seconds (max for weight estimation requests)
- **Max Instances**: 10 (auto-scaling limit)
- **Min Instances**: 0 (scales to zero when idle to save costs)

#### Cost Optimization
- Service scales to zero when idle (no charges for idle time)
- Set `--min-instances=1` for always-warm instances (faster response but costs more)
- Monitor usage in GCP Console > Cloud Run

#### Security Best Practices
```bash
# Option 1: Require authentication
gcloud run deploy weight-estimation-api --no-allow-unauthenticated

# Option 2: Use Secret Manager for sensitive data
gcloud secrets create gemini-api-key --data-file=- <<< "your-api-key"
gcloud run deploy weight-estimation-api \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest"
```

### 10. Performance Optimization

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

### 11. Troubleshooting

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

### 12. Production Environment Variables

```bash
# .env file for production
MONGODB_CONNECTION_STRING=mongodb://user:pass@host:port/db?authSource=db
MONGODB_DATABASE_NAME=markazmongodbprod
MONGODB_COLLECTION_NAME=products
GEMINI_API_KEY=your-production-api-key
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=False
```

### 13. Backup and Recovery

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

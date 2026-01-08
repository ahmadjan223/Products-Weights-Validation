"""
Main FastAPI Application
Provides weight estimation endpoint with modular architecture
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import get_settings
from app.models.schemas import (
    WeightEstimationRequest,
    WeightEstimationResponse,
    ErrorResponse
)
from app.modules.data_retrieval import DataRetriever
from app.modules.preprocessing import DataPreprocessor
from app.modules.model_api import ModelAPIClient
from app.modules.response_builder import ResponseBuilder
from app.utils.helpers import setup_logging

# Setup logging
setup_logging("logs/app.log")
logger = logging.getLogger(__name__)

# Global instances
data_retriever = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI application
    Initializes and cleans up resources
    """
    global data_retriever, model_client
    
    # Startup
    logger.info("🚀 Starting Weight Estimation API...")
    settings = get_settings()
    
    try:
        # Initialize MongoDB connection
        data_retriever = DataRetriever(
            connection_string=settings.mongodb_connection_string,
            database_name=settings.mongodb_database_name,
            collection_name=settings.mongodb_collection_name
        )
        logger.info("✅ MongoDB connection initialized")
        
        # Model API client will be initialized per request with user's model choice
        logger.info("✅ Configuration loaded")
        
        logger.info("🎉 Application startup complete!")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down application...")
    if data_retriever:
        data_retriever.close()
        logger.info("✅ MongoDB connection closed")
    logger.info("👋 Application shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="Weight Estimation API",
    description="API for estimating product weights using AI",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Weight Estimation API",
        "version": "1.0.0"
    }


@app.post(
    "/estimate-weight",
    response_model=WeightEstimationResponse,
    responses={
        200: {"description": "Successful weight estimation"},
        404: {"model": ErrorResponse, "description": "Offer ID not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def estimate_weight(request: WeightEstimationRequest):
    """
    Estimate product weights for a given offer ID
    
    Process:
    1. Retrieve product data from MongoDB using offer ID
    2. Preprocess data (filter, clean, remove duplicates)
    3. Call AI model for weight estimation
    4. Return results with comprehensive metadata
    
    Args:
        request: WeightEstimationRequest containing offer_id
        
    Returns:
        WeightEstimationResponse with estimated weights and metadata
    """
    offer_id = request.offer_id
    model_name = request.model_name
    drop_similar_skus = request.drop_similar_skus
    
    logger.info(f"📨 Received request for offer ID: {offer_id}")
    logger.info(f"⚙️  Settings - Model: {model_name}, Drop duplicates: {drop_similar_skus}")
    
    try:
        # Step 1: Retrieve data from MongoDB
        logger.info(f"Step 1/4: Retrieving data for offer ID: {offer_id}")
        raw_data = data_retriever.fetch_by_offer_id(offer_id)
        
        if not raw_data:
            error_msg = f"No product found with offer ID: {offer_id}"
            logger.warning(error_msg)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        
        logger.info("✅ Data retrieved successfully")
        
        # Step 2: Preprocess data
        logger.info("Step 2/4: Preprocessing data...")
        preprocessed_data, preprocessing_stats = DataPreprocessor.preprocess_pipeline(
            raw_data, 
            drop_duplicates=drop_similar_skus
        )
        logger.info(f"✅ Preprocessing complete - {preprocessing_stats['skus_removed']} SKUs removed")
        
        # Step 3: Initialize model client with user's choice and call API
        logger.info(f"Step 3/4: Calling AI model ({model_name}) for weight estimation...")
        settings = get_settings()
        model_client = ModelAPIClient(
            api_key=settings.anthropic_api_key,
            model_name=model_name
        )
        estimated_data, api_stats = model_client.estimate_weights(preprocessed_data)
        logger.info(f"✅ Model estimation complete - Used {api_stats['total_tokens']} tokens")
        
        # Step 4: Build response with metadata
        logger.info("Step 4/4: Building response...")
        response = ResponseBuilder.build_success_response(
            offer_id=offer_id,
            raw_data=raw_data,
            preprocessed_data=preprocessed_data,
            estimated_data=estimated_data,
            preprocessing_stats=preprocessing_stats,
            api_stats=api_stats
        )
        
        logger.info(f"✅ Request completed successfully for offer ID: {offer_id}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except ValueError as e:
        # Handle validation errors
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
        
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Internal server error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.get("/health")
async def health_check():
    """
    Detailed health check endpoint
    Checks connectivity to external services
    """
    health_status = {
        "status": "healthy",
        "components": {}
    }
    
    # Check MongoDB
    try:
        if data_retriever and data_retriever.client:
            data_retriever.client.admin.command('ping')
            health_status["components"]["mongodb"] = "connected"
        else:
            health_status["components"]["mongodb"] = "not initialized"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["mongodb"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check Model API configuration
    settings = get_settings()
    if settings.anthropic_api_key:
        health_status["components"]["model_api"] = "configured"
    else:
        health_status["components"]["model_api"] = "not configured"
        health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug
    )

"""
Main FastAPI Application
Provides weight estimation endpoint with modular architecture
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
import asyncio
from typing import Dict, Any

from app.config import get_settings
from app.models.schemas import (
    WeightEstimationRequest,
    WeightEstimationResponse,
    BatchWeightEstimationRequest,
    BatchSubmissionResponse,
    BatchStatusResponse,
    BatchResultsResponse,
    ErrorResponse
)
from app.modules.data_retrieval import DataRetriever
from app.modules.preprocessing import DataPreprocessor
from app.modules.model_api import ModelAPIClient
from app.modules.response_builder import ResponseBuilder
from app.utils.helpers import (
    setup_logging,
    save_to_json,
    save_model_response_as_csv,
    save_text,
    remove_files_by_glob,
)

# Setup logging
setup_logging("logs/app.log")
logger = logging.getLogger(__name__)

# Global instances
data_retriever = None
active_batch_id: str | None = None
batch_lock = asyncio.Lock()
batch_preprocessing_stats: Dict[str, Dict[str, Any]] = {}  # Store preprocessing stats by batch_id
batch_request_mappings: Dict[str, Dict[int, str]] = {}  # Store request index -> offer_id mappings by batch_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI application
    Initializes and cleans up resources
    """
    global data_retriever, model_client
    
    # Startup
    logger.info("Starting Weight Estimation API...")
    settings = get_settings()
    
    try:
        # Initialize MongoDB connection
        data_retriever = DataRetriever(
            connection_string=settings.mongodb_connection_string,
            database_name=settings.mongodb_database_name,
            collection_name=settings.mongodb_collection_name
        )
        logger.info("MongoDB connection initialized")
        
        # Model API client will be initialized per request with user's model choice
        logger.info("Configuration loaded")
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    if data_retriever:
        data_retriever.close()
        logger.info("MongoDB connection closed")
    logger.info("Application shutdown complete")


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
    
    logger.info(f"Received request for offer ID: {offer_id} | Model: {model_name} | Drop duplicates: {drop_similar_skus}")
    
    try:
        # Step 1: Retrieve data from MongoDB
        raw_data = data_retriever.fetch_by_offer_id(offer_id)
        
        if not raw_data:
            error_msg = f"No product found with offer ID: {offer_id}"
            logger.warning(error_msg)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        
        logger.info("Data retrieved successfully")
        
        # Persist raw Mongo payload
        # save_to_json(raw_data, f"artifacts/raw.json")

        # Step 2: Preprocess data (filter + optional duplicate removal)
        filtered_data = DataPreprocessor.filter_product_data(raw_data)
        if not filtered_data:
            raise ValueError("Failed to filter product data")
        # save_to_json(filtered_data, f"artifacts/filtered.json")

        preprocessed_data, preprocessing_stats = DataPreprocessor.remove_duplicate_skus(
            [filtered_data], drop_duplicates=drop_similar_skus
        )
        logger.info(f"Preprocessing complete - {preprocessing_stats['skus_removed']} SKUs removed")
        # save_to_json(preprocessed_data, f"artifacts/deduped.json")
        
        # Step 3: Initialize model client with Gemini API for single requests
        settings = get_settings()
        model_client = ModelAPIClient(
            gemini_api_key=settings.gemini_api_key,
            model_name=model_name
        )
        estimated_data, api_stats, raw_model_text = model_client.estimate_weights(preprocessed_data)
        logger.info(f"Model estimation complete - {api_stats['total_tokens']} tokens used")
        
        # Save model response in JSON, CSV, and raw text formats
        # save_to_json(estimated_data, f"artifacts/{offer_id}_model_response.json")
        # save_model_response_as_csv(estimated_data, f"artifacts/{offer_id}_model_response.csv")
        # save_text(raw_model_text, f"artifacts/{offer_id}_model_response_raw.txt")
        
        # Step 4: Build response with metadata
        response = ResponseBuilder.build_success_response(
            offer_id=offer_id,
            raw_data=raw_data,
            preprocessed_data=preprocessed_data,
            estimated_data=estimated_data,
            preprocessing_stats=preprocessing_stats,
            api_stats=api_stats
        )
        
        # save_to_json(response.model_dump(by_alias=True), f"artifacts/response.json")

        logger.info(f"Request completed successfully for offer ID: {offer_id}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except ValueError as e:
        # Handle validation errors
        error_msg = str(e)
        
        # Check if it's a Pydantic validation error about null values
        if "Input should be a valid number" in error_msg and "input_value=None" in error_msg:
            user_friendly_msg = (
                "Model returned null values for dimension fields. "
                "This may indicate the model couldn't estimate dimensions from the available data. "
                "Try: 1) Using a different model (e.g., claude-opus-4), "
                "2) Ensuring the product has valid data in MongoDB, or "
                "3) Retrying the request."
            )
            logger.error(f"Model validation error: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=user_friendly_msg
            )
        
        logger.error(f"Validation error: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {error_msg}"
        )
        
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Internal server error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.post(
    "/batch-submit",
    response_model=BatchSubmissionResponse,
    responses={
        200: {"description": "Batch job submitted successfully"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def batch_submit(request: BatchWeightEstimationRequest):
    """
    Submit a batch job for async processing with 50% cost savings
    
    Process:
    1. Fetch and preprocess all offer IDs
    2. Create Claude Batch API job
    3. Return batch_id for status tracking
    
    Note: Results are not immediate - use /batch-status and /batch-results endpoints
    
    Args:
        request: BatchWeightEstimationRequest with offer_ids
        
    Returns:
        BatchSubmissionResponse with batch_id
    """
    offer_ids = request.offer_ids
    model_name = request.model_name
    drop_similar_skus = request.drop_similar_skus
    
    logger.info(f"Submitting batch job for {len(offer_ids)} offer IDs | Model: {model_name}")
    
    global active_batch_id
    try:
        # Enforce single in-flight batch
        async with batch_lock:
            if active_batch_id:
                settings = get_settings()
                model_client_check = ModelAPIClient(
                    gemini_api_key=settings.gemini_api_key,
                    model_name=model_name
                )
                status_info = model_client_check.get_batch_status(active_batch_id)
                if status_info.get("state") not in {"JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"}:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Another batch is running (batch_id={active_batch_id}, status={status_info.get('state')}). Wait until it ends."
                    )
                # clear stale marker
                active_batch_id = None

            # keep only latest results by removing old batch result artifacts
            remove_files_by_glob(["artifacts/batch_*_results.json"])

        # Step 1: Fetch all products in bulk
        raw_products = data_retriever.fetch_by_offer_id(offer_ids)
        
        # Step 2: Filter all products in bulk  
        filtered_products = DataPreprocessor.filter_product_data(raw_products)
        
        # Step 3: Remove duplicates in bulk
        preprocessed_products, preprocessing_stats = DataPreprocessor.remove_duplicate_skus(
            filtered_products, drop_duplicates=drop_similar_skus
        )
        
        # Step 4: Build batch requests only for successful products
        batch_requests = []
        failed_offers = []
        
        for offer_id in offer_ids:
            if preprocessed_products.get(offer_id) is None:
                logger.warning(f"Failed to process offer ID: {offer_id}")
                failed_offers.append(offer_id)
                continue
            
            # Add to batch requests
            batch_requests.append({
                "custom_id": offer_id,
                "products": preprocessed_products[offer_id]
            })
        
        if not batch_requests:
            raise ValueError("No valid offers to process")
        
        # Step 2: Create batch job with Gemini
        settings = get_settings()
        model_client = ModelAPIClient(
            gemini_api_key=settings.gemini_api_key,
            model_name=model_name
        )
        
        batch_id, request_id_mapping = model_client.create_batch_job(batch_requests)
        
        # Store preprocessing stats and request mapping for this batch
        global batch_preprocessing_stats, batch_request_mappings
        batch_preprocessing_stats[batch_id] = preprocessing_stats
        batch_request_mappings[batch_id] = request_id_mapping
        
        logger.info(f"✅ Batch job created: {batch_id} ({len(batch_requests)} requests)")

        async with batch_lock:
            active_batch_id = batch_id
        
        return BatchSubmissionResponse(
            success=True,
            batch_id=batch_id,
            total_requests=len(batch_requests),
            message=f"Batch job submitted successfully. {len(failed_offers)} offers failed preprocessing.",
            model_name=model_name,
            drop_similar_skus=drop_similar_skus
        )
        
    except Exception as e:
        error_msg = f"Batch submission error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.get(
    "/batch-status/{batch_id:path}",
    response_model=BatchStatusResponse,
    responses={
        200: {"description": "Batch status retrieved"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def batch_status(batch_id: str):
    """
    Check status of a batch job
    
    Status values:
    - queued: Job is waiting to be processed
    - in_progress: Job is currently being processed
    - ended: Job has completed (check request_counts for details)
    
    Args:
        batch_id: The batch job ID from /batch-submit
        
    Returns:
        BatchStatusResponse with current status
    """
    try:
        settings = get_settings()
        model_client = ModelAPIClient(
            gemini_api_key=settings.gemini_api_key,
            model_name="gemini-2.5-flash"
        )
        
        global active_batch_id
        
        logger.info(f"🔍 Checking batch status for: {batch_id}")
        status_info = model_client.get_batch_status(batch_id)

        if status_info.get("state") in {"JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"} and active_batch_id == batch_id:
            async with batch_lock:
                active_batch_id = None
        
        logger.info(f"✅ Batch status: {status_info['state']}")
        return BatchStatusResponse(
            success=True,
            batch_id=status_info["name"],
            status=status_info["state"],
            request_counts={},  # Gemini doesn't provide detailed request counts
            ended_at=status_info.get("update_time"),
            expires_at=None
        )
        
    except Exception as e:
        error_msg = f"Error checking batch status: {str(e)}"
        logger.error(f"❌ {error_msg}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.get(
    "/batch-results/{batch_id:path}",
    response_model=BatchResultsResponse,
    responses={
        200: {"description": "Batch results retrieved"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def batch_results(batch_id: str):
    """
    Retrieve results from a completed batch job
    
    Note: Only works for jobs with status='ended'
    
    Args:
        batch_id: The batch job ID from /batch-submit
        
    Returns:
        BatchResultsResponse with results for all offers
    """
    try:
        settings = get_settings()
        model_client = ModelAPIClient(
            gemini_api_key=settings.gemini_api_key,
            model_name="gemini-2.5-flash"
        )
        
        # Ensure batch is finished before fetching results
        status_info = model_client.get_batch_status(batch_id)
        if status_info.get("state") != "JOB_STATE_SUCCEEDED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Batch is not finished yet (status={status_info.get('state')}). Retry after it ends."
            )
        
        global active_batch_id, batch_preprocessing_stats, batch_request_mappings
        # Get batch results with request mapping
        request_id_mapping = batch_request_mappings.get(batch_id, {})
        batch_results_data = model_client.get_batch_results(batch_id, request_id_mapping)
        
        # Load preprocessing stats from global storage
        preprocessing_stats = batch_preprocessing_stats.get(batch_id, {})
        
        # Build response for each offer
        results = []
        successful_count = 0
        failed_count = 0
        
        for result in batch_results_data:
            offer_id = result["custom_id"]
            
            if result["success"]:
                # Flatten the estimated weights for batch response
                flattened_weights = []
                for product in result["data"]:
                    if 'skus' in product:
                        flattened_weights.extend(product['skus'])
                
                # Get preprocessing stats for this offer
                offer_stats = preprocessing_stats.get(offer_id, {})
                skus_were_identical = offer_stats.get("skus_were_identical", False)
                
                results.append({
                    "success": True,
                    "offer_id": offer_id,
                    "skus_were_identical": skus_were_identical,
                    "skus": flattened_weights
                    # Note: Gemini batch API doesn't provide usage stats per request
                })
                successful_count += 1
            else:
                results.append({
                    "success": False,
                    "offer_id": offer_id,
                    "error": result["error"]
                })
                failed_count += 1
        
        # Save batch results (only latest kept; older cleared at submit time)
        save_to_json(results, f"artifacts/batch_{batch_id}_results.json")

        async with batch_lock:
            if active_batch_id == batch_id:
                active_batch_id = None
            # Clean up preprocessing stats for completed batch
            if batch_id in batch_preprocessing_stats:
                del batch_preprocessing_stats[batch_id]
        
        return BatchResultsResponse(
            success=True,
            batch_id=batch_id,
            total_offers=len(results),
            successful_offers=successful_count,
            failed_offers=failed_count,
            results=results
        )
        
    except Exception as e:
        error_msg = f"Error retrieving batch results: {str(e)}"
        logger.error(error_msg)
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
    if settings.gemini_api_key:
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

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
    BatchWeightEstimationRequest,
    BatchWeightEstimationResponse,
    ErrorResponse
)
from app.modules.data_retrieval import DataRetriever
from app.modules.preprocessing import DataPreprocessor
from app.modules.model_api import ModelAPIClient
from app.modules.response_builder import ResponseBuilder
from app.utils.helpers import setup_logging, save_to_json, save_model_response_as_csv, save_text

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
        save_to_json(raw_data, f"artifacts/raw.json")

        # Step 2: Preprocess data (filter + optional duplicate removal)
        filtered_data = DataPreprocessor.filter_product_data(raw_data)
        if not filtered_data:
            raise ValueError("Failed to filter product data")
        save_to_json(filtered_data, f"artifacts/filtered.json")

        preprocessed_data, preprocessing_stats = DataPreprocessor.remove_duplicate_skus(
            [filtered_data], drop_duplicates=drop_similar_skus
        )
        logger.info(f"Preprocessing complete - {preprocessing_stats['skus_removed']} SKUs removed")
        save_to_json(preprocessed_data, f"artifacts/deduped.json")
        
        # Step 3: Initialize model client with user's choice and call API
        settings = get_settings()
        model_client = ModelAPIClient(
            api_key=settings.anthropic_api_key,
            model_name=model_name
        )
        estimated_data, api_stats, raw_model_text = model_client.estimate_weights(preprocessed_data)
        logger.info(f"Model estimation complete - {api_stats['total_tokens']} tokens used")
        
        # Save model response in JSON, CSV, and raw text formats
        save_to_json(estimated_data, f"artifacts/{offer_id}_model_response.json")
        save_model_response_as_csv(estimated_data, f"artifacts/{offer_id}_model_response.csv")
        save_text(raw_model_text, f"artifacts/{offer_id}_model_response_raw.txt")
        
        # Step 4: Build response with metadata
        response = ResponseBuilder.build_success_response(
            offer_id=offer_id,
            raw_data=raw_data,
            preprocessed_data=preprocessed_data,
            estimated_data=estimated_data,
            preprocessing_stats=preprocessing_stats,
            api_stats=api_stats
        )
        
        save_to_json(response.model_dump(by_alias=True), f"artifacts/response.json")

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


@app.post(
    "/estimate-weight-batch",
    response_model=BatchWeightEstimationResponse,
    responses={
        200: {"description": "Batch weight estimation completed"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def estimate_weight_batch(request: BatchWeightEstimationRequest):
    """
    Estimate product weights for multiple offer IDs in a single batch request
    
    Process:
    1. Retrieve all product data from MongoDB in one batch query
    2. Preprocess all products (filter, clean, remove duplicates)
    3. Call Claude API once with all products for efficient processing
    4. Return individual results for each offer ID
    
    Args:
        request: BatchWeightEstimationRequest containing list of offer_ids
        
    Returns:
        BatchWeightEstimationResponse with results for all offers
    """
    offer_ids = request.offer_ids
    model_name = request.model_name
    drop_similar_skus = request.drop_similar_skus
    
    logger.info(f"Received batch request for {len(offer_ids)} offer IDs | Model: {model_name}")
    
    results = []
    successful_count = 0
    failed_count = 0
    all_preprocessed_data = []
    offer_to_preprocessed_index = {}  # Map offer_id to index in preprocessed list
    
    try:
        # Step 1: Batch fetch all data from MongoDB
        raw_data_map = data_retriever.fetch_by_offer_ids(offer_ids)
        logger.info(f"Fetched {len([v for v in raw_data_map.values() if v])} products from database")
        
        # Step 2: Preprocess all products
        for offer_id in offer_ids:
            raw_data = raw_data_map.get(offer_id)
            
            if not raw_data:
                # Record error for missing offer
                failed_count += 1
                results.append(ErrorResponse(
                    success=False,
                    error=f"No product found with offer ID: {offer_id}",
                    offer_id=offer_id
                ))
                continue
            
            try:
                # Preprocess this product
                filtered_data = DataPreprocessor.filter_product_data(raw_data)
                if not filtered_data:
                    raise ValueError("Failed to filter product data")
                
                preprocessed_data, preprocessing_stats = DataPreprocessor.remove_duplicate_skus(
                    [filtered_data], drop_duplicates=drop_similar_skus
                )
                
                # Store mapping of offer_id to its index in the batch
                offer_to_preprocessed_index[offer_id] = len(all_preprocessed_data)
                all_preprocessed_data.extend(preprocessed_data)
                
                logger.info(f"Preprocessed offer {offer_id} - {preprocessing_stats['skus_removed']} SKUs removed")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Preprocessing failed for offer {offer_id}: {e}")
                results.append(ErrorResponse(
                    success=False,
                    error=f"Preprocessing error: {str(e)}",
                    offer_id=offer_id
                ))
        
        # Step 3: Call Claude API once with all preprocessed products
        if all_preprocessed_data:
            settings = get_settings()
            model_client = ModelAPIClient(
                api_key=settings.anthropic_api_key,
                model_name=model_name
            )
            
            estimated_data, api_stats, raw_model_text = model_client.estimate_weights(all_preprocessed_data)
            logger.info(f"Batch model estimation complete - {api_stats['total_tokens']} tokens used for {len(all_preprocessed_data)} products")
            
            # Save batch model response
            save_to_json(estimated_data, f"artifacts/batch_model_response.json")
            save_text(raw_model_text, f"artifacts/batch_model_response_raw.txt")
            
            # Step 4: Map results back to individual offers
            for offer_id in offer_ids:
                if offer_id not in offer_to_preprocessed_index:
                    continue  # Already recorded as error
                
                try:
                    idx = offer_to_preprocessed_index[offer_id]
                    estimated_product = estimated_data[idx]
                    
                    # Get original data for this offer
                    raw_data = raw_data_map[offer_id]
                    filtered_data = DataPreprocessor.filter_product_data(raw_data)
                    preprocessed_data, preprocessing_stats = DataPreprocessor.remove_duplicate_skus(
                        [filtered_data], drop_duplicates=drop_similar_skus
                    )
                    
                    # Build individual response
                    response = ResponseBuilder.build_success_response(
                        offer_id=offer_id,
                        raw_data=raw_data,
                        preprocessed_data=preprocessed_data,
                        estimated_data=[estimated_product],
                        preprocessing_stats=preprocessing_stats,
                        api_stats=api_stats  # Same stats for all in batch
                    )
                    
                    results.append(response)
                    successful_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Response building failed for offer {offer_id}: {e}")
                    results.append(ErrorResponse(
                        success=False,
                        error=f"Response building error: {str(e)}",
                        offer_id=offer_id
                    ))
        
        # Build batch response
        from app.models.schemas import ModelAPIStats
        batch_response = BatchWeightEstimationResponse(
            success=True,
            total_offers=len(offer_ids),
            successful_offers=successful_count,
            failed_offers=failed_count,
            results=results,
            model_api_stats=ModelAPIStats(**api_stats) if all_preprocessed_data else ModelAPIStats(
                api_calls_count=0,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                processing_time_seconds=0.0,
                model_name=model_name
            )
        )
        
        logger.info(f"Batch processing complete: {successful_count} successful, {failed_count} failed")
        return batch_response
        
    except Exception as e:
        error_msg = f"Batch processing error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug
    )

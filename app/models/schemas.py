"""
Pydantic Models for Request/Response Validation
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============ Request Models ============

class WeightEstimationRequest(BaseModel):
    """Request model for weight estimation endpoint"""
    offer_id: str = Field(..., description="The offer ID to process")
    

# ============ Response Models ============

class SKUDimensions(BaseModel):
    """Physical dimensions for a single SKU"""
    sku_id: str = Field(..., alias="skuId")
    length_cm: float = Field(..., alias="length_cm")
    width_cm: float = Field(..., alias="width_cm")
    height_cm: float = Field(..., alias="height_cm")
    weight_g: float = Field(..., alias="weight_g")
    
    class Config:
        populate_by_name = True


class ProcessedProduct(BaseModel):
    """Processed product with SKU dimensions"""
    skus: List[SKUDimensions]


class PreprocessingStats(BaseModel):
    """Statistics from preprocessing stage"""
    total_skus_before: int
    total_skus_after: int
    skus_removed: int
    duplicate_removal_applied: bool


class ModelAPIStats(BaseModel):
    """Statistics from model API call"""
    model_config = {"protected_namespaces": ()}
    
    api_calls_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    processing_time_seconds: float
    model_name: str = "claude-sonnet-4-5"


class WeightEstimationResponse(BaseModel):
    """Complete response with data and metadata"""
    model_config = {"protected_namespaces": ()}
    
    success: bool
    offer_id: str
    
    # Main data
    estimated_weights: List[ProcessedProduct]
    
    # Metadata
    preprocessing_stats: PreprocessingStats
    model_api_stats: ModelAPIStats
    
    # Raw input sizes for reference
    raw_data_size_chars: int
    preprocessed_data_size_chars: int
    
    # Optional error info
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    offer_id: Optional[str] = None

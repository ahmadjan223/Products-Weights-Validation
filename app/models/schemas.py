"""
Pydantic Models for Request/Response Validation
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator


# ============ Request Models ============

class WeightEstimationRequest(BaseModel):
    """Request model for weight estimation endpoint"""
    model_config = {"protected_namespaces": ()}
    
    offer_id: str = Field(..., description="The offer ID to process")
    model_name: Optional[str] = Field(
        default="claude-sonnet-4-5",
        description="Claude model to use for estimation"
    )
    drop_similar_skus: bool = Field(
        default=True,
        description="Whether to remove duplicate SKUs with identical dimensions"
    )
    

# ============ Response Models ============

class SKUDimensions(BaseModel):
    """Physical dimensions for a single SKU"""
    sku_id: Union[str, int] = Field(..., alias="skuId")
    length_cm: float = Field(..., alias="length_cm")
    width_cm: float = Field(..., alias="width_cm")
    height_cm: float = Field(..., alias="height_cm")
    weight_g: float = Field(..., alias="weight_g")
    
    @field_validator('sku_id', mode='before')
    @classmethod
    def convert_sku_id_to_string(cls, v):
        """Convert skuId to string if it's an integer"""
        return str(v) if v is not None else v
    
    class Config:
        populate_by_name = True


class ImputationStats(BaseModel):
    """Statistics about data imputation and corrections"""
    total_fields_processed: int = 0
    fields_imputed: int = 0
    fields_corrected: int = 0
    unit_conversions: int = 0
    success: bool = True


class ProcessedProduct(BaseModel):
    """Processed product with SKU dimensions"""
    skus: List[SKUDimensions]
    imputation_stats: Optional[ImputationStats] = None


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
    skus_were_identical: bool = Field(
        default=False,
        description="True if multiple SKUs were reduced to 1 due to identical dimensions"
    )
    
    # Main data
    estimated_weights: List[ProcessedProduct]
    
    # Metadata
    preprocessing_stats: PreprocessingStats
    model_api_stats: ModelAPIStats
    model_imputation_summary: Optional[ImputationStats] = None
    
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

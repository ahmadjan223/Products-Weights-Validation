"""
Response Builder Module
Constructs the final API response with all metadata
"""
from typing import Dict, List, Any
import json
import logging
from app.models.schemas import (
    WeightEstimationResponse,
    PreprocessingStats,
    ModelAPIStats,
    ProcessedProduct
)

logger = logging.getLogger(__name__)


class ResponseBuilder:
    """Builds structured API responses with metadata"""
    
    @staticmethod
    def build_success_response(
        offer_id: str,
        raw_data: Dict[Any, Any],
        preprocessed_data: List[Dict[str, Any]],
        estimated_data: List[Dict[str, Any]],
        preprocessing_stats: Dict[str, int],
        api_stats: Dict[str, Any]
    ) -> WeightEstimationResponse:
        """
        Build a successful response with all data and metadata
        
        Args:
            offer_id: The offer ID processed
            raw_data: Original raw data from MongoDB
            preprocessed_data: Data after preprocessing
            estimated_data: Weight estimation results from model
            preprocessing_stats: Stats from preprocessing stage
            api_stats: Stats from model API call
            
        Returns:
            WeightEstimationResponse object
        """
        # Calculate data sizes
        raw_data_size = len(json.dumps(raw_data, default=str))
        preprocessed_data_size = len(json.dumps(preprocessed_data, default=str))
        
        # Build preprocessing stats
        prep_stats = PreprocessingStats(
            total_skus_before=preprocessing_stats.get("total_skus_before", 0),
            total_skus_after=preprocessing_stats.get("total_skus_after", 0),
            skus_removed=preprocessing_stats.get("skus_removed", 0),
            duplicate_removal_applied=preprocessing_stats.get("skus_removed", 0) > 0
        )
        
        # Build model API stats
        model_stats = ModelAPIStats(
            api_calls_count=api_stats.get("api_calls_count", 1),
            input_tokens=api_stats.get("input_tokens", 0),
            output_tokens=api_stats.get("output_tokens", 0),
            total_tokens=api_stats.get("total_tokens", 0),
            processing_time_seconds=api_stats.get("processing_time_seconds", 0.0),
            model_name=api_stats.get("model_name", "claude-sonnet-4-5")
        )
        
        # Parse estimated data into ProcessedProduct objects
        processed_products = [
            ProcessedProduct(**product) for product in estimated_data
        ]
        
        # Calculate overall imputation summary
        imputation_summary = None
        if processed_products and processed_products[0].imputation_stats:
            # Aggregate stats from all products
            total_fields = sum(p.imputation_stats.total_fields_processed for p in processed_products if p.imputation_stats)
            fields_imputed = sum(p.imputation_stats.fields_imputed for p in processed_products if p.imputation_stats)
            fields_corrected = sum(p.imputation_stats.fields_corrected for p in processed_products if p.imputation_stats)
            unit_conversions = sum(p.imputation_stats.unit_conversions for p in processed_products if p.imputation_stats)
            all_success = all(p.imputation_stats.success for p in processed_products if p.imputation_stats)
            
            from app.models.schemas import ImputationStats
            imputation_summary = ImputationStats(
                total_fields_processed=total_fields,
                fields_imputed=fields_imputed,
                fields_corrected=fields_corrected,
                unit_conversions=unit_conversions,
                success=all_success
            )
        
        # Build complete response
        response = WeightEstimationResponse(
            success=True,
            offer_id=offer_id,
            skus_were_identical=preprocessing_stats.get("skus_were_identical", False),
            estimated_weights=processed_products,
            preprocessing_stats=prep_stats,
            model_api_stats=model_stats,
            model_imputation_summary=imputation_summary,
            raw_data_size_chars=raw_data_size,
            preprocessed_data_size_chars=preprocessed_data_size
        )
        
        logger.info(f"Successfully built response for offer ID: {offer_id}")
        
        return response
    
    @staticmethod
    def build_error_response(
        error_message: str,
        offer_id: str = None
    ) -> Dict[str, Any]:
        """
        Build an error response
        
        Args:
            error_message: Description of the error
            offer_id: Optional offer ID if available
            
        Returns:
            Error response dict
        """
        logger.error(f"❌ Building error response: {error_message}")
        
        return {
            "success": False,
            "error": error_message,
            "offer_id": offer_id
        }

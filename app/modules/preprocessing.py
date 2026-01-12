"""
Preprocessing Module
Handles data cleaning, filtering, and duplicate removal
"""
from typing import Dict, List, Any, Tuple, Optional, Union
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Handles all preprocessing operations on product data"""
    
    @staticmethod
    def filter_product_data(product_data) -> Union[Optional[Dict[str, Any]], Dict[str, Optional[Dict[str, Any]]]]:
        """
        Extract shipping, ID, and attribute information from product data
        
        Args:
            product_data: Single raw product (Dict) or bulk products (Dict[str, Dict])
            
        Returns:
            Single mode: Filtered product dict or None if invalid
            Bulk mode: Dict mapping offer_id to filtered product data
        """
        # Handle bulk mode (dict of offer_id -> raw_product)
        if isinstance(product_data, dict) and all(isinstance(k, str) and isinstance(v, (dict, type(None))) for k, v in product_data.items()):
            # Check if this looks like bulk data (string keys with dict/None values)
            if any(v is None or ('_id' in v and 'offerId' in v) for v in product_data.values() if v is not None):
                return DataPreprocessor._filter_bulk(product_data)
        
        # Handle single mode (direct product dict)
        return DataPreprocessor._filter_single(product_data)
    
    @staticmethod
    def _filter_single(product_json: Dict[Any, Any]) -> Optional[Dict[str, Any]]:
        """
        Internal method for single product filtering
        """
        # Safety check
        if not isinstance(product_json, dict):
            logger.warning("Invalid product data: not a dictionary")
            return None

        # --- 1. ID Handling ---
        raw_id = product_json.get('_id')
        product_id = raw_id.get('$oid') if isinstance(raw_id, dict) else raw_id

        # --- 2. Extract General Product Info ---
        sku_infos = product_json.get('productSkuInfos', [])
        if not isinstance(sku_infos, list):
            sku_infos = []

        first_sku_info = sku_infos[0] if sku_infos else {}
        if not isinstance(first_sku_info, dict):
            first_sku_info = {}

        product_shipping_info = first_sku_info.get('productShippingInfo', {})
        if not isinstance(product_shipping_info, dict):
            product_shipping_info = {}

        product_info = {
            "length": product_shipping_info.get('length'),
            "weight": product_shipping_info.get('weight'),
            "height": product_shipping_info.get('height'),
            "width": product_shipping_info.get('width'),
            "aiWeight": product_shipping_info.get('aiWeight')
        }

        # --- 3. Extract SKU Details & Attributes ---
        formatted_skus = []

        for info in sku_infos:
            if not isinstance(info, dict):
                continue

            # Extract SKU ID
            raw_sku_id = info.get('skuId')
            if isinstance(raw_sku_id, dict):
                sku_id = raw_sku_id.get('$numberLong')
            else:
                sku_id = raw_sku_id

            # Extract Attributes
            sku_attributes = info.get('skuAttributes', [])

            # Extract Dimensions
            detail = info.get('skuShippingDetail', {})
            if not isinstance(detail, dict):
                detail = {}

            sku_entry = {
                "skuId": sku_id,
                "skuAttributes": sku_attributes,
                "length": detail.get('length'),
                "weight": detail.get('weight'),
                "height": detail.get('height'),
                "width": detail.get('width'),
                "aiWeight": detail.get('aiWeight')
            }
            formatted_skus.append(sku_entry)

        # --- 4. Construct Final Output ---
        output_data = {
            "id": product_id,
            "categories": product_json.get('categories'),
            "name": product_json.get('name'),
            "Product info": product_info,
            "skus": formatted_skus
        }

        return output_data
    
    @staticmethod
    def _filter_bulk(products_data: Dict[str, Optional[Dict[Any, Any]]]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Internal method for bulk product filtering
        """
        result = {}
        for offer_id, raw_data in products_data.items():
            if raw_data is None:
                result[offer_id] = None
            else:
                try:
                    filtered = DataPreprocessor._filter_single(raw_data)
                    result[offer_id] = filtered
                except Exception as e:
                    logger.error(f"Error filtering offer ID {offer_id}: {e}")
                    result[offer_id] = None
        
        return result
    
    @staticmethod
    def remove_duplicate_skus(
        data, 
        drop_duplicates: bool = True
    ):
        """
        Remove duplicate SKUs when all SKUs have identical physical properties
        
        Args:
            data: Single mode: List of product dicts
                  Bulk mode: Dict[str, Optional[List[Dict]]] mapping offer_id to product list
            drop_duplicates: Whether to remove duplicate SKUs (default: True)
            
        Returns:
            Single mode: Tuple of (processed_data, stats_dict)
            Bulk mode: Tuple of (processed_products_dict, all_stats_dict)
        """
        # Handle bulk mode (dict of offer_id -> product list)
        if isinstance(data, dict):
            return DataPreprocessor._remove_duplicates_bulk(data, drop_duplicates)
        
        # Handle single mode (list of products)
        return DataPreprocessor._remove_duplicates_single(data, drop_duplicates)
    
    @staticmethod
    def _remove_duplicates_single(
        data: List[Dict[str, Any]], 
        drop_duplicates: bool = True
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Internal method for single mode duplicate removal
        """
        processed_data = deepcopy(data)
        
        # If not dropping duplicates, return data as-is with zero stats
        if not drop_duplicates:
            total_skus = sum(len(p.get('skus', [])) for p in data)
            return processed_data, {
                "total_skus_before": total_skus,
                "total_skus_after": total_skus,
                "skus_removed": 0
            }
        
        processed_data = deepcopy(data)
        stats = {
            "total_skus_before": 0,
            "total_skus_after": 0,
            "skus_removed": 0,
            "skus_were_identical": False
        }
        
        for product in processed_data:
            if 'skus' not in product or len(product['skus']) <= 1:
                stats["total_skus_before"] += len(product.get('skus', []))
                stats["total_skus_after"] += len(product.get('skus', []))
                continue
            
            skus = product['skus']
            stats["total_skus_before"] += len(skus)
            
            first_sku = skus[0]
            
            # Extract weight from first SKU
            first_weight = first_sku.get('weight')
            
            # Check if weight is null or zero - if so, skip duplicate removal
            if first_weight is None or first_weight == 0:
                logger.info(f"Product {product.get('name', 'Unknown')}: Skipping duplicate removal - weight is null or zero")
                stats["total_skus_after"] += len(skus)
                continue
            
            # Check if all SKUs have identical weight
            all_identical = True
            for sku in skus[1:]:
                sku_weight = sku.get('weight')
                
                # If any SKU has null or zero weight, don't drop
                if sku_weight is None or sku_weight == 0:
                    all_identical = False
                    break
                
                # If weights differ, don't drop
                if sku_weight != first_weight:
                    all_identical = False
                    break
            
            # If all weights are identical and valid, keep only first SKU
            if all_identical:
                logger.info(f"Product {product.get('name', 'Unknown')}: Reduced from {len(skus)} to 1 SKU")
                product['skus'] = [first_sku]
                stats["total_skus_after"] += 1
                stats["skus_were_identical"] = True
            else:
                stats["total_skus_after"] += len(skus)
        
        stats["skus_removed"] = stats["total_skus_before"] - stats["total_skus_after"]
        
        return processed_data, stats
    
    @staticmethod
    def _remove_duplicates_bulk(
        filtered_products: Dict[str, Optional[List[Dict[str, Any]]]], 
        drop_duplicates: bool = True
    ) -> Tuple[Dict[str, Optional[List[Dict[str, Any]]]], Dict[str, Dict[str, int]]]:
        """
        Internal method for bulk duplicate removal
        """
        processed_products = {}
        all_stats = {}
        
        for offer_id, product_data in filtered_products.items():
            if product_data is None:
                processed_products[offer_id] = None
                all_stats[offer_id] = {
                    "total_skus_before": 0,
                    "total_skus_after": 0,
                    "skus_removed": 0
                }
            else:
                try:
                    # Convert single product to list for processing
                    processed_data, stats = DataPreprocessor._remove_duplicates_single([product_data], drop_duplicates)
                    processed_products[offer_id] = processed_data
                    all_stats[offer_id] = stats
                except Exception as e:
                    logger.error(f"Error processing duplicates for offer ID {offer_id}: {e}")
                    processed_products[offer_id] = None
                    all_stats[offer_id] = {
                        "total_skus_before": 0,
                        "total_skus_after": 0,
                        "skus_removed": 0
                    }
        
        return processed_products, all_stats
    
    @classmethod
    def preprocess_pipeline(
        cls, 
        raw_product: Dict[Any, Any],
        drop_duplicates: bool = True
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Complete preprocessing pipeline
        
        Args:
            raw_product: Raw product data from MongoDB
            drop_duplicates: Whether to remove duplicate SKUs (default: True)
            
        Returns:
            Tuple of (cleaned_data, preprocessing_stats)
        """
        # Step 1: Filter and structure data
        filtered = cls.filter_product_data(raw_product)
        
        if not filtered:
            raise ValueError("Failed to filter product data")
        
        # Step 2: Remove duplicate SKUs
        cleaned_data, stats = cls.remove_duplicate_skus([filtered], drop_duplicates)
        
        logger.info(f"Preprocessing complete: {stats['skus_removed']} SKUs removed")
        
        return cleaned_data, stats

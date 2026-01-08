"""
Preprocessing Module
Handles data cleaning, filtering, and duplicate removal
"""
from typing import Dict, List, Any, Tuple, Optional
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Handles all preprocessing operations on product data"""
    
    @staticmethod
    def filter_product_data(product_json: Dict[Any, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract shipping, ID, and attribute information from product JSON
        
        Args:
            product_json: Raw product data from MongoDB
            
        Returns:
            Filtered product dict or None if invalid
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
    def remove_duplicate_skus(
        data: List[Dict[str, Any]], 
        drop_duplicates: bool = True
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Remove duplicate SKUs when all SKUs have identical physical properties
        
        Args:
            data: List of processed product dicts
            drop_duplicates: Whether to remove duplicate SKUs (default: True)
            
        Returns:
            Tuple of (processed_data, stats_dict)
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
            "skus_removed": 0
        }
        
        for product in processed_data:
            if 'skus' not in product or len(product['skus']) <= 1:
                stats["total_skus_before"] += len(product.get('skus', []))
                stats["total_skus_after"] += len(product.get('skus', []))
                continue
            
            skus = product['skus']
            stats["total_skus_before"] += len(skus)
            
            first_sku = skus[0]
            
            # Extract physical properties from first SKU
            first_props = {
                'weight': first_sku.get('weight'),
                'length': first_sku.get('length'),
                'height': first_sku.get('height'),
                'width': first_sku.get('width'),
                'aiWeight': first_sku.get('aiWeight')
            }
            
            # Check if all properties are null
            all_props_null = all(value is None for value in first_props.values())
            if all_props_null:
                logger.info(f"Product {product.get('name', 'Unknown')}: Skipping duplicate removal - all properties null")
                stats["total_skus_after"] += len(skus)
                continue
            
            # Check if all SKUs have identical physical properties
            all_identical = True
            for sku in skus[1:]:
                sku_props = {
                    'weight': sku.get('weight'),
                    'length': sku.get('length'),
                    'height': sku.get('height'),
                    'width': sku.get('width'),
                    'aiWeight': sku.get('aiWeight')
                }
                
                if sku_props != first_props:
                    all_identical = False
                    break
            
            # If all identical, keep only first SKU
            if all_identical:
                logger.info(f"Product {product.get('name', 'Unknown')}: Reduced from {len(skus)} to 1 SKU")
                product['skus'] = [first_sku]
                stats["total_skus_after"] += 1
            else:
                stats["total_skus_after"] += len(skus)
        
        stats["skus_removed"] = stats["total_skus_before"] - stats["total_skus_after"]
        
        return processed_data, stats
    
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

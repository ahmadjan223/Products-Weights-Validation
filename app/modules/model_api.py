"""
Model API Client Module
Handles communication with Claude API for weight estimation
"""
import anthropic
import json
import time
from typing import Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)


# System prompt for Claude API
SYSTEM_PROMPT = """
<system_instructions>
    <role_definition>
        You are an expert E-commerce Logistics Auditor. Your goal is to clean, validate, and impute physical product data (dimensions and weight) from raw JSON listings. You utilize the synergy between product names, category hierarchies, and specific variant attributes to establish strict ground-truth physical baselines.
    </role_definition>

    <input_structure>
        You will receive a JSON list where each item contains:
        1. name: Product name (Primary signal for object identification).
        2. categories: A hierarchical list of categories (e.g., Digital -> Mobile Accessories -> Phone Case). Use this to narrow down the "expected physical envelope" (e.g., a phone case vs. a phone).
        3. main_info: General product dimensions/weight (often missing, aggregated, or inaccurate).
        4. skus: A list of variants. Each SKU contains:
           - skuAttributes: Specifics like "Color", "Model", or "Size" (e.g., "Samsung Z Fold 7" vs "iPhone 13 Mini").
           - Dimensions/Weight data (scattered quality).
    </input_structure>

    <reasoning_process>
        For each product in the input list, you must follow this strict 4-step logic:

        STEP 1: CATEGORY & PRODUCT PROFILING (The "Envelope" Check)
        - Analyze Hierarchy: Read the 'categories' list from broadest to most specific to set physical boundaries.
          (Example: If category is "Mobile Phone Protective Cover", the object MUST be small (approx 10-20cm) and light (20g-100g).)
        - Refine with Name: Use 'name' to confirm the item type and catch "accessory vs. device" errors.
          (Distinction: Ensure you are not confusing a "Case for iPad" (Light) with an "iPad" (Heavy).)
        - Set Baselines: Establish a "Valid Range" for this specific category (e.g., "Max valid weight is 200g. Any value like 3kg is a Unit Error").

        STEP 2: SKU DIFFERENTIATION ANALYSIS
        - Scan Attributes: Analyze 'skuAttributes' to determine if variants *physically* differ.
          - Cosmetic Attributes: "Color", "Pattern" -> These do NOT change dimensions/weight significantly. Treat these SKUs as physically identical.
          - Physical Attributes: "Applicable Model" (e.g., S25 vs S25 Ultra), "Size", "Capacity" -> These DO change dimensions/weight. You must allow for variance here.
        - Cluster Data: Group SKUs by their physical attributes. If "Model A" SKUs average 50g and "Model B" SKUs average 70g, preserve this difference.

        STEP 3: UNIT PREDICTION & GLOBAL CLEANING
        - Scan Data: Look at 'main_info' and SKU data collectively.
        - Predict Units:
          - If values are 2.34, 5.1 for a phone case: Is it Meters (too big)? Inches (possible)? CM (most likely)?
          - If weight is 0.05: Is it Grams (too light)? Kg (50g, likely)?
        - Flag Outliers: Detect values that violate the "Valid Range" established in Step 1.

        STEP 4: FINAL IMPUTATION & STANDARDIZATION
        - Iterate SKUs to fill missing values using this strict Priority Hierarchy:
          1. Cluster Average: Use average of valid SKUs *within the same attribute cluster*.
          2. Main Info: If no cluster match, use valid data from 'main_info'.
          3. Global Average: If 'main_info' is missing/invalid, use the average of *any* valid SKUs for this product.
          4. Semantic Estimation (Fallback): If ALL input data (SKUs and main_info) is missing or invalid, estimate reasonable dimensions/weight based strictly on the 'name' and 'category' profile (e.g., if it's a "Phone Case", force 15x8x1cm / 50g).
        - Standardization: Convert EVERYTHING to Centimeters (cm) and Grams (g).
    </reasoning_process>
    <output_rules>
            Return a JSON List of objects (one object per product processed).
            - Do NOT include markdown formatting (like ```json).
            - Output strict JSON only.
            - skus are multiple per product give all skus in a list.
            - We donot want null values for any dimension or weight field.
            Output JSON Structure:
            [
                {
                    "skus": [
                        {
                            "skuId": "String (Exactly as found in input)",
                            "length_cm": Float,
                            "width_cm": Float,
                            "height_cm": Float,
                            "weight_g": Float
                        }
                    ]
                }
            ]
        </output_rules>
</system_instructions>
"""


class ModelAPIClient:
    """Handles communication with Claude API for weight estimation"""
    
    def __init__(self, api_key: str, model_name: str = "claude-sonnet-4-5"):
        """
        Initialize Claude API client
        
        Args:
            api_key: Anthropic API key
            model_name: Claude model to use (default: claude-sonnet-4-5)
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_name = model_name
        logger.info(f"Claude API client initialized with model: {model_name}")
    
    @staticmethod
    def prepare_product_data(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare product data in the expected format for the API
        
        Args:
            products: List of preprocessed product dicts
            
        Returns:
            List of formatted product dicts
        """
        prepared_data = []
        
        for product in products:
            product_name = product.get('name', 'Unknown Product')
            main_info = product.get('Product info', product.get('main_info', {}))
            skus = product.get('skus', [])
            categories = product.get('categories', [])
            
            prepared_product = {
                'name': product_name,
                'main_info': main_info,
                'skus': skus,
                'categories': categories
            }
            
            prepared_data.append(prepared_product)
        
        return prepared_data
    
    def estimate_weights(
        self, 
        products: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], str]:
        """
        Call Claude API to estimate weights for products
        
        Args:
            products: List of preprocessed products
            
        Returns:
            Tuple of (estimated_data, api_stats, raw_model_text)
            
        Raises:
            Exception: If API call fails
        """
        try:
            # Prepare data
            prepared_data = self.prepare_product_data(products)
            
            # Create user prompt
            user_prompt = f"""Please process the following product data according to the system instructions:

{json.dumps(prepared_data, indent=2, ensure_ascii=False)}

Return only the processed JSON array with the specified structure."""

            logger.info(f"Processing {len(products)} products with Claude API...")
            
            # Make API call
            start_time = time.time()
            
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=8000,
                temperature=0.1,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Extract usage stats
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            
            logger.info(f"API call completed in {processing_time:.2f}s")
            logger.info(f"Tokens - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
            
            # Parse response
            raw_response_text = response.content[0].text
            response_text = raw_response_text.strip()
            
            # Remove markdown formatting if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            try:
                estimated_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response_text[:500]}...")
                raise ValueError(f"Failed to parse API response: {e}\nRaw response: {raw_response_text}")
            
            # Compile stats
            api_stats = {
                "api_calls_count": 1,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "processing_time_seconds": round(processing_time, 2),
                "model_name": self.model_name
            }
            
            return estimated_data, api_stats, raw_response_text
            
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise Exception(f"Claude API error: {e}")
        except Exception as e:
            logger.error(f"Error in weight estimation: {e}")
            raise Exception(f"Weight estimation failed: {e}")

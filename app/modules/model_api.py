"""
Model API Client Module
Handles communication with AI APIs for weight estimation
- Gemini (Google AI) for single requests
- Claude (Anthropic) for batch processing
"""
import anthropic
from google import genai
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
    """Handles communication with AI APIs for weight estimation"""
    
    def __init__(
        self, 
        anthropic_api_key: str = None,
        gemini_api_key: str = None,
        model_name: str = "gemini-2.5-flash"
    ):
        """
        Initialize AI API client
        
        Args:
            anthropic_api_key: Anthropic API key (for batch processing)
            gemini_api_key: Google Gemini API key (for single requests)
            model_name: Model to use (default: gemini-2.5-flash)
        """
        # Initialize Anthropic for batch processing
        if anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
            logger.info("Anthropic API client initialized for batch processing")
        else:
            self.anthropic_client = None
            
        # Store Gemini API key for single requests
        if gemini_api_key:
            self.gemini_client = genai.Client(api_key=gemini_api_key)
            self.gemini_api_key = gemini_api_key
            logger.info("Google Gemini API initialized with API key")
        else:
            self.gemini_client = None
            self.gemini_api_key = None
            
        self.model_name = model_name
        logger.info(f"Model API client initialized with model: {model_name}")
    
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
        Call Gemini API to estimate weights for products
        
        Args:
            products: List of preprocessed products
            
        Returns:
            Tuple of (estimated_data, api_stats, raw_model_text)
            
        Raises:
            Exception: If API call fails
        """
        if not self.gemini_api_key:
            raise ValueError("Gemini API not initialized. Provide gemini_api_key.")
            
        try:
            # Prepare data
            prepared_data = self.prepare_product_data(products)
            
            # Create user prompt
            user_prompt = f"""Please process the following product data according to the system instructions:

{json.dumps(prepared_data, indent=2, ensure_ascii=False)}

Return only the processed JSON array with the specified structure."""

            logger.info(f"Processing {len(products)} products with Gemini API...")
            
            # Make API call
            start_time = time.time()
            
            # Combine system prompt and user prompt for Gemini
            full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"
            
            # Call Gemini API using new client
            response = self.gemini_client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config={
                    "temperature": 0.1,
                    "max_output_tokens": 8000,
                }
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Extract usage stats
            input_tokens = getattr(response, 'prompt_token_count', 0)
            output_tokens = getattr(response, 'candidates_token_count', 0)
            total_tokens = input_tokens + output_tokens
            
            logger.info(f"API call completed in {processing_time:.2f}s")
            logger.info(f"Tokens - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
            
            # Parse response
            raw_response_text = response.text
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
            
        except Exception as e:
            if "gemini" in str(e).lower() or "api" in str(e).lower():
                logger.error(f"Gemini API error: {e}")
                raise Exception(f"Gemini API error: {e}")
            logger.error(f"Error in weight estimation: {e}")
            raise Exception(f"Weight estimation failed: {e}")
    
    def create_batch_job(
        self,
        requests_data: List[Dict[str, Any]]
    ) -> str:
        """
        Create a Claude Batch API job for async processing (50% cost savings)
        Uses Anthropic Claude for batch operations
        
        Args:
            requests_data: List of request dictionaries with custom_id and products
            
        Returns:
            batch_id: ID to track the batch job
        """
        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized. Provide anthropic_api_key for batch processing.")
            
        try:
            # Prepare batch requests in Claude's format
            batch_requests = []
            
            for req_data in requests_data:
                offer_id = req_data["custom_id"]
                products = req_data["products"]
                
                # Prepare product data
                prepared_data = self.prepare_product_data(products)
                
                # Create user prompt
                user_prompt = f"""Please process the following product data according to the system instructions:

{json.dumps(prepared_data, indent=2, ensure_ascii=False)}

Return only the processed JSON array with the specified structure."""
                
                # Format as batch request
                batch_request = {
                    "custom_id": offer_id,
                    "params": {
                        "model": self.model_name,
                        "max_tokens": 20000,
                        "temperature": 0.1,
                        "system": SYSTEM_PROMPT,
                        "messages": [
                            {
                                "role": "user",
                                "content": user_prompt
                            }
                        ]
                    }
                }
                batch_requests.append(batch_request)
            
            logger.info(f"Creating batch job with {len(batch_requests)} requests...")
            
            # Create batch job using Anthropic beta API
            message_batch = self.anthropic_client.beta.messages.batches.create(
                requests=batch_requests
            )
            
            batch_id = message_batch.id
            logger.info(f"✅ Batch job created: {batch_id}")
            
            return batch_id
            
        except Exception as e:
            logger.error(f"Error creating batch job: {e}")
            raise Exception(f"Failed to create batch job: {e}")
    
    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Check status of a batch job
        
        Args:
            batch_id: The batch job ID
            
        Returns:
            Status information dictionary
        """
        try:
            message_batch = self.anthropic_client.beta.messages.batches.retrieve(batch_id)
            
            status_info = {
                "id": message_batch.id,
                "processing_status": message_batch.processing_status,
                "request_counts": {
                    "processing": message_batch.request_counts.processing,
                    "succeeded": message_batch.request_counts.succeeded,
                    "errored": message_batch.request_counts.errored,
                    "canceled": message_batch.request_counts.canceled,
                    "expired": message_batch.request_counts.expired
                },
                "ended_at": message_batch.ended_at,
                "expires_at": message_batch.expires_at,
                "results_url": message_batch.results_url if hasattr(message_batch, 'results_url') else None
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error retrieving batch status: {e}")
            raise Exception(f"Failed to get batch status: {e}")
    
    def get_batch_results(self, batch_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve results from a completed batch job
        
        Args:
            batch_id: The batch job ID
            
        Returns:
            List of results for each request
        """
        try:
            # Get batch results
            results = []
            
            for result in self.anthropic_client.beta.messages.batches.results(batch_id):
                custom_id = result.custom_id
                
                if result.result.type == "succeeded":
                    # Parse successful response
                    response_text = result.result.message.content[0].text.strip()
                    
                    # Remove markdown formatting if present
                    if response_text.startswith('```json'):
                        response_text = response_text[7:]
                    if response_text.endswith('```'):
                        response_text = response_text[:-3]
                    response_text = response_text.strip()
                    
                    try:
                        estimated_data = json.loads(response_text)
                        results.append({
                            "custom_id": custom_id,
                            "success": True,
                            "data": estimated_data,
                            "usage": {
                                "input_tokens": result.result.message.usage.input_tokens,
                                "output_tokens": result.result.message.usage.output_tokens
                            }
                        })
                    except json.JSONDecodeError as e:
                        results.append({
                            "custom_id": custom_id,
                            "success": False,
                            "error": f"Failed to parse response: {e}"
                        })
                else:
                    # Handle error
                    error_info = result.result.error if hasattr(result.result, 'error') else result.result
                    error_msg = str(error_info) if error_info else "Unknown error"
                    results.append({
                        "custom_id": custom_id,
                        "success": False,
                        "error": error_msg
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving batch results: {e}")
            raise Exception(f"Failed to get batch results: {e}")

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
        gemini_api_key: str = None,
        model_name: str = "gemini-2.5-flash"
    ):
        """
        Initialize AI API client
        
        Args:
            gemini_api_key: Google Gemini API key (for single and batch requests)
            model_name: Model to use (default: gemini-2.5-flash)
        """
        # Initialize Gemini for single and batch requests
        if gemini_api_key:
            self.gemini_client = genai.Client(api_key=gemini_api_key)
            self.gemini_api_key = gemini_api_key
            logger.info("Google Gemini API initialized for single and batch processing")
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
        Create a Gemini Batch API job for async processing
        Uses Google Gemini for batch operations
        
        Args:
            requests_data: List of request dictionaries with custom_id and products
            
        Returns:
            batch_name: Name to track the batch job (e.g., batches/...)
        """
        if not self.gemini_client:
            raise ValueError("Gemini client not initialized. Provide gemini_api_key for batch processing.")
            
        try:
            # Prepare batch requests in Gemini's format
            inline_requests = []
            
            for req_data in requests_data:
                offer_id = req_data["custom_id"]
                products = req_data["products"]
                
                # Prepare product data
                prepared_data = self.prepare_product_data(products)
                
                # Create user prompt combining system and user instructions
                full_prompt = f"""{SYSTEM_PROMPT}

Please process the following product data according to the system instructions:

{json.dumps(prepared_data, indent=2, ensure_ascii=False)}

Return only the processed JSON array with the specified structure."""
                
                # Format as Gemini batch request
                batch_request = {
                    'contents': [{
                        'parts': [{'text': full_prompt}],
                        'role': 'user'
                    }],
                    'custom_id': offer_id  # Store custom_id for result mapping
                }
                inline_requests.append(batch_request)
            
            logger.info(f"Creating Gemini batch job with {len(inline_requests)} requests...")
            
            # Create batch job using Gemini API
            inline_batch_job = self.gemini_client.batches.create(
                model=f"models/{self.model_name}",
                src=inline_requests,
                config={
                    'display_name': f"weight-estimation-batch-{int(time.time())}",
                },
            )
            
            batch_name = inline_batch_job.name
            logger.info(f"✅ Gemini batch job created: {batch_name}")
            
            return batch_name
            
        except Exception as e:
            logger.error(f"Error creating Gemini batch job: {e}")
            raise Exception(f"Failed to create batch job: {e}")
    
    def get_batch_status(self, batch_name: str) -> Dict[str, Any]:
        """
        Check status of a Gemini batch job
        
        Args:
            batch_name: The batch job name (e.g., batches/...)
            
        Returns:
            Status information dictionary
        """
        try:
            batch_job = self.gemini_client.batches.get(name=batch_name)
            
            status_info = {
                "name": batch_job.name,
                "state": batch_job.state.name,
                "create_time": str(batch_job.create_time) if hasattr(batch_job, 'create_time') else None,
                "update_time": str(batch_job.update_time) if hasattr(batch_job, 'update_time') else None,
                "error": str(batch_job.error) if hasattr(batch_job, 'error') and batch_job.error else None
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error retrieving Gemini batch status: {e}")
            raise Exception(f"Failed to get batch status: {e}")
    
    def get_batch_results(self, batch_name: str) -> List[Dict[str, Any]]:
        """
        Retrieve results from a completed Gemini batch job
        
        Args:
            batch_name: The batch job name (e.g., batches/...)
            
        Returns:
            List of results for each request
        """
        try:
            batch_job = self.gemini_client.batches.get(name=batch_name)
            
            if batch_job.state.name != 'JOB_STATE_SUCCEEDED':
                raise ValueError(f"Batch job not successful. State: {batch_job.state.name}")
            
            results = []
            
            # Check if results are inline
            if batch_job.dest and batch_job.dest.inlined_responses:
                for i, inline_response in enumerate(batch_job.dest.inlined_responses):
                    # Extract custom_id (stored in request at same index)
                    custom_id = f"request_{i}"  # Default fallback
                    
                    if inline_response.response:
                        try:
                            # Get response text
                            response_text = inline_response.response.text.strip()
                            
                            # Remove markdown formatting if present
                            if response_text.startswith('```json'):
                                response_text = response_text[7:]
                            if response_text.endswith('```'):
                                response_text = response_text[:-3]
                            response_text = response_text.strip()
                            
                            estimated_data = json.loads(response_text)
                            results.append({
                                "custom_id": custom_id,
                                "success": True,
                                "data": estimated_data
                            })
                        except (AttributeError, json.JSONDecodeError) as e:
                            results.append({
                                "custom_id": custom_id,
                                "success": False,
                                "error": f"Failed to parse response: {e}"
                            })
                    elif inline_response.error:
                        results.append({
                            "custom_id": custom_id,
                            "success": False,
                            "error": str(inline_response.error)
                        })
            
            # Check if results are in a file
            elif batch_job.dest and batch_job.dest.file_name:
                result_file_name = batch_job.dest.file_name
                logger.info(f"Downloading results from file: {result_file_name}")
                
                file_content = self.gemini_client.files.download(file=result_file_name)
                file_text = file_content.decode('utf-8')
                
                # Parse JSONL format (one JSON object per line)
                for line in file_text.strip().split('\n'):
                    if line.strip():
                        try:
                            result_obj = json.loads(line)
                            custom_id = result_obj.get('custom_id', 'unknown')
                            
                            if 'response' in result_obj:
                                response_text = result_obj['response'].get('text', '')
                                estimated_data = json.loads(response_text)
                                results.append({
                                    "custom_id": custom_id,
                                    "success": True,
                                    "data": estimated_data
                                })
                            else:
                                results.append({
                                    "custom_id": custom_id,
                                    "success": False,
                                    "error": result_obj.get('error', 'Unknown error')
                                })
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse result line: {e}")
            else:
                raise ValueError("No results found (neither file nor inline)")
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving Gemini batch results: {e}")
            raise Exception(f"Failed to get batch results: {e}")

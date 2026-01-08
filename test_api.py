"""
Test script to verify API functionality
"""
import requests
import json


def test_health_check():
    """Test health check endpoint"""
    print("🔍 Testing health check endpoint...")
    response = requests.get("http://localhost:8000/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_root():
    """Test root endpoint"""
    print("🔍 Testing root endpoint...")
    response = requests.get("http://localhost:8000/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_estimate_weight(offer_id: str):
    """Test weight estimation endpoint"""
    print(f"🔍 Testing weight estimation for offer ID: {offer_id}...")
    
    payload = {"offer_id": offer_id}
    response = requests.post(
        "http://localhost:8000/estimate-weight",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Success!")
        print(f"\nOffer ID: {result['offer_id']}")
        print(f"\nPreprocessing Stats:")
        print(f"  - SKUs before: {result['preprocessing_stats']['total_skus_before']}")
        print(f"  - SKUs after: {result['preprocessing_stats']['total_skus_after']}")
        print(f"  - SKUs removed: {result['preprocessing_stats']['skus_removed']}")
        print(f"\nModel API Stats:")
        print(f"  - Model: {result['model_api_stats']['model_name']}")
        print(f"  - Input tokens: {result['model_api_stats']['input_tokens']}")
        print(f"  - Output tokens: {result['model_api_stats']['output_tokens']}")
        print(f"  - Total tokens: {result['model_api_stats']['total_tokens']}")
        print(f"  - Processing time: {result['model_api_stats']['processing_time_seconds']}s")
        print(f"\nEstimated Weights:")
        for product in result['estimated_weights']:
            print(f"  Product has {len(product['skus'])} SKU(s):")
            for sku in product['skus']:
                # Handle both skuId and sku_id formats
                sku_id = sku.get('skuId') or sku.get('sku_id', 'Unknown')
                print(f"    - SKU {sku_id}:")
                print(f"      Length: {sku.get('length_cm', 'N/A')} cm")
                print(f"      Width: {sku.get('width_cm', 'N/A')} cm")
                print(f"      Height: {sku.get('height_cm', 'N/A')} cm")
                print(f"      Weight: {sku.get('weight_g', 'N/A')} g")
    else:
        print("❌ Error!")
        print(f"Response: {response.text}")
    
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Weight Estimation API - Test Script")
    print("=" * 60)
    print()
    
    # Test basic endpoints
    test_root()
    test_health_check()
    
    # Test weight estimation with the offer ID from the notebook
    offer_id = "624730890959"
    test_estimate_weight(offer_id)
    
    print("=" * 60)
    print("Testing complete!")
    print("=" * 60)

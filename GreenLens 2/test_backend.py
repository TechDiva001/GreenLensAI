import requests
import json
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Base URL for the local backend
BASE_URL = "http://127.0.0.1:8000"

def print_result(endpoint, response):
    logger.info(f"--- Testing {endpoint} ---")
    logger.info(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        logger.info(f"Response Data:\n{json.dumps(data, indent=2)}\n")
    except Exception:
        logger.info(f"Raw Text Response:\n{response.text}\n")

def run_tests():
    logger.info(f"Starting Backend Tests at {BASE_URL}...\n")
    
    # 1. Test Health Check Endpoint
    try:
        res = requests.get(f"{BASE_URL}/api/health")
        print_result("GET /api/health", res)
    except requests.exceptions.ConnectionError:
        logger.error(f"Failed to connect to {BASE_URL}. Is your FastAPI server running?")
        return
        
    # 2. Test Analyze Image Endpoint
    # Note: Replace 'image_url' with a valid public image URL or a signed Supabase URL for real testing.
    # We will test if the endpoint structure works. It might return 500 if the image_url is fake and the download fails,
    # but 422 if the payload is bad.
    analyze_payload = {
        "image_url": "https://via.placeholder.com/150", 
        "user_id": "test-user-123",
        "latitude": 5.6037,
        "longitude": -0.1870,
        "description": "Test report from test script",
        "historical_flooding": False
    }
    
    try:
        res = requests.post(f"{BASE_URL}/api/ai/analyze-image", json=analyze_payload)
        print_result("POST /api/ai/analyze-image", res)
    except Exception as e:
        logger.error(f"Failed to test /api/ai/analyze-image: {e}")

if __name__ == "__main__":
    run_tests()

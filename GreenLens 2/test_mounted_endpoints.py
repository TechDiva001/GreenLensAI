import os
import sys
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

# Mock images for cleanup verification
MOCK_BEFORE_IMG = "mock_test_before.jpg"
MOCK_AFTER_IMG = "mock_test_after.jpg"

def setup_mock_images():
    img_before = Image.new("RGB", (200, 200), color=(100, 60, 30))
    draw = ImageDraw.Draw(img_before)
    draw.rectangle([40, 40, 160, 160], fill=(200, 30, 30))
    img_before.save(MOCK_BEFORE_IMG)

    img_after = Image.new("RGB", (200, 200), color=(30, 150, 30))
    draw = ImageDraw.Draw(img_after)
    draw.rectangle([70, 70, 130, 130], fill=(100, 180, 100))
    img_after.save(MOCK_AFTER_IMG)

def cleanup_mock_images():
    for f in [MOCK_BEFORE_IMG, MOCK_AFTER_IMG]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

def main():
    setup_mock_images()
    try:
        from main import app
        client = TestClient(app)
        
        print("="*70)
        print("RUNNING GREENLENS FASTAPI ENDPOINT VERIFICATION TESTS")
        print("="*70)

        # 1. Test Health Check
        print("\n[TEST 1] GET /api/health")
        res = client.get("/api/health")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 200
        assert "WeatherAPI" in res.json().get("weather_engine", "")
        print("--> PASS: Health check endpoint working.")

        # 2. Test Weather Forecast (WeatherAPI)
        print("\n[TEST 2] GET /api/weather/forecast (Accra: lat=5.6037, lon=-0.1870)")
        res = client.get("/api/weather/forecast?latitude=5.6037&longitude=-0.1870")
        print(f"Status: {res.status_code}")
        w_data = res.json()
        print(f"  Source: {w_data.get('source')}")
        print(f"  Location: {w_data.get('location')}")
        print(f"  Current Temp: {w_data.get('current', {}).get('temp_c')}°C ({w_data.get('current', {}).get('condition_text')})")
        print(f"  Rain 24h: {w_data.get('rain_24h_mm')} mm (Prob: {w_data.get('rain_probability_24h')}%)")
        print(f"  Rain 48h: {w_data.get('rain_48h_mm')} mm (Prob: {w_data.get('rain_probability_48h')}%)")
        print(f"  Daily cards count: {len(w_data.get('daily_forecast', []))}")
        assert res.status_code == 200
        assert "rain_24h_mm" in w_data
        print("--> PASS: WeatherAPI forecast endpoint working.")

        # 3. Test Weather Current
        print("\n[TEST 3] GET /api/weather/current")
        res = client.get("/api/weather/current?latitude=5.6037&longitude=-0.1870")
        print(f"Status: {res.status_code}")
        assert res.status_code == 200
        print("--> PASS: Current weather endpoint working.")

        # 4. Test Cleanup Verification
        print("\n[TEST 4] POST /api/ai/verify-cleanup")
        before_abs = os.path.abspath(MOCK_BEFORE_IMG)
        after_abs = os.path.abspath(MOCK_AFTER_IMG)
        res = client.post("/api/ai/verify-cleanup", json={
            "report_id": "GL-TEST01",
            "before_image_url": before_abs,
            "after_image_url": after_abs
        })
        print(f"Status: {res.status_code}")
        v_data = res.json()
        print(f"  Report ID: {v_data.get('report_id')}")
        print(f"  Status: {v_data.get('status')}")
        print(f"  Verified: {v_data.get('verified')}")
        print(f"  Improvement: {v_data.get('improvement_percentage')}%")
        print(f"  Explanation: {v_data.get('explanation')}")
        assert res.status_code == 200
        assert "verified" in v_data
        print("--> PASS: Cleanup verification endpoint working.")

        # 5. Test Assistant Chat
        print("\n[TEST 5] POST /api/ai/assistant/chat")
        res = client.post("/api/ai/assistant/chat", json={
            "query": "Which reports currently have the highest flood risk in the community?"
        })
        print(f"Status: {res.status_code}")
        chat_data = res.json()
        print(f"  Response: {chat_data.get('response')}")
        print(f"  Sources: {chat_data.get('sources')}")
        assert res.status_code == 200
        assert "response" in chat_data
        print("--> PASS: Assistant chat endpoint working.")

        # 6. Test Daily Summary
        print("\n[TEST 6] GET /api/ai/assistant/daily-summary")
        res = client.get("/api/ai/assistant/daily-summary")
        print(f"Status: {res.status_code}")
        sum_data = res.json()
        print(f"  Summary: {sum_data.get('summary')}")
        print(f"  Report Count: {sum_data.get('report_count')}")
        assert res.status_code == 200
        assert "summary" in sum_data
        print("--> PASS: Assistant daily summary endpoint working.")

        print("\n" + "="*70)
        print("ALL ENDPOINTS AND WEATHERAPI INTEGRATION VERIFIED SUCCESSFULLY!")
        print("="*70)

    finally:
        cleanup_mock_images()

if __name__ == "__main__":
    main()

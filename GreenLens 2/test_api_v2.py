import os
import time
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

# Mock filenames
MOCK_BLOCKED_IMG = "mock_blocked.jpg"
MOCK_CLEAN_IMG = "mock_clean.jpg"

def create_mock_images():
    """
    Creates two mock images (blocked & clean states) for testing.
    """
    # 1. Blocked drain mock
    img_blocked = Image.new("RGB", (300, 300), color=(110, 70, 40))
    draw = ImageDraw.Draw(img_blocked)
    draw.rectangle([60, 60, 240, 240], fill=(210, 40, 40))  # red block (trash)
    draw.ellipse([90, 90, 160, 160], fill=(40, 40, 210))   # blue block (cans)
    draw.text((10, 10), "MOCK BLOCKED DRAIN", fill=(255, 255, 255))
    img_blocked.save(MOCK_BLOCKED_IMG)

    # 2. Clean drain mock
    img_clean = Image.new("RGB", (300, 300), color=(40, 160, 40))
    draw = ImageDraw.Draw(img_clean)
    draw.rectangle([90, 90, 210, 210], fill=(110, 190, 110)) # clean concrete channel
    draw.text((10, 10), "MOCK CLEAN DRAIN", fill=(255, 255, 255))
    img_clean.save(MOCK_CLEAN_IMG)

def cleanup_mock_files():
    """
    Removes mock files and database generated during testing.
    """
    for file in [MOCK_BLOCKED_IMG, MOCK_CLEAN_IMG, "database.json"]:
        if os.path.exists(file):
            try:
                os.remove(file)
            except Exception:
                pass

def test_comprehensive_pipeline():
    # Teardown any old files first
    cleanup_mock_files()
    create_mock_images()
    
    # Import main FastAPI application from main.py
    from main import app
    client = TestClient(app)
    
    print("\n" + "="*70)
    print("STARTING GREENLENS AI COMPREHENSIVE PIPELINE VERIFICATION (V2)")
    print("="*70)
    
    # Test 1: Health Check
    print("\n[TEST 1] Checking API Health & fallbacks...")
    response = client.get("/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    
    # Test 2: Upload New Report (Ingestion flow)
    print("\n[TEST 2] Submitting report at Accra Mall (Latitude: 5.6152, Longitude: -0.1731)...")
    with open(MOCK_BLOCKED_IMG, "rb") as img_file:
        files = {"image": (MOCK_BLOCKED_IMG, img_file, "image/jpeg")}
        data = {
            "latitude": 5.6152,
            "longitude": -0.1731,
            "historical_flooding": "true",
            "description": "High density of plastic bottle blockages in the main gutter."
        }
        response = client.post("/api/ai/analyze-image", files=files, data=data)
        
    print(f"Status: {response.status_code}")
    report_data = response.json()
    assert response.status_code == 200
    
    report_id = report_data.get("report_id")
    print(f"  Report ID: {report_id}")
    print(f"  Quality Usable: {report_data.get('usable')} (Score: {report_data.get('quality_score')}/100)")
    print(f"  Waste Type: {report_data.get('waste_type')}, Density: {report_data.get('waste_density')}")
    print(f"  Drain Detected: {report_data.get('drain_detected')}, Structure: {report_data.get('drainage_structure')}")
    print(f"  Proximity Segment: {report_data.get('nearest_segment_name')} (Distance: {report_data.get('proximity_distance_meters')}m, Proximity: {report_data.get('proximity_level')})")
    print(f"  Flood Risk Score: {report_data.get('risk_score')}/100 ({report_data.get('risk_level')})")
    print(f"  Predictive Maintenance: {report_data.get('maintenance_message')}")
    print(f"  Dispatch: {report_data.get('dispatch_recommendation', {}).get('recommended_action')}")
    
    assert report_id is not None
    assert "risk_score" in report_data
    assert "proximity_level" in report_data
    assert "days_until_critical" in report_data
    
    # Test 3: Duplicate & Fraud Prevention
    print("\n[TEST 3] Testing duplicate check (same image & location)...")
    with open(MOCK_BLOCKED_IMG, "rb") as img_file:
        files = {"image": (MOCK_BLOCKED_IMG, img_file, "image/jpeg")}
        data = {"latitude": 5.6152, "longitude": -0.1731, "historical_flooding": "true"}
        response = client.post("/api/ai/analyze-image", files=files, data=data)
    dup_res = response.json()
    print(f"  Duplicate Status: {dup_res.get('status')}, ID: {dup_res.get('report_id')}")
    assert response.status_code == 200
    assert dup_res.get("status") == "DUPLICATE"
    
    # Test 4: Submit Second Report to build route optimization and hotspots
    print("\n[TEST 4] Submitting a second report at Kaneshie Gutter (Latitude: 5.5721, Longitude: -0.2292)...")
    with open(MOCK_BLOCKED_IMG, "rb") as img_file:
        files = {"image": (MOCK_BLOCKED_IMG, img_file, "image/jpeg")}
        data = {
            "latitude": 5.5721,
            "longitude": -0.2292,
            "historical_flooding": "false",
            "description": "Blockage near Kaneshie Market."
        }
        response = client.post("/api/ai/analyze-image", files=files, data=data)
    report_data_2 = response.json()
    report_id_2 = report_data_2.get("report_id")
    print(f"  Report 2 ID: {report_id_2}, Risk Score: {report_data_2.get('risk_score')}/100")
    assert response.status_code == 200
    
    # Test 5: Fetch Prioritized List
    print("\n[TEST 5] Getting prioritized incidents...")
    response = client.get("/api/ai/prioritized")
    prioritized = response.json()
    print(f"  Incidents count: {len(prioritized)}")
    for idx, inc in enumerate(prioritized):
        print(f"    {idx+1}. ID: {inc['report_id']} | Risk: {inc['risk_score']} ({inc['risk_level']}) | Dispatch: {inc['dispatch_recommendation']['team_assigned']}")
    assert response.status_code == 200
    assert len(prioritized) == 2
    
    # Test 6: Hotspot Clustering
    print("\n[TEST 6] Detecting waste hotspots...")
    response = client.get("/api/ai/hotspots")
    hotspots = response.json()
    print(f"  Detected hotspots: {hotspots}")
    assert response.status_code == 200
    
    # Test 7: Route Optimization & Environmental Impact
    print("\n[TEST 7] Calculating optimized collection routes for trucks...")
    response = client.post("/api/ai/route-optimization", json={
        "depot_latitude": 5.6037,
        "depot_longitude": -0.1870,
        "truck_capacity_kg": 2000.0
    })
    opt_res = response.json()
    print(f"  Route points count: {len(opt_res.get('route_points', []))}")
    print(f"  Total distance: {opt_res.get('total_distance_km')} km")
    print(f"  Total waste collected: {opt_res.get('total_waste_collected_kg')} kg")
    impact = opt_res.get("environmental_impact", {})
    print(f"  [IMPACT] Distance saved: {impact.get('distance_saved_km')} km")
    print(f"  [IMPACT] Fuel saved: {impact.get('fuel_saved_liters')} liters")
    print(f"  [IMPACT] CO2 avoided: {impact.get('co2_avoided_kg')} kg")
    assert response.status_code == 200
    assert "environmental_impact" in opt_res
    
    # Test 8: Municipal Assistant RAG Chat
    print("\n[TEST 8] Querying the Municipal Assistant RAG chat...")
    response = client.post("/api/ai/assistant/chat", json={"query": "Which communities have the highest flood risk?"})
    print(f"  User: Which communities have the highest flood risk?")
    print(f"  Assistant response: {response.json().get('response')}")
    assert response.status_code == 200
    
    # Test 9: Daily Summary Report
    print("\n[TEST 9] Generating Daily Summary report...")
    response = client.get("/api/ai/assistant/daily-summary")
    print(f"  Summary:\n{response.json().get('summary')}")
    assert response.status_code == 200
    
    # Test 10: Cleanup Verification
    print(f"\n[TEST 10] Submitting cleanup verification for {report_id}...")
    with open(MOCK_CLEAN_IMG, "rb") as img_file:
        files = {"after_image": (MOCK_CLEAN_IMG, img_file, "image/jpeg")}
        data = {"report_id": report_id}
        response = client.post("/api/ai/verify-cleanup", files=files, data=data)
    print(f"  Status: {response.status_code}")
    v_data = response.json()
    print(f"  Resolution Status: {v_data.get('status')}")
    v_res = v_data.get("verification_result", {})
    print(f"  Improvement: {v_res.get('estimated_improvement')}% | Verified PASS: {v_res.get('cleanup_verified')}")
    print(f"  Explanation: {v_res.get('explanation')}")
    assert response.status_code == 200
    
    print("\n" + "="*70)
    print("ALL COMPREHENSIVE PIPELINE VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("="*70 + "\n")
    
    # Cleanup
    cleanup_mock_files()

if __name__ == "__main__":
    test_comprehensive_pipeline()

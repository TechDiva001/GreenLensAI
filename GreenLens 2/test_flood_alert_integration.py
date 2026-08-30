import sys
import os
import unittest

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient
from main import app
from services.hydrology_service import evaluate_alert_severity

client = TestClient(app)

class TestFloodAlertIntegration(unittest.TestCase):
    def test_alert_check_endpoint_live(self):
        """Test GET /api/weather/alert-check returns a valid FloodAlertPayload"""
        response = client.get("/api/weather/alert-check?latitude=5.34352&longitude=-0.62566&blockage_percent=40.0")
        self.assertEqual(response.status_code, 200, f"Expected 200, got {response.status_code}: {response.text}")
        data = response.json()
        
        self.assertIn("alert_severity", data)
        self.assertIn("should_alert", data)
        self.assertIn("title", data)
        self.assertIn("message", data)
        self.assertIn("key_metrics", data)
        self.assertIn("safe_actions", data)
        self.assertIn("time_to_overflow_hours", data)
        
        metrics = data["key_metrics"]
        self.assertIn("rain_24h_mm", metrics)
        self.assertIn("surcharge_ratio", metrics)
        self.assertIn("overtopping_probability", metrics)
        self.assertIn("hydrograph_peak_mm_h", metrics)
        print(f"[TEST PASS] /api/weather/alert-check response: Severity={data['alert_severity']} (Alert={data['should_alert']})")

    def test_evaluate_alert_severity_critical(self):
        """Test CRITICAL alert threshold triggered when surcharge >= 1.0 or overtopping >= 90%"""
        hydrology = {
            "surcharge_ratio": 1.25,
            "overtopping_probability_percent": 95,
            "time_to_overflow_hours": 4.8
        }
        telemetry = {
            "rain_24h_mm": 45.0,
            "rain_probability_24h": 95,
            "hydrograph": [{"precipitation_mm": 6.5}]
        }
        result = evaluate_alert_severity(hydrology, telemetry)
        self.assertEqual(result["alert_severity"], "CRITICAL")
        self.assertTrue(result["should_alert"])
        self.assertIn("CRITICAL FLOOD ALERT", result["title"])
        self.assertGreater(len(result["safe_actions"]), 0)
        print(f"[TEST PASS] CRITICAL threshold verified: {result['title']}")

    def test_evaluate_alert_severity_high(self):
        """Test HIGH alert threshold triggered when overtopping >= 65%"""
        hydrology = {
            "surcharge_ratio": 0.85,
            "overtopping_probability_percent": 70,
            "time_to_overflow_hours": 9.2
        }
        telemetry = {
            "rain_24h_mm": 20.0,
            "rain_probability_24h": 75,
            "hydrograph": [{"precipitation_mm": 3.5}]
        }
        result = evaluate_alert_severity(hydrology, telemetry)
        self.assertEqual(result["alert_severity"], "HIGH")
        self.assertTrue(result["should_alert"])
        self.assertIn("HIGH FLOOD RISK ALERT", result["title"])
        print(f"[TEST PASS] HIGH threshold verified: {result['title']}")

    def test_evaluate_alert_severity_moderate(self):
        """Test MODERATE alert threshold triggered when 24h rain >= 15mm"""
        hydrology = {
            "surcharge_ratio": 0.55,
            "overtopping_probability_percent": 45,
            "time_to_overflow_hours": 18.0
        }
        telemetry = {
            "rain_24h_mm": 18.0,
            "rain_probability_24h": 60,
            "hydrograph": [{"precipitation_mm": 1.5}]
        }
        result = evaluate_alert_severity(hydrology, telemetry)
        self.assertEqual(result["alert_severity"], "MODERATE")
        self.assertTrue(result["should_alert"])
        self.assertIn("MODERATE FLOOD RISK", result["title"])
        print(f"[TEST PASS] MODERATE threshold verified: {result['title']}")

    def test_evaluate_alert_severity_none(self):
        """Test NONE alert when conditions are dry and clear"""
        hydrology = {
            "surcharge_ratio": 0.05,
            "overtopping_probability_percent": 5,
            "time_to_overflow_hours": 24.0
        }
        telemetry = {
            "rain_24h_mm": 0.0,
            "rain_probability_24h": 10,
            "hydrograph": [{"precipitation_mm": 0.0}]
        }
        result = evaluate_alert_severity(hydrology, telemetry)
        self.assertEqual(result["alert_severity"], "NONE")
        self.assertFalse(result["should_alert"])
        print(f"[TEST PASS] NONE threshold verified: {result['title']}")

    def test_flood_history_endpoints(self):
        """Test GET and POST /api/weather/flood-history"""
        # Test POST
        payload = {
            "catchment_name": "Winneba Catchment Basin",
            "latitude": 5.34352,
            "longitude": -0.62566,
            "severity": "CRITICAL",
            "compound_risk_score": 85.0,
            "surcharge_ratio": 1.22,
            "overtopping_probability_percent": 92,
            "time_to_overflow_hours": 4.9,
            "effective_capacity_m3s": 3.75,
            "nominal_capacity_m3s": 12.5,
            "storm_inflow_q_m3s": 4.575,
            "rainfall_24h_mm": 42.0,
            "rainfall_intensity_mm_h": 25.0,
            "rainfall_probability_24h": 95,
            "crowdsourced_blockage_percent": 70.0,
            "nearby_reports_count": 6,
            "verified_cleanups_count": 0,
            "primary_waste_type": "PLASTIC",
            "event_status": "PREDICTED",
            "mitigation_actions": ["Emergency drainage crew dispatched"]
        }
        post_res = client.post("/api/weather/flood-history", json=payload)
        self.assertEqual(post_res.status_code, 200)
        self.assertEqual(post_res.json()["status"], "success")

        # Test GET
        get_res = client.get("/api/weather/flood-history?catchment=Winneba%20Catchment")
        self.assertEqual(get_res.status_code, 200)
        history_list = get_res.json()
        self.assertIsInstance(history_list, list)
        self.assertGreater(len(history_list), 0)
        self.assertEqual(history_list[0]["severity"], "CRITICAL")
        print(f"[TEST PASS] /api/weather/flood-history verified: Retrieved {len(history_list)} archived records.")

if __name__ == "__main__":
    unittest.main()

import os
import sys
import json
import pytest
import numpy as np
import cv2
import httpx

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

def create_mock_img(filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    img = np.full((200, 200, 3), (100, 150, 80), dtype=np.uint8)
    cv2.imwrite(filepath, img)

@pytest.mark.anyio
async def test_analyze_image_stream():
    img_path = os.path.join("scratch", "stream_test.jpg")
    create_mock_img(img_path)
    abs_path = os.path.abspath(img_path)

    payload = {
        "image_url": abs_path,
        "user_id": "user_stream_test",
        "municipality_id": "1",
        "latitude": 5.6037,
        "longitude": -0.1870,
        "description": "Stream progress test",
        "historical_flooding": False
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream("POST", "/api/ai/analyze-image-stream", json=payload) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
            
            stages_received = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event_data = json.loads(line[6:])
                    stage = event_data.get("stage")
                    status = event_data.get("status")
                    stages_received.append((stage, status))
                    print(f"[SSE EVENT] Stage: {stage}, Status: {status}, Msg: {event_data.get('message')}")
                    if stage == "COMPLETE":
                        assert "result" in event_data
                        assert "report_id" in event_data["result"]

            stage_names = [s[0] for s in stages_received]
            print("Stages received:", stage_names)
            assert "IMAGE_DOWNLOAD" in stage_names
            assert "VISION_ANALYSIS" in stage_names
            assert "RISK_ASSESSMENT" in stage_names
            assert "COMPLETE" in stage_names

    if os.path.exists(img_path):
        os.remove(img_path)


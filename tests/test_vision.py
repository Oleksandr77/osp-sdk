import unittest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# Add operations root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboard.main import app, system

class TestVision(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        
        # Mock Agent Manager execution to avoid real LLM calls
        self.original_execute = system.agent_manager.execute_agent
        system.agent_manager.execute_agent = MagicMock(return_value={
            "result": {"message": "I see a test image."},
            "target_skill": None
        })

    def tearDown(self):
        system.agent_manager.execute_agent = self.original_execute

    def test_image_upload(self):
        # Base64 fake image
        fake_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        
        payload = {
            "session_id": "test_session",
            "message": "What is this?",
            "image": fake_image
        }
        
        response = self.client.post("/api/chat", data=payload)
        self.assertEqual(response.status_code, 200)
        
        # Verify Agent Manager received image
        system.agent_manager.execute_agent.assert_called_once()
        call_args = system.agent_manager.execute_agent.call_args
        self.assertEqual(call_args[1].get('image_data'), fake_image)
        
        print("Vision Endpoint Verified!")

if __name__ == '__main__':
    unittest.main()

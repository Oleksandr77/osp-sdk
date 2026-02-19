import unittest
from fastapi.testclient import TestClient
import sys
import os

# Add operations root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboard.main import app, system

class TestSettings(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_settings_page(self):
        response = self.client.get("/settings")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Agent Settings", response.text)

    def test_update_settings(self):
        new_prompt = "You are a specialized Medical Assistant."
        new_key = "test_key_123"
        
        data = {
            "system_prompt": new_prompt,
            "api_key": new_key
        }
        
        response = self.client.post("/api/settings", json=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "updated")
        
        # Verify changes in system
        # Check prompt update
        self.assertEqual(system.agent_manager.base_system_prompt, new_prompt)
        
        # Check env var update
        self.assertEqual(os.environ.get("GEMINI_API_KEY"), new_key)

        print("Settings Endpoint Verified!")

if __name__ == '__main__':
    unittest.main()

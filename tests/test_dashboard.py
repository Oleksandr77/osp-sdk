import unittest
from fastapi.testclient import TestClient
import sys
import os

# Add operations root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboard.main import app

class TestDashboard(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_home_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Antigravity Dashboard", response.text)
        self.assertIn("Active Session", response.text)

    def test_chat_endpoint(self):
        # We need a valid session ID. Fetch from home page or use mock?
        # The main.py initializes a global 'system' object.
        # Let's just try to hit the chat UI page first
        response = self.client.get("/chat")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Live Chat", response.text)

    # Note: Testing /api/chat might trigger actual Agent execution which calls LLM. 
    # We should mock AgentManager in main.py for a proper unit test, 
    # but for "Verification" that the app loads, this is enough.

if __name__ == '__main__':
    unittest.main()

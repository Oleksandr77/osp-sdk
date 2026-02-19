import unittest
import os
import sys
from unittest.mock import MagicMock, patch

# Add operations root
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from skills.foundation.summarize.scripts import tools as summarize_tools
from skills.integrations.telegram.scripts import tools as telegram_tools

class TestTelegramSkills(unittest.TestCase):
    def test_summarize_mock(self):
        """Test summarization with mocked Gemini"""
        with patch('skills.foundation.summarize.scripts.tools.model') as mock_model:
            mock_response = MagicMock()
            mock_response.text = "Mock Summary"
            mock_model.generate_content.return_value = mock_response
            
            result = summarize_tools.execute({"text": "Long text..."})
            self.assertEqual(result["summary"], "Mock Summary")
            self.assertEqual(result["status"], "success")

    def test_telegram_send_mock(self):
        """Test sending message with mocked requests"""
        with patch('skills.integrations.telegram.scripts.tools.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
            mock_post.return_value = mock_response
            
            # Mock Token
            with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "123:ABC"}):
                # Reload module to pick up env var if needed, or just patch the constant
                # Since constant is read at import time, we might need to patch it directly
                with patch('skills.integrations.telegram.scripts.tools.BOT_TOKEN', "123:ABC"):
                    result = telegram_tools.execute({"chat_id": 1, "text": "Hello"})
                    self.assertEqual(result["status"], "success")
                    self.assertEqual(result["message_id"], 123)

if __name__ == '__main__':
    unittest.main()

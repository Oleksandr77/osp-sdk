import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# Add operations root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Determine path to monitor_bot.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../integrations/telegram")))

# We need to mock imports BEFORE importing monitor_bot because it runs code at top level (e.g. logging config) and imports server
with patch.dict(sys.modules, {
    "telethon": MagicMock(),
    "telethon.TelegramClient": MagicMock(),
    "telethon.events": MagicMock(),
    "pandas": MagicMock(),
    "youtube_handler": MagicMock(),
    "server": MagicMock(), # Mock server module
    "web.web_handler": MagicMock(),
    "ai_core.vector_handler": MagicMock(),
    "ai_core.agent_manager": MagicMock(),
    "ai_core.skill_manager": MagicMock(),
}):
    import integrations.telegram.monitor_bot as bot_module

class TestMonitorBotLogic(unittest.IsolatedAsyncioTestCase):
    async def test_youtube_command_routing(self):
        """Test that /youtube command calls AgentManager"""
        bot = bot_module.AISmartBot()
        
        # Mock Agent Manager
        bot.agent_manager = MagicMock()
        bot.agent_session = MagicMock()
        bot.agent_session.session_id = "test-session"
        
        # Mock execution result
        bot.agent_manager.execute_agent.return_value = {
            "output": "Summary of the video..."
        }
        
        # Mock Event
        event = AsyncMock()
        event.raw_text = "/youtube https://youtu.be/123"
        event.edit = AsyncMock()
        
        # Call handler manually
        await bot.handle_command(event)
        
        # Verify Agent Manager was called
        bot.agent_manager.execute_agent.assert_called_once()
        args = bot.agent_manager.execute_agent.call_args
        self.assertEqual(args[0][0], "test-session")
        self.assertIn("Analyze this YouTube video", args[0][1])
        
        # Verify response sent
        event.edit.assert_called()
        # Initial "Analyzing..." message
        # Final response
        self.assertTrue(event.edit.call_count >= 2)

if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add operations root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Patch get_llm_provider BEFORE importing agent_manager
with patch('ai_core.llm.providers.get_llm_provider') as mock_provider:
    from ai_core.agent_manager import AgentManager
    from ai_core.skill_manager import SkillManager

class TestSwarmDelegation(unittest.TestCase):
    def setUp(self):
        self.mock_skill_manager = MagicMock(spec=SkillManager)
        self.mock_skill_manager.skills = {}
        # We don't need real vector db for this test
        self.agent_manager = AgentManager(self.mock_skill_manager)
        
        # Mock LLM for the sub-agent execution
        self.mock_llm = MagicMock()
        self.mock_llm.chat_completion.return_value = {"content": "I have researched the topic."}
        
    @patch('ai_core.llm.providers.get_llm_provider')
    def test_delegation(self, mock_get_llm):
        """Test that delegate_task creates a sub-session and runs it"""
        mock_get_llm.return_value = self.mock_llm
        
        # Main Session
        main_session = self.agent_manager.create_session({"name": "Main Agent"})
        
        # Delegate
        result = self.agent_manager.delegate_task(
            from_session_id=main_session.session_id,
            to_role="researcher",
            task_description="Find latest AI news"
        )
        
        # Verify result structure
        self.assertEqual(result["role"], "researcher")
        self.assertIn("delegated_to", result)
        self.assertNotEqual(result["delegated_to"], main_session.session_id)
        
        # Verify sub-session was created
        sub_session_id = result["delegated_to"]
        self.assertIn(sub_session_id, self.agent_manager.active_sessions)
        sub_session = self.agent_manager.active_sessions[sub_session_id]
        
        # Verify sub-session role
        self.assertEqual(sub_session.expertise["role"], "researcher")
        self.assertIn("expert Researcher", sub_session.expertise["system_prompt"])
        
        print("Swarm Delegation Verified!")

if __name__ == '__main__':
    unittest.main()

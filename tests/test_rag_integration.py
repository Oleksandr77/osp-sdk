import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add operations root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_core.agent_manager import AgentManager
from ai_core.skill_manager import SkillManager
from ai_core.memory.memory_store import MemoryScope

class TestRAGIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_skill_manager = MagicMock(spec=SkillManager)
        self.mock_skill_manager.skills = {}
        self.mock_vector_db = MagicMock()
        self.agent_manager = AgentManager(self.mock_skill_manager, vector_db=self.mock_vector_db)
        
        # Create a session
        self.session = self.agent_manager.create_session({"name": "Test Agent", "personality": {}})
        
        # Mock LLM provider to avoid actual API calls
        self.mock_llm = MagicMock()
        self.mock_llm.chat_completion.return_value = {"content": "I see the secret code."}
        
    @patch('ai_core.llm.providers.get_llm_provider')
    def test_rag_context_injection(self, mock_get_llm):
        """Test that vector search results are injected into system prompt"""
        mock_get_llm.return_value = self.mock_llm
        
        # Setup mock vector search result
        self.mock_vector_db.search.return_value = [
            {
                "text": "The secret code is Blue-7.",
                "metadata": {"title": "Secret Doc", "category": "Security"}
            }
        ]
        
        # Execute agent
        input_text = "What is the secret code?"
        result = self.agent_manager.execute_agent(self.session.session_id, input_text)
        
        # Verify vector search was called
        self.mock_vector_db.search.assert_called_once_with(input_text, n_results=3)
        
        # Verify LLM was called with injected context
        call_args = self.mock_llm.chat_completion.call_args
        messages = call_args[0][0] # first arg is messages list
        system_msg = messages[0]['content']
        
        self.assertIn("RELEVANT KNOWLEDGE FROM MEMORY:", system_msg)
        self.assertIn("The secret code is Blue-7", system_msg)
        self.assertIn("Security", system_msg)
        
        print("RAG Context Injection Verified!")

if __name__ == '__main__':
    unittest.main()

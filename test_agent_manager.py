import unittest
from ai_core.agent_manager import AgentManager
from ai_core.skill_manager import SkillManager
from ai_core.memory.memory_store import MemoryScope

class TestAgentManager(unittest.TestCase):
    def setUp(self):
        self.sm = SkillManager() # Mocks or real
        self.am = AgentManager(self.sm)
        
        self.test_profile = {
            "expertise_id": "test-researcher",
            "name": "Research Assistant",
            "version": "1.0.0",
            "persona": {
                "system_prompt": "You are a helpful research assistant.",
                "tone": "formal"
            },
            "skill_groups": ["group-search-analysis"]
        }

    def test_session_creation(self):
        session = self.am.create_session(self.test_profile)
        self.assertIsNotNone(session.session_id)
        
        # Check memory initialization
        prompt = session.memory.get("agent.persona.system_prompt", MemoryScope.SESSION)
        self.assertEqual(prompt, "You are a helpful research assistant.")

    def test_memory_operations(self):
        session = self.am.create_session(self.test_profile)
        session.memory.set("user_name", "Alice", MemoryScope.USER)
        
        val = session.memory.get("user_name", MemoryScope.USER)
        self.assertEqual(val, "Alice")
        
        # Ensure scope isolation
        val_session = session.memory.get("user_name", MemoryScope.SESSION)
        self.assertIsNone(val_session)

if __name__ == '__main__':
    unittest.main()

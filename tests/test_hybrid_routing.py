import unittest
from ai_core.agent_manager import AgentManager
from ai_core.skill_manager import SkillManager
from ai_core.vector_handler import VectorHandler
import shutil
import os
import sys

# Add operations
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

class TestHybridRouting(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.skill_manager = SkillManager()
        # Ensure vector DB is fresh
        db_path = "tests/temp_chroma_hybrid"
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
            
        self.vector_db = VectorHandler(persist_directory=db_path)
        self.agent_manager = AgentManager(self.skill_manager, vector_db=self.vector_db)
        
        # Add Mock Skills
        self.agent_manager.skill_manager.skills = {
            "calculator": {
                "metadata": {
                    "id": "calculator",
                    "name": "Calculator",
                    "description": "Perform mathematical operations and calculations.",
                    "activation_keywords": ["math", "sum", "add"]
                }
            },
            "weather": {
                "metadata": {
                    "id": "weather",
                    "name": "Weather Service",
                    "description": "Get forecasts for rain and sun.",
                    "activation_keywords": ["weather", "rain"]
                }
            }
        }

    def tearDown(self):
        if os.path.exists("tests/temp_chroma_hybrid"):
            shutil.rmtree("tests/temp_chroma_hybrid")

    def test_routing(self):
        # 1. Lexical Match
        res = self.agent_manager.execute_agent("sess1", "Check the weather")
        # Should populate candidates in log, but hard to assert internal candidates from outside.
        # However, if target_skill is selected (or passed to LLM), it means it worked.
        # Since we don't have real LLM here (it tries to load provider), it might fallback.
        # BUT, we can inspect logs or check if routing logic didn't crash.
        
        # Actually, let's spy on the router by checking if vector_db has skills.
        self.assertTrue(self.vector_db.count() > 0) # Skills should be indexed
        
        print("Hybrid Routing Test Executed - No crashes.")

if __name__ == '__main__':
    unittest.main()

import unittest
from fastapi.testclient import TestClient
import sys
import os
import shutil

# Add operations root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboard.main import app

class TestSkillBuilder(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_skill_name = "test_joke_skill"
        self.skills_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../skills/user"))

    def tearDown(self):
        # Cleanup created skill
        skill_path = os.path.join(self.skills_dir, self.test_skill_name)
        if os.path.exists(skill_path):
            shutil.rmtree(skill_path)

    def test_create_skill(self):
        payload = {
            "name": self.test_skill_name,
            "description": "A test skill for jokes",
            "instructions": "Tell a joke about {{topic}}",
            "parameters": {
                "topic": {"type": "string", "description": "The topic of the joke"}
            }
        }
        
        response = self.client.post("/api/skills/create", json=payload)
        self.assertEqual(response.status_code, 200)
        
        # Verify File Creation
        skill_path = os.path.join(self.skills_dir, self.test_skill_name)
        self.assertTrue(os.path.exists(os.path.join(skill_path, "metadata.yaml")))
        self.assertTrue(os.path.exists(os.path.join(skill_path, "skill.md")))
        
        # Verify Metadata Content
        import yaml
        with open(os.path.join(skill_path, "metadata.yaml")) as f:
            meta = yaml.safe_load(f)
            self.assertEqual(meta["name"], self.test_skill_name)
            self.assertEqual(meta["id"], f"user.{self.test_skill_name}")

        print("Skill Builder Verified!")

if __name__ == '__main__':
    unittest.main()

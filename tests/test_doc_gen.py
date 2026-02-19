import unittest
import os
import shutil
import sys
import yaml

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Import doc_gen script via exec since it's a script
DOC_GEN_SCRIPT = os.path.join(os.path.dirname(__file__), "../scripts/doc_gen.py")

class TestDocGen(unittest.TestCase):
    def setUp(self):
        self.test_skills_dir = "test_skills_doc"
        self.test_docs_dir = "test_docs_out"
        os.makedirs(self.test_skills_dir, exist_ok=True)
        os.makedirs(self.test_docs_dir, exist_ok=True)
        
        # Create a dummy skill
        skill_dir = os.path.join(self.test_skills_dir, "test-skill")
        os.makedirs(skill_dir, exist_ok=True)
        with open(os.path.join(skill_dir, "metadata.yaml"), "w") as f:
            yaml.dump({
                "id": "test.skill",
                "name": "Test Skill",
                "description": "A skill for testing doc generation.",
                "triggers": ["test it"]
            }, f)

    def tearDown(self):
        shutil.rmtree(self.test_skills_dir)
        shutil.rmtree(self.test_docs_dir)

    def test_generate_docs(self):
        """
        Verify that doc_gen.py produces a markdown file.
        """
        import subprocess
        
        result = subprocess.run(
            ["python3", DOC_GEN_SCRIPT, self.test_skills_dir, self.test_docs_dir],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Script Output: {result.stdout}")
            print(f"❌ Script Error: {result.stderr}")
            
        self.assertEqual(result.returncode, 0)
        
        expected_file = os.path.join(self.test_docs_dir, "test.skill.md")
        self.assertTrue(os.path.exists(expected_file))
        
        with open(expected_file, "r") as f:
            content = f.read()
            self.assertIn("# Test Skill", content)
            self.assertIn("**ID**: `test.skill`", content)
            self.assertIn("- `test it`", content)
            
        print("✅ Doc Generation Verified.")

if __name__ == '__main__':
    unittest.main()

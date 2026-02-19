import unittest
import os
import shutil
import sys
from io import StringIO
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Import asp_cli main function (assuming it's importable)
# If asp_cli is a package, we might need to adjust imports
from osp_cli import main

class TestCLIScaffold(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_scaffold_output"
        os.makedirs(self.test_dir, exist_ok=True)
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    @patch('sys.stdout', new_callable=StringIO)
    def test_create_skill(self, mock_stdout):
        """
        Test 'osp new skill test-skill'
        """
        test_args = ["osp", "new", "skill", "test-skill"]
        with patch.object(sys, 'argv', test_args):
            main.main()
        
        self.assertTrue(os.path.exists("test-skill/metadata.yaml"))
        self.assertTrue(os.path.exists("test-skill/scripts/tools.py"))
        self.assertIn("✅ Skill test-skill created successfully!", mock_stdout.getvalue())
        print("✅ CLI Skill Scaffolding Verified.")

    @patch('sys.stdout', new_callable=StringIO)
    def test_create_agent(self, mock_stdout):
        """
        Test 'osp new agent test-agent'
        """
        test_args = ["osp", "new", "agent", "test-agent"]
        with patch.object(sys, 'argv', test_args):
            main.main()
            
        self.assertTrue(os.path.exists("test-agent/agent.yaml"))
        self.assertTrue(os.path.exists("test-agent/main.py"))
        self.assertIn("✅ Agent test-agent created successfully!", mock_stdout.getvalue())
        print("✅ CLI Agent Scaffolding Verified.")

if __name__ == '__main__':
    unittest.main()

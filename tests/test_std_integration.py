import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from ai_core.skill_manager import SkillManager

class TestSkillManagerStdLib(unittest.TestCase):
    def test_std_lib_loading(self):
        """
        Verify that SkillManager loads osp-std skills automatically.
        """
        manager = SkillManager(skills_dir="../skills")
        
        # Check if std skills are present
        self.assertIn("osp.std.fs", manager.skill_registry)
        self.assertIn("osp.std.http", manager.skill_registry)
        self.assertIn("osp.std.system", manager.skill_registry)
        
        # Verify metadata
        fs_meta = manager.skill_registry["osp.std.fs"]
        self.assertEqual(fs_meta["name"], "FS")
        print("✅ Standard Library Skills Loaded Successfully.")

if __name__ == '__main__':
    unittest.main()

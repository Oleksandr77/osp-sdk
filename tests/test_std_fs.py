import unittest
import os
import shutil
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from osp_std import fs

class TestFileSystemSkill(unittest.TestCase):
    def setUp(self):
        # Create a test sandbox
        self.test_dir = os.path.abspath(os.path.join(os.getcwd(), "test_sandbox"))
        os.makedirs(self.test_dir, exist_ok=True)
        # Override SANDBOX_ROOT for testing
        fs.SANDBOX_ROOT = self.test_dir

    def tearDown(self):
        # Cleanup
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_write_read_file(self):
        """
        Verify basic write and read.
        """
        path = "hello.txt"
        content = "Hello OSP!"
        
        # Write
        result = fs.write_file(path, content)
        self.assertIn("Successfully wrote", result)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, path)))
        
        # Read
        read_content = fs.read_file(path)
        self.assertEqual(read_content, content)
        print("✅ Basic Write/Read Passed.")

    def test_jailbreak_attempt(self):
        """
        Verify that accessing files outside sandbox raises PermissionError.
        """
        # Try to access a sensitive file (Mac/Linux specific, but principle holds)
        sensitive_path = "../../../../../etc/passwd" 
        
        with self.assertRaises(PermissionError):
            fs.read_file(sensitive_path)
            
        print("✅ Jailbreak blocked (Relative Path).")

        # Try absolute path
        with self.assertRaises(PermissionError):
            fs.read_file("/etc/hosts")
            
        print("✅ Jailbreak blocked (Absolute Path).")

if __name__ == '__main__':
    unittest.main()

import unittest
import os
import sys

# Add operations root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def run_tests():
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n✅ ALL SYSTEMS GO! OSP Platform is ready.")
        sys.exit(0)
    else:
        print("\n❌ SYSTEM CHECKS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    print("Running OSP System Verification...")
    run_tests()

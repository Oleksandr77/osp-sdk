import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from osp_server.logic.metrics import OSP_REQUESTS_TOTAL, generate_latest

class TestMetrics(unittest.TestCase):
    def test_metrics_increment(self):
        """
        Verify that metric counters can be incremented (even if stubbed).
        """
        try:
            OSP_REQUESTS_TOTAL.labels(method="test", status="200").inc()
            print("✅ Incremented metric successfully.")
        except Exception as e:
            self.fail(f"Metric increment failed: {e}")

    def test_generate_latest(self):
        """
        Verify that generate_latest returns bytes.
        """
        output = generate_latest()
        self.assertIsInstance(output, bytes)
        print(f"✅ Metric Output: {output.decode('utf-8').strip()}")

if __name__ == '__main__':
    unittest.main()

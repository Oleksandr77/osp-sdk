import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import time
import logging

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from osp_server.logic.degradation import DegradationController, DegradationLevel

class TestAutoDegradation(unittest.TestCase):
    def setUp(self):
        self.controller = DegradationController()
        # Reset state
        self.controller.set_level(DegradationLevel.D0_NORMAL)
        # Stop any existing monitor
        self.controller.stop_monitoring()
        
    def tearDown(self):
        self.controller.stop_monitoring()

    @patch('asp_server.logic.degradation.psutil') 
    def test_high_cpu_trigger_d3(self, mock_psutil):
        """
        Verify that high CPU (>95%) triggers D3_CRITICAL.
        """
        logging.info("🧪 Testing High CPU -> D3 transition...")
        
        # Mock CPU to return 99%
        mock_psutil.cpu_percent.return_value = 99.0
        mock_psutil.virtual_memory.return_value.percent = 50.0 # Normal RAM
        
        # Start monitoring with fast interval
        self.controller.start_monitoring(interval=0.1)
        
        # Give it time to poll (need 2 ticks for escalation + overhead)
        time.sleep(0.5)
        
        self.assertEqual(self.controller.current_level, DegradationLevel.D3_CRITICAL)
        logging.info("   ✅ Correctly escalated to D3 on High CPU.")

    @patch('asp_server.logic.degradation.psutil') 
    def test_high_ram_trigger_d2(self, mock_psutil):
        """
        Verify that high RAM (>85%) triggers D2_MINIMAL.
        """
        logging.info("🧪 Testing High RAM -> D2 transition...")
        
        # Mock CPU normal, RAM high
        mock_psutil.cpu_percent.return_value = 20.0
        mock_psutil.virtual_memory.return_value.percent = 88.0
        
        self.controller.start_monitoring(interval=0.1)
        time.sleep(0.5)
        
        self.assertEqual(self.controller.current_level, DegradationLevel.D2_MINIMAL)
        logging.info("   ✅ Correctly escalated to D2 on High RAM.")

    @patch('asp_server.logic.degradation.psutil') 
    def test_recovery(self, mock_psutil):
        """
        Verify recovery from D3 -> D0 when load drops.
        Recovery requires RECOVERY_THRESHOLD (4) consecutive good ticks.
        psutil.cpu_percent(interval=1) blocks for 1s, so we need >= 5s.
        """
        logging.info("🧪 Testing Recovery D3 -> D0...")
        
        # Set to D3 manually
        self.controller.set_level(DegradationLevel.D3_CRITICAL)
        
        # Mock Normal stats
        mock_psutil.cpu_percent.return_value = 10.0
        mock_psutil.virtual_memory.return_value.percent = 30.0
        
        self.controller.start_monitoring(interval=0.1)
        
        # Recovery needs 4 good ticks. The _monitor_loop calls
        # psutil.cpu_percent(interval=1) which blocks; since psutil is mocked
        # it returns instantly. Then it sleeps max(0.1, interval-1) = 0.1s.
        # So ~4 * 0.1 = 0.4s min, but give extra margin.
        time.sleep(1.5)
        
        self.assertEqual(self.controller.current_level, DegradationLevel.D0_NORMAL)
        logging.info("   ✅ Correctly recovered to D0 when load normalized.")

    def test_manual_level_setting(self):
        """Verify manual set_level works for all levels."""
        for level in DegradationLevel:
            self.controller.set_level(level)
            self.assertEqual(self.controller.current_level, level)

    def test_d3_blocks_requests(self):
        """D3 should reject all incoming requests."""
        self.controller.set_level(DegradationLevel.D3_CRITICAL)
        self.assertFalse(self.controller.check_request_allowed())

    def test_d0_allows_requests(self):
        """D0 should allow all requests."""
        self.controller.set_level(DegradationLevel.D0_NORMAL)
        self.assertTrue(self.controller.check_request_allowed())

    def test_d0_allows_llm(self):
        """Only D0 allows LLM routing."""
        self.controller.set_level(DegradationLevel.D0_NORMAL)
        self.assertTrue(self.controller.should_use_llm())
        self.controller.set_level(DegradationLevel.D1_REDUCED_INTELLIGENCE)
        self.assertFalse(self.controller.should_use_llm())

    def test_d2_strict_routing(self):
        """D2+ enables strict routing only."""
        self.controller.set_level(DegradationLevel.D2_MINIMAL)
        self.assertTrue(self.controller.is_strict_routing_only())
        self.controller.set_level(DegradationLevel.D0_NORMAL)
        self.assertFalse(self.controller.is_strict_routing_only())

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main()


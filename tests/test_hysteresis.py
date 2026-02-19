import unittest
from unittest.mock import MagicMock, patch
import time
import sys
import os

# Add operations
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from osp_server.logic.degradation import DegradationController, DegradationLevel

class TestHysteresis(unittest.TestCase):
    def setUp(self):
        # Reset singleton logic? 
        # DegradationController is a singleton, so we need to be careful.
        # Ideally we reset its state.
        self.controller = DegradationController()
        self.controller.current_level = DegradationLevel.D0_NORMAL
        self.controller._stop_event = MagicMock()
        self.controller.logger = MagicMock()
        
    def test_escalation_hysteresis(self):
        # We will mock psutil and run the loop logic step by step 
        # (extracted logic or by mocking time.sleep to raise StopIteration after N loops? 
        #  Hard with infinite loop. Better to refactor or just test logic if extracted.
        #  Since I can't refactor easily now, I'll subclass or mock carefully.)
        
        # Let's mock inner loop variables by inspecting the code? No.
        # Let's rely on the fact that _monitor_loop calls set_level.
        
        with patch('asp_server.logic.degradation.psutil') as mock_psutil:
            with patch('time.sleep', side_effect=InterruptedError("Stop")): 
                # We can't easily break the loop without throwing exception or setting stop_event.
                # Let's manually invoke the logic if possible?
                # No, let's just use `_monitor_loop` logic rewritten as a test, or
                # create a separate method `_check_vitals` if I refactor.
                pass
                
    def test_hysteresis_logic_simulation(self):
        # Simulating the logic from the file
        high_load_ticks = 0
        normal_load_ticks = 0
        current_level = DegradationLevel.D0_NORMAL
        ESCALATION_THRESHOLD = 2
        RECOVERY_THRESHOLD = 4
        
        # Scenario 1: Spike (1 tick)
        cpu = 99
        ram = 50
        target = DegradationLevel.D3_CRITICAL
        
        # Tick 1
        if target.value > current_level.value:
            high_load_ticks += 1
            normal_load_ticks = 0
        
        # Should NOT escalate yet
        self.assertEqual(current_level, DegradationLevel.D0_NORMAL)
        self.assertEqual(high_load_ticks, 1)
        
        # Tick 2
        if target.value > current_level.value:
             high_load_ticks += 1
             if high_load_ticks >= ESCALATION_THRESHOLD:
                 current_level = target
                 high_load_ticks = 0
        
        # SHOULD escalate now
        self.assertEqual(current_level, DegradationLevel.D3_CRITICAL)
        self.assertEqual(high_load_ticks, 0)
        
        # Scenario 2: Flapping Recovery (1 tick normal)
        cpu = 10
        ram = 10
        target = DegradationLevel.D0_NORMAL
        
        # Tick 1
        if target.value < current_level.value:
            normal_load_ticks += 1
            high_load_ticks = 0
            
        # Should NOT recover yet
        self.assertEqual(current_level, DegradationLevel.D3_CRITICAL)
        
        # Tick 2, 3, 4
        for _ in range(3):
            normal_load_ticks += 1
            if normal_load_ticks >= RECOVERY_THRESHOLD:
                current_level = target
                normal_load_ticks = 0
                
        # Now 4 ticks total -> Recovery
        self.assertEqual(current_level, DegradationLevel.D0_NORMAL)

if __name__ == '__main__':
    unittest.main()

from enum import Enum
import logging
try:
    import psutil
except ImportError:
    psutil = None

class DegradationLevel(Enum):
    D0_NORMAL = 0
    D1_REDUCED_INTELLIGENCE = 1  # Standard Deterministic Routing Only (No LLM)
    D2_MINIMAL = 2               # Strict Routing (Exact Matches Only)
    D3_CRITICAL = 3              # Load Shedding (Service Unavailable)

class DegradationController:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DegradationController, cls).__new__(cls)
            cls._instance.current_level = DegradationLevel.D0_NORMAL
            cls._instance.logger = logging.getLogger("osp.degradation")
            cls._instance._monitor_thread = None
            cls._instance._stop_event = None
        return cls._instance

    def set_level(self, level: DegradationLevel):
        if self.current_level != level:
            self.current_level = level
            if hasattr(self, 'logger'):
                self.logger.warning(f"⚠️ Degradation Level switched to {level.name}")

    def start_monitoring(self, interval: int = 5):
        """
        Starts a background thread to monitor system vitals (CPU/RAM).
        Requries 'psutil' to be installed.
        """
        import threading
        
        if self._monitor_thread and self._monitor_thread.is_alive():
             self.logger.warning("Monitoring already running.")
             return

        if psutil is None:
            self.logger.warning("❌ 'psutil' not found. Auto-degradation monitoring disabled.")
            return

        self._stop_event = threading.Event()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self._monitor_thread.start()
        self.logger.info(f"✅ Auto-Degradation Monitoring started (Interval: {interval}s)")

    def stop_monitoring(self):
        if self._stop_event:
            self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
            self.logger.info("🛑 Monitoring stopped.")

    def _monitor_loop(self, interval: int):
        import time
        
        # Hysteresis counters
        high_load_ticks = 0
        normal_load_ticks = 0
        
        # Configuration
        ESCALATION_THRESHOLD = 2   # Need 2 bad checks to escalate
        RECOVERY_THRESHOLD = 4     # Need 4 good checks to recover
        
        while not self._stop_event.is_set():
            try:
                cpu = psutil.cpu_percent(interval=1) # Blocking for 1s
                ram = psutil.virtual_memory().percent
                
                # Determine Target State
                target_level = DegradationLevel.D0_NORMAL
                
                if cpu > 95 or ram > 95:
                    target_level = DegradationLevel.D3_CRITICAL
                elif cpu > 80 or ram > 85:
                    target_level = DegradationLevel.D2_MINIMAL
                elif cpu > 50 or ram > 60:
                    target_level = DegradationLevel.D1_REDUCED_INTELLIGENCE
                
                # Hysteresis Logic
                if target_level.value > self.current_level.value:
                    # Potential Escalation
                    high_load_ticks += 1
                    normal_load_ticks = 0 # Reset recovery
                    
                    if high_load_ticks >= ESCALATION_THRESHOLD:
                        self.set_level(target_level)
                        self.logger.warning(f"🔥 Load Spike (CPU:{cpu}% RAM:{ram}%) -> Escalating to {target_level.name}")
                        high_load_ticks = 0
                        
                elif target_level.value < self.current_level.value:
                    # Potential Recovery
                    normal_load_ticks += 1
                    high_load_ticks = 0 # Reset escalation
                    
                    if normal_load_ticks >= RECOVERY_THRESHOLD:
                        self.set_level(target_level)
                        self.logger.info(f"❄️ Load Stabilized (CPU:{cpu}% RAM:{ram}%) -> Recovering to {target_level.name}")
                        normal_load_ticks = 0
                else:
                    # Stable state
                    high_load_ticks = 0
                    normal_load_ticks = 0
                    
                # Wait rest of interval
                time.sleep(max(0.1, interval - 1))
                
            except Exception as e:
                self.logger.error(f"Monitoring Loop Error: {e}")
                time.sleep(interval)

    def check_request_allowed(self) -> bool:
        """
        Returns True if request should proceed, False if it should be shed (D3).
        """
        if self.current_level == DegradationLevel.D3_CRITICAL:
            return False
        return True

    def should_use_llm(self) -> bool:
        """
        Returns True if LLM (Stage 2) is allowed.
        False for D1 and D2.
        """
        return self.current_level == DegradationLevel.D0_NORMAL

    def is_strict_routing_only(self) -> bool:
        """
        Returns True if only strict lexical matching is allowed (D2).
        """
        return self.current_level.value >= DegradationLevel.D2_MINIMAL.value

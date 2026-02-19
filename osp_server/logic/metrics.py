import logging
import time
from functools import wraps

logger = logging.getLogger("osp.metrics")

try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("❌ 'prometheus_client' not found. Metrics will be disabled/stubbed.")

    # Stub classes to prevent crashes
    class StubMetric:
        def __init__(self, *args, **kwargs): pass
        def inc(self, amount=1): pass
        def set(self, value): pass
        def observe(self, value): pass
        def labels(self, *args, **kwargs): return self
    
    Counter = StubMetric
    Gauge = StubMetric
    Histogram = StubMetric
    
    def generate_latest():
        return b"# Prometheus client not installed.\n"
    
    CONTENT_TYPE_LATEST = "text/plain"

# Define Metrics
OSP_REQUESTS_TOTAL = Counter(
    "osp_requests_total", 
    "Total number of OSP requests", 
    ["method", "status"]
)

OSP_AGENT_EXECUTION_DURATION = Histogram(
    "osp_agent_execution_duration_seconds",
    "Time spent executing agent skills",
    ["skill_id"]
)

OSP_DEGRADATION_LEVEL = Gauge(
    "osp_degradation_level",
    "Current system degradation level (0-3)"
)

OSP_LLM_TOKENS_USED = Counter(
    "osp_llm_tokens_used",
    "Estimated tokens used by LLM router",
    ["model"]
)

def track_time(metric, **labels):
    """Decorator to track execution time in a Histogram."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                metric.labels(**labels).observe(duration)
        return wrapper
    return decorator

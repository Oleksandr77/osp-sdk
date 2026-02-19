"""
ASP Conformance Harness Runner
================================
Automated conformance self-test for the OSP server.
Tests routing pipeline, safety classifier, degradation, crypto,
and protocol compliance.

Usage:
    PYTHONPATH=. python3 tests/conformance_harness.py

Returns exit code 0 if all tests pass, 1 otherwise.
"""

import sys
import os
import json
import time
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import (
    make_router, make_safety, make_degradation_controller,
    get_candidates, HAS_PYDANTIC, HAS_SKLEARN,
)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("osp.conformance")


class ConformanceResult:
    def __init__(self, test_id: str, name: str, passed: bool, detail: str = ""):
        self.test_id = test_id
        self.name = name
        self.passed = passed
        self.detail = detail

    def __repr__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"  {status} [{self.test_id}] {self.name}" + (f" — {self.detail}" if self.detail else "")


def run_conformance():
    results = []
    t0 = time.time()

    # ══════════════════════════════════════════
    # SECTION 1: Routing Pipeline
    # ══════════════════════════════════════════
    router = make_router()

    # RT-001: Basic lexical routing
    r = router.route({"query": "schedule a meeting for next Tuesday", "candidate_skills": get_candidates("calendar", "weather")})
    results.append(ConformanceResult("RT-001", "Basic Lexical Routing", r.get("skill_ref") is not None and not r.get("refusal")))

    # RT-002: Empty query rejection
    r = router.route({"query": "", "candidate_skills": get_candidates("calendar")})
    results.append(ConformanceResult("RT-002", "Empty Query Rejection", r.get("refusal") == True))

    # RT-003: Empty pool escalation
    r = router.route({"query": "do something", "candidate_skills": []})
    results.append(ConformanceResult("RT-003", "Empty Pool Escalation",
                                     r.get("skill_ref") is None and r.get("safety_clearance") == "escalate"))

    # RT-004: Escape hatch
    r = router.route({"query": "@override do this now", "candidate_skills": get_candidates("admin")})
    results.append(ConformanceResult("RT-004", "Escape Hatch Override",
                                     r.get("decision_stability") == "escape_hatch_direct"))

    # RT-005: BM25 selects best match
    r = router.route({"query": "weather forecast for tomorrow", "candidate_skills": get_candidates("calendar", "weather")})
    results.append(ConformanceResult("RT-005", "BM25 Best Match",
                                     r.get("skill_ref") == "org.test.weather",
                                     f"got: {r.get('skill_ref')}"))

    # RT-006: Skip semantic condition
    r = router.route({"query": "quarterly earnings", "candidate_skills": get_candidates("finance"),
                       "routing_conditions": {"skip_semantic": True}})
    trace_codes = [t["code"] for t in r.get("trace_events", [])]
    results.append(ConformanceResult("RT-006", "Skip Semantic Condition",
                                     "STAGE2_SKIPPED" in trace_codes))

    # RT-007: Trace events always present
    r = router.route({"query": "test", "candidate_skills": get_candidates("calendar")})
    results.append(ConformanceResult("RT-007", "Trace Events Present",
                                     len(r.get("trace_events", [])) > 0))

    # RT-008: IEEE 754 epsilon
    from osp_server.logic.routing import _fp64_equal
    results.append(ConformanceResult("RT-008", "IEEE 754 Epsilon",
                                     _fp64_equal(1.0, 1.0 + 1e-7) and not _fp64_equal(1.0, 1.1)))

    # ══════════════════════════════════════════
    # SECTION 2: Safety Pipeline
    # ══════════════════════════════════════════
    safety = make_safety()

    # SAF-001: SQL injection blocked
    r = safety.check_safety("SELECT * FROM users UNION SELECT password FROM admin", {})
    results.append(ConformanceResult("SAF-001", "SQL Injection Blocked",
                                     r is not None and r.get("reason_code") == "PREFILTER_SQL_INJECTION"))

    # SAF-002: Command injection blocked
    r = safety.check_safety("execute: rm -rf /important", {})
    results.append(ConformanceResult("SAF-002", "Command Injection Blocked",
                                     r is not None and r.get("reason_code") == "PREFILTER_COMMAND_INJECTION"))

    # SAF-003: Safe query passes
    r = safety.check_safety("What time is the team meeting?", {})
    results.append(ConformanceResult("SAF-003", "Safe Query Passes", r is None))

    # SAF-004: Violence detected
    r = safety.check_safety("how to build an improvised explosive device at home", {})
    results.append(ConformanceResult("SAF-004", "Violence Detection",
                                     r is not None and r.get("safe") == False))

    # SAF-005: Fail-closed behavior
    from osp_server.logic.safety import _kl_divergence
    kl = _kl_divergence([0.25, 0.25, 0.25, 0.25], [0.25, 0.25, 0.25, 0.25])
    results.append(ConformanceResult("SAF-005", "KL-Divergence Zero for Identical",
                                     abs(kl) < 1e-5))

    # ══════════════════════════════════════════
    # SECTION 3: Degradation
    # ══════════════════════════════════════════
    from osp_server.logic.degradation import DegradationLevel

    ctrl = make_degradation_controller()

    # DEG-001: D0 allows LLM
    results.append(ConformanceResult("DEG-001", "D0 Allows LLM", ctrl.should_use_llm()))

    # DEG-002: D1 blocks LLM
    ctrl.set_level(DegradationLevel.D1_REDUCED_INTELLIGENCE)
    results.append(ConformanceResult("DEG-002", "D1 Blocks LLM", not ctrl.should_use_llm()))

    # DEG-003: D3 sheds load
    ctrl.set_level(DegradationLevel.D3_CRITICAL)
    results.append(ConformanceResult("DEG-003", "D3 Sheds Load", not ctrl.check_request_allowed()))

    # DEG-004: D2 strict routing only
    ctrl.set_level(DegradationLevel.D2_MINIMAL)
    results.append(ConformanceResult("DEG-004", "D2 Strict Routing Only", ctrl.is_strict_routing_only()))

    # Reset
    ctrl.set_level(DegradationLevel.D0_NORMAL)

    # ══════════════════════════════════════════
    # SECTION 4: Models (if pydantic available)
    # ══════════════════════════════════════════
    if HAS_PYDANTIC:
        from osp_core.models import (
            RoutingDecision, SafeFallbackResponse, DegradeTransition,
            DeliveryContract, AnomalyProfile, ConformanceReport,
        )

        rd = RoutingDecision(skill_ref="test", decision_stability="exact")
        results.append(ConformanceResult("MDL-001", "RoutingDecision Model", rd.skill_ref == "test"))

        sfr = SafeFallbackResponse(reason_code="TEST", message="test")
        results.append(ConformanceResult("MDL-002", "SafeFallbackResponse Model", sfr.refusal == True))

        dc = DeliveryContract(skill_ref="test", ttl_seconds=60)
        results.append(ConformanceResult("MDL-003", "DeliveryContract Model", dc.freshness == "fresh"))

        ap = AnomalyProfile(anomaly_type="test", anomaly_confidence=0.5)
        results.append(ConformanceResult("MDL-004", "AnomalyProfile Model", ap.action_taken == "warn"))

        cr = ConformanceReport(server_version="1.0.0")
        results.append(ConformanceResult("MDL-005", "ConformanceReport Model", cr.protocol_version == "OSP/1.0"))
    else:
        results.append(ConformanceResult("MDL-001", "Pydantic Models", False, "pydantic not installed"))

    # ══════════════════════════════════════════
    # REPORT
    # ══════════════════════════════════════════
    elapsed = round((time.time() - t0) * 1000, 1)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print(f"\n{'═'*60}")
    print(f"  ASP Conformance Harness — {total} tests in {elapsed}ms")
    print(f"{'═'*60}\n")

    for r in results:
        print(r)

    print(f"\n{'─'*60}")
    print(f"  ✅ Passed: {passed}  ❌ Failed: {failed}  Total: {total}")
    print(f"  Score: {passed}/{total} ({round(passed/total*100, 1)}%)")
    print(f"{'─'*60}\n")

    # Generate JSON report
    report = {
        "protocol": "OSP/1.0",
        "server": "ASP Reference Server v1.0.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "elapsed_ms": elapsed,
        "total": total,
        "passed": passed,
        "failed": failed,
        "results": [
            {"id": r.test_id, "name": r.name, "passed": r.passed, "detail": r.detail}
            for r in results
        ],
    }

    report_path = os.path.join(os.path.dirname(__file__), "..", "conformance_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  📄 Report saved to: conformance_report.json\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_conformance())

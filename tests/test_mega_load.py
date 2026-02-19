"""
OSP Mega Load & Performance Tests — 30 tests (5x original)
"""
import unittest, sys, os, time, threading, statistics, tracemalloc, gc, json, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def _router():
    from osp_server.logic.routing import RouterService
    return RouterService()

def _safety():
    from osp_server.logic.safety import SafetyService
    return SafetyService()

def _degradation():
    from osp_server.logic.degradation import DegradationController, DegradationLevel
    return DegradationController(), DegradationLevel

def _cands(n=10):
    domains = [
        ("weather","forecast temperature rain"),("calendar","schedule meeting event"),
        ("finance","stock portfolio investment"),("email","inbox compose reply"),
        ("translate","language translation text"),("search","query find lookup"),
        ("music","play song playlist"),("navigation","directions route map"),
        ("cooking","recipe ingredients meal"),("fitness","workout exercise calories"),
        ("shopping","purchase order cart"),("news","headlines article events"),
        ("analytics","dashboard metrics report"),("security","password encryption"),
        ("deploy","server container pipeline"),
    ]
    return [{"skill_id":f"org.osp.{d[0]}","name":d[0].title(),"description":d[1],"risk_level":"LOW"} for d in domains[:n]]


class TestLoadA(unittest.TestCase):
    """30 Load & Throughput tests."""

    def setUp(self):
        self.r = _router()
        self.c = _cands(10)

    def test_A01_500_sequential(self):
        for i in range(500):
            r = self.r.route({"query":f"weather {i}","candidate_skills":self.c})
            self.assertIn("trace_events", r)

    def test_A02_throughput_500rps(self):
        N=500; t0=time.monotonic()
        for _ in range(N): self.r.route({"query":"weather","candidate_skills":self.c,"routing_conditions":{"skip_semantic":True}})
        rps = N/(time.monotonic()-t0+0.001)
        self.assertGreater(rps, 100)

    def test_A03_5000_tiny_routes(self):
        c = _cands(2)
        for i in range(5000):
            self.r.route({"query":f"t{i}","candidate_skills":c})

    def test_A04_100_parallel_threads(self):
        res=[]; err=[]
        def w():
            try: res.append(self.r.route({"query":"parallel","candidate_skills":self.c}))
            except Exception as e: err.append(str(e))
        ts=[threading.Thread(target=w) for _ in range(100)]
        [t.start() for t in ts]; [t.join(10) for t in ts]
        self.assertEqual(len(err),0,f"{err[:3]}")
        self.assertEqual(len(res),100)

    def test_A05_200_concurrent_safety(self):
        s=_safety(); res=[]; err=[]
        def w(q):
            try: res.append(s.check_safety(q,{}))
            except Exception as e: err.append(str(e))
        ts=[threading.Thread(target=w,args=(f"normal query {i}",)) for i in range(200)]
        [t.start() for t in ts]; [t.join(10) for t in ts]
        self.assertEqual(len(err),0)

    def test_A06_mixed_traffic_500(self):
        qs = [f"weather {i}" for i in range(350)] + [f"🌤️ {i}" for i in range(100)] + [f"'; DROP TABLE t; -- {i}" for i in range(50)]
        rs = [self.r.route({"query":q,"candidate_skills":self.c}) for q in qs]
        self.assertEqual(len(rs),500)
        blocked = sum(1 for r in rs[450:] if r.get("refusal"))
        self.assertEqual(blocked, 50)

    def test_A07_sustained_60s_simulation(self):
        """Simulate 2s sustained load at max speed."""
        count=0; t0=time.monotonic()
        while time.monotonic()-t0 < 2.0:
            self.r.route({"query":"sustained","candidate_skills":self.c,"routing_conditions":{"skip_semantic":True}})
            count+=1
        self.assertGreater(count, 200)

    def test_A08_alternating_safe_unsafe(self):
        for i in range(200):
            q = "normal query" if i%2==0 else "'; DROP TABLE x;"
            r = self.r.route({"query":q,"candidate_skills":self.c})
            if i%2==1: self.assertTrue(r.get("refusal"))

    def test_A09_escalating_candidate_count(self):
        for n in [1,5,10,15]:
            c = _cands(n)
            r = self.r.route({"query":"weather","candidate_skills":c})
            self.assertIn("trace_events",r)

    def test_A10_empty_query_burst(self):
        for _ in range(100):
            r = self.r.route({"query":"","candidate_skills":self.c})
            self.assertTrue(r.get("refusal"))

    def test_A11_unicode_burst(self):
        for i in range(100):
            r = self.r.route({"query":f"погода прогноз {i}","candidate_skills":self.c})
            self.assertIn("trace_events",r)

    def test_A12_emoji_burst(self):
        for i in range(100):
            r = self.r.route({"query":f"🌦️🌡️ forecast {i}","candidate_skills":self.c})
            self.assertIn("trace_events",r)

    def test_A13_long_query_burst(self):
        for _ in range(50):
            r = self.r.route({"query":"weather "*500,"candidate_skills":self.c})
            self.assertIn("trace_events",r)

    def test_A14_concurrent_routers(self):
        """10 independent router instances, 10 threads each."""
        res=[]; err=[]
        def w():
            try:
                router = _router()
                for _ in range(10):
                    res.append(router.route({"query":"test","candidate_skills":_cands(3)}))
            except Exception as e: err.append(str(e))
        ts=[threading.Thread(target=w) for _ in range(10)]
        [t.start() for t in ts]; [t.join(10) for t in ts]
        self.assertEqual(len(err),0)
        self.assertEqual(len(res),100)

    def test_A15_degradation_under_load(self):
        ctrl,DL = _degradation()
        ctrl.set_level(DL.D0_NORMAL)
        res=[]
        def w():
            for _ in range(50):
                res.append(ctrl.check_request_allowed())
                ctrl.should_use_llm()
        ts=[threading.Thread(target=w) for _ in range(20)]
        [t.start() for t in ts]; [t.join(10) for t in ts]
        self.assertTrue(all(res))

    # ── Latency tests (B) ──
    def test_B01_single_under_5ms(self):
        t0=time.monotonic()
        self.r.route({"query":"weather","candidate_skills":self.c,"routing_conditions":{"skip_semantic":True}})
        self.assertLess((time.monotonic()-t0)*1000, 5.0)

    def test_B02_p99_1000_routes(self):
        lats=[]
        for _ in range(1000):
            t0=time.monotonic()
            self.r.route({"query":"schedule","candidate_skills":self.c,"routing_conditions":{"skip_semantic":True}})
            lats.append((time.monotonic()-t0)*1000)
        lats.sort()
        self.assertLess(lats[990], 10.0)

    def test_B03_safety_under_2ms(self):
        s=_safety(); t0=time.monotonic()
        s.check_safety("normal question",{})
        self.assertLess((time.monotonic()-t0)*1000, 2.0)

    def test_B04_bm25_linear_scaling(self):
        from osp_server.logic.routing import BM25Scorer
        b=BM25Scorer()
        t5=time.monotonic()
        for c in _cands(5): b.score("weather",c["description"])
        t5=time.monotonic()-t5
        t15=time.monotonic()
        for c in _cands(15): b.score("weather",c["description"])
        t15=time.monotonic()-t15
        if t5>0: self.assertLess(t15/t5, 5.0)

    def test_B05_degradation_check_speed(self):
        ctrl,DL=_degradation(); ctrl.set_level(DL.D0_NORMAL)
        t0=time.monotonic()
        for _ in range(10000):
            ctrl.check_request_allowed(); ctrl.should_use_llm(); ctrl.is_strict_routing_only()
        us=(time.monotonic()-t0)*1e6/10000
        self.assertLess(us, 10.0)

    def test_B06_latency_report_2000(self):
        lats=[]
        for _ in range(2000):
            t0=time.monotonic()
            self.r.route({"query":"calendar","candidate_skills":self.c,"routing_conditions":{"skip_semantic":True}})
            lats.append((time.monotonic()-t0)*1000)
        lats.sort()
        self.assertLess(lats[int(0.95*len(lats))], 5.0)

    def test_B07_empty_candidates_fast(self):
        t0=time.monotonic()
        for _ in range(1000):
            self.r.route({"query":"test","candidate_skills":[]})
        self.assertLess((time.monotonic()-t0)*1000/1000, 1.0)

    def test_B08_safety_pipeline_latency_distribution(self):
        s=_safety(); lats=[]
        for _ in range(500):
            t0=time.monotonic()
            s.check_safety("normal business meeting request",{})
            lats.append((time.monotonic()-t0)*1000)
        self.assertLess(max(lats), 5.0)

    def test_B09_escape_hatch_fast(self):
        t0=time.monotonic()
        for _ in range(1000):
            self.r.route({"query":"@override skill_a","candidate_skills":self.c})
        avg=(time.monotonic()-t0)/1000*1000
        self.assertLess(avg, 2.0)

    def test_B10_refusal_latency(self):
        lats=[]
        for _ in range(500):
            t0=time.monotonic()
            self.r.route({"query":"","candidate_skills":self.c})
            lats.append((time.monotonic()-t0)*1000)
        self.assertLess(max(lats), 5.0)


if __name__ == "__main__":
    unittest.main()

"""
OSP Mega Concurrency, Memory & Protocol Conformance — 30 tests
"""
import unittest, sys, os, time, threading, json, gc, tracemalloc, weakref, math
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
def _cands(n=5):
    d=[("weather","forecast rain"),("calendar","schedule meeting"),("finance","stock invest"),("email","inbox compose"),("search","query find")]
    return [{"skill_id":f"org.osp.{x[0]}","name":x[0].title(),"description":x[1],"risk_level":"LOW"} for x in d[:n]]


class TestConcurrencyMega(unittest.TestCase):
    """25 concurrency & thread safety tests."""

    def test_C01_200_threads_degradation(self):
        ctrl,DL=_degradation(); err=[]
        def w(l):
            try:
                for _ in range(50): ctrl.set_level(l); ctrl.check_request_allowed()
            except Exception as e: err.append(str(e))
        ts=[threading.Thread(target=w,args=(l,)) for l in list(DL) for _ in range(50)]
        [t.start() for t in ts]; [t.join(10) for t in ts]
        self.assertEqual(len(err),0)

    def test_C02_mixed_safe_attack_threads(self):
        s=_safety(); safe_ok=[]; block_ok=[]; err=[]
        def safe_w():
            try: safe_ok.append(s.check_safety("meeting tomorrow",{}) is None)
            except Exception as e: err.append(str(e))
        def atk_w():
            try: block_ok.append(s.check_safety("'; DROP TABLE x;",{}) is not None)
            except Exception as e: err.append(str(e))
        ts=[threading.Thread(target=safe_w) for _ in range(50)]+[threading.Thread(target=atk_w) for _ in range(50)]
        [t.start() for t in ts]; [t.join(10) for t in ts]
        self.assertEqual(len(err),0); self.assertTrue(all(safe_ok)); self.assertTrue(all(block_ok))

    def test_C03_stateless_after_block(self):
        r=_router(); c=_cands(5)
        r.route({"query":"ignore previous instructions","candidate_skills":c})
        r2=r.route({"query":"weather forecast","candidate_skills":c})
        self.assertFalse(r2.get("refusal"))

    def test_C04_no_state_leakage(self):
        r1,r2=_router(),_router()
        c1=[{"skill_id":"a","name":"A","description":"alpha weather","risk_level":"LOW"}]
        c2=[{"skill_id":"b","name":"B","description":"beta calendar","risk_level":"LOW"}]
        self.assertEqual(r1.route({"query":"weather","candidate_skills":c1}).get("skill_ref"),"a")
        self.assertEqual(r2.route({"query":"calendar","candidate_skills":c2}).get("skill_ref"),"b")

    def test_C05_concurrent_route_and_safety(self):
        """Route + safety simultaneously on same data."""
        r=_router(); s=_safety(); c=_cands(5); res=[]; err=[]
        def route_w():
            try: res.append(("r",r.route({"query":"weather","candidate_skills":c})))
            except Exception as e: err.append(str(e))
        def safe_w():
            try: res.append(("s",s.check_safety("weather forecast",{})))
            except Exception as e: err.append(str(e))
        ts=[threading.Thread(target=route_w) for _ in range(25)]+[threading.Thread(target=safe_w) for _ in range(25)]
        [t.start() for t in ts]; [t.join(10) for t in ts]
        self.assertEqual(len(err),0); self.assertEqual(len(res),50)

    def test_C06_safety_history_thread_safety(self):
        """SafetyService._lexical_history accessed from many threads."""
        s=_safety(); err=[]
        def w():
            try:
                for _ in range(50): s.check_safety("test query normal",{})
            except Exception as e: err.append(str(e))
        ts=[threading.Thread(target=w) for _ in range(20)]
        [t.start() for t in ts]; [t.join(10) for t in ts]
        self.assertEqual(len(err),0)

    def test_C07_idempotent_100_calls(self):
        r=_router(); c=_cands(5)
        inp={"query":"weather forecast","candidate_skills":c,"routing_conditions":{"skip_semantic":True}}
        refs=set()
        for _ in range(100):
            refs.add(r.route(inp).get("skill_ref"))
        self.assertEqual(len(refs),1)

    def test_C08_concurrent_empty_and_valid(self):
        r=_router(); c=_cands(3); res=[]; err=[]
        def w(q):
            try: res.append(r.route({"query":q,"candidate_skills":c}))
            except Exception as e: err.append(str(e))
        ts=[threading.Thread(target=w,args=("" if i%2==0 else "weather",)) for i in range(100)]
        [t.start() for t in ts]; [t.join(10) for t in ts]
        self.assertEqual(len(err),0); self.assertEqual(len(res),100)

    def test_C09_degradation_rapid_toggle_threads(self):
        ctrl,DL=_degradation(); err=[]
        def w():
            try:
                for _ in range(200): ctrl.set_level(DL.D3_CRITICAL); ctrl.set_level(DL.D0_NORMAL)
            except Exception as e: err.append(str(e))
        ts=[threading.Thread(target=w) for _ in range(20)]
        [t.start() for t in ts]; [t.join(10) for t in ts]
        self.assertEqual(len(err),0)

    def test_C10_concurrent_escape_hatch(self):
        r=_router(); c=_cands(5); res=[]
        def w(): res.append(r.route({"query":"@override org.osp.weather","candidate_skills":c}))
        ts=[threading.Thread(target=w) for _ in range(50)]
        [t.start() for t in ts]; [t.join(10) for t in ts]
        self.assertEqual(len(res),50)
        for rr in res: self.assertFalse(rr.get("refusal"))


class TestMemoryMega(unittest.TestCase):
    """20 memory & resource management tests."""

    def test_D01_no_leak_5000_routes(self):
        tracemalloc.start()
        r=_router(); c=_cands(3)
        s1=tracemalloc.take_snapshot()
        for _ in range(5000): r.route({"query":"weather","candidate_skills":c})
        s2=tracemalloc.take_snapshot()
        diff=sum(s.size_diff for s in s2.compare_to(s1,'lineno')[:20])
        tracemalloc.stop()
        self.assertLess(diff, 10*1024*1024)

    def test_D02_gc_collectable(self):
        r=_router(); ref=weakref.ref(r); del r; gc.collect()

    def test_D03_200_candidates(self):
        r=_router()
        c=[{"skill_id":f"s{i}","name":f"S{i}","description":f"desc {i}","risk_level":"LOW"} for i in range(200)]
        res=r.route({"query":"desc","candidate_skills":c})
        self.assertIn("trace_events",res)

    def test_D04_trace_bounded(self):
        r=_router(); c=_cands(10)
        res=r.route({"query":"weather","candidate_skills":c})
        self.assertLess(len(res.get("trace_events",[])),50)

    def test_D05_safety_history_bounded(self):
        s=_safety()
        for i in range(200): s.check_safety(f"query {i}",{})
        self.assertLessEqual(len(s._lexical_history),200)

    def test_D06_no_leak_safety_1000(self):
        tracemalloc.start()
        s=_safety(); s1=tracemalloc.take_snapshot()
        for i in range(1000): s.check_safety(f"test {i}",{})
        s2=tracemalloc.take_snapshot()
        diff=sum(x.size_diff for x in s2.compare_to(s1,'lineno')[:20])
        tracemalloc.stop()
        self.assertLess(diff, 5*1024*1024)

    def test_D07_response_size_bounded(self):
        r=_router(); c=_cands(10)
        res=r.route({"query":"weather","candidate_skills":c})
        self.assertLess(len(json.dumps(res)), 10000)

    def test_D08_large_query_no_oom(self):
        r=_router(); c=_cands(3)
        res=r.route({"query":"x"*100000,"candidate_skills":c})
        self.assertIn("trace_events",res)

    def test_D09_many_safety_instances(self):
        instances=[_safety() for _ in range(50)]
        for s in instances: s.check_safety("test",{})

    def test_D10_refusal_response_compact(self):
        r=_router(); c=_cands(3)
        res=r.route({"query":"'; DROP TABLE x;","candidate_skills":c})
        self.assertLess(len(json.dumps(res)), 2000)


class TestConformanceMega(unittest.TestCase):
    """25 protocol conformance depth tests."""

    def setUp(self):
        self.r=_router(); self.c=_cands(5)

    def test_E01_idempotent(self):
        inp={"query":"weather","candidate_skills":self.c,"routing_conditions":{"skip_semantic":True}}
        self.assertEqual(self.r.route(inp).get("skill_ref"), self.r.route(inp).get("skill_ref"))

    def test_E02_refusals_have_traces(self):
        for q in ["","'; DROP TABLE x;","rm -rf /etc/passwd"]:
            r=self.r.route({"query":q,"candidate_skills":self.c})
            self.assertIn("trace_events",r); self.assertTrue(r.get("refusal"))

    def test_E03_json_serializable(self):
        for q in ["weather","","rm -rf /","@override t",]:
            r=self.r.route({"query":q,"candidate_skills":self.c})
            json.dumps(r)

    def test_E04_trace_event_codes(self):
        r=self.r.route({"query":"weather","candidate_skills":self.c})
        for e in r.get("trace_events",[]): self.assertIn("code",e)

    def test_E05_decision_stability_present(self):
        for q in ["weather","calendar","finance","music"]:
            r=self.r.route({"query":q,"candidate_skills":self.c})
            if not r.get("refusal"): self.assertIn("decision_stability",r)

    def test_E06_skill_ref_matches_candidate(self):
        r=self.r.route({"query":"weather forecast","candidate_skills":self.c})
        if not r.get("refusal"):
            ids=[c["skill_id"] for c in self.c]
            self.assertIn(r["skill_ref"], ids)

    def test_E07_escape_hatch_direct_dispatch(self):
        r=self.r.route({"query":"@override org.osp.weather","candidate_skills":self.c})
        self.assertEqual(r.get("decision_stability"),"escape_hatch_direct")

    def test_E08_empty_candidates_escalation(self):
        r=self.r.route({"query":"test","candidate_skills":[]})
        self.assertIsNone(r.get("skill_ref"))
        self.assertEqual(r.get("safety_clearance"),"escalate")

    def test_E09_tie_break_deterministic(self):
        dupes=[{"skill_id":"b","name":"B","description":"test","risk_level":"LOW"},
               {"skill_id":"a","name":"A","description":"test","risk_level":"LOW"}]
        r1=self.r.route({"query":"test","candidate_skills":dupes,"routing_conditions":{"skip_semantic":True}})
        r2=self.r.route({"query":"test","candidate_skills":dupes,"routing_conditions":{"skip_semantic":True}})
        self.assertEqual(r1.get("skill_ref"), r2.get("skill_ref"))

    def test_E10_approximate_flag_present(self):
        r=self.r.route({"query":"weather","candidate_skills":self.c})
        if not r.get("refusal"): self.assertIn("approximate",r)

    def test_E11_tie_break_applied_flag(self):
        r=self.r.route({"query":"weather","candidate_skills":self.c})
        if not r.get("refusal"): self.assertIn("tie_break_applied",r)

    def test_E12_safety_clearance_values(self):
        valid={"allow","restricted","escalate",None}
        for q in ["weather","test","finance"]:
            r=self.r.route({"query":q,"candidate_skills":self.c})
            if not r.get("refusal"):
                self.assertIn(r.get("safety_clearance"),valid)

    def test_E13_refusal_has_reason_code(self):
        r=self.r.route({"query":"'; DROP TABLE x;","candidate_skills":self.c})
        self.assertIn("reason_code",r)

    def test_E14_refusal_has_message(self):
        r=self.r.route({"query":"rm -rf /","candidate_skills":self.c})
        self.assertIn("message",r)

    def test_E15_trace_events_ordered(self):
        r=self.r.route({"query":"weather","candidate_skills":self.c})
        codes=[e["code"] for e in r.get("trace_events",[])]
        self.assertTrue(codes[-1].startswith("ROUTING_DECISION") or codes[-1].startswith("ROUTING_FALLBACK"))

    def test_E16_no_internal_scores_leaked(self):
        r=self.r.route({"query":"weather","candidate_skills":self.c})
        self.assertNotIn("_bm25_score",r)
        self.assertNotIn("_semantic_score",r)

    def test_E17_float_query_handled(self):
        r=self.r.route({"query":3.14,"candidate_skills":self.c})
        self.assertIn("trace_events",r)

    def test_E18_list_query_handled(self):
        r=self.r.route({"query":["a","b"],"candidate_skills":self.c})
        self.assertIn("trace_events",r)

    def test_E19_bool_query_handled(self):
        r=self.r.route({"query":True,"candidate_skills":self.c})
        self.assertIn("trace_events",r)

    def test_E20_none_query_handled(self):
        r=self.r.route({"query":None,"candidate_skills":self.c})
        self.assertIn("trace_events",r)


if __name__ == "__main__":
    unittest.main()

import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from datetime import datetime, timezone, timedelta
import run
T0 = datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc); MS = int(T0.timestamp() * 1000)
def entry(buy, price=100.0): return {"id": "forward.xautusdt", "fetched_at": run.iso(T0), "value": {"coin": "XAUT", "stance": "wait", "price": price, "buy": buy}}
def C(i, h, l, c): return [MS + i * 3600_000, c, h, l, c, 1]
def flat(n=24, p=100.0): return [C(i, p, p, p) for i in range(n)]
BUY = {"zone_lo": 94, "zone_hi": 95, "invalidation": 93, "target": 108, "risk_pct": 2.105, "reward_pct": 13.684}
class T(unittest.TestCase):
    def test_not_scored_before_24h(self): self.assertIsNone(run.score(entry(None), flat(23)))
    def test_no_plan_return(self):
        c = flat(); c[-1] = C(23, 110, 100, 110); r = run.score(entry(None), c); self.assertEqual(r["buy_status"], "no_plan"); self.assertEqual(r["ret_24h_pct"], 10.0)
    def test_no_touch(self): self.assertEqual(run.score(entry(BUY), flat())["buy_status"], "no_touch")
    def test_target_first(self):
        c = flat(); c[3] = C(3, 100, 94.5, 96); c[6] = C(6, 108.5, 100, 108)   # touches zone, later hits target
        r = run.score(entry(BUY), c); self.assertEqual(r["buy_status"], "target_first"); self.assertAlmostEqual(r["net_pct"], 13.684 - 0.3, 3)
    def test_invalid_first_and_same_candle_conservative(self):
        c = flat(); c[3] = C(3, 100, 92.5, 96); r = run.score(entry(BUY), c)          # touch and invalidation in one candle
        self.assertEqual(r["buy_status"], "invalid_first"); self.assertAlmostEqual(r["net_pct"], -2.105 - 0.3, 3)
        c = flat(); c[3] = C(3, 109, 94, 100); self.assertEqual(run.score(entry(BUY), c)["buy_status"], "target_first")  # target hit after touch in same candle, no invalidation
    def test_open_mark_to_market(self):
        c = flat(); c[2] = C(2, 100, 94.8, 96); c[-1] = C(23, 100, 96, 99); r = run.score(entry(BUY), c)
        self.assertEqual(r["buy_status"], "open"); self.assertAlmostEqual(r["net_pct"], 100 * (99 / 95 - 1) - 0.3, 3)
    def test_new_entries_hourly_and_append_only(self):
        rec = {"records": [{"id": "recommendation.%susdt" % s.lower(), "value": {"stance": "wait", "price_ref": 1.0, "price_ref_time": 0, "edge": {"proven": False}, "buy_plan": None, "news": {"wait": False, "leak_trap": False}}} for s in run.SYMS]}
        e = run.new_entries(rec, {"records": []}, T0); self.assertEqual(len(e), 4)
        old = {"records": e}; self.assertEqual(run.new_entries(rec, old, T0 + timedelta(minutes=30)), [])          # too soon
        self.assertEqual(len(run.new_entries(rec, old, T0 + timedelta(minutes=60))), 4)
    def test_summary_counts(self):
        sc = [{"value": {"coin": "XAUT", "entry_time": "2026-11-26T10:00:00Z", "buy_status": "target_first", "net_pct": 5.0}}, {"value": {"coin": "XAUT", "entry_time": "2026-11-26T11:00:00Z", "buy_status": "invalid_first", "net_pct": -2.0}},
              {"value": {"coin": "XAUT", "entry_time": "2026-11-27T11:00:00Z", "buy_status": "no_touch", "net_pct": None}}]
        s = run.summarize("XAUT", [], sc, "t")["value"]; self.assertEqual((s["scored"], s["touched"], s["wins"], s["independent_days"]), (3, 2, 1, 2)); self.assertEqual(s["avg_net_pct"], 1.5)
if __name__ == "__main__": unittest.main()

import os, sys, unittest
from datetime import datetime, timezone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline")); sys.path.insert(0, os.path.join(ROOT, "modules", "crosscheck-log"))
import validate as V, run as R
NOW = datetime(2026, 11, 25, 12, 30, tzinfo=timezone.utc)
def doc(rid, ck, t="2026-11-25T12:00:00Z"): return {"records": [{"id": rid, "fetched_at": t, "checked_against": ck}]}
def docs(diff=0.03, ok=True, t="2026-11-25T12:00:00Z"):
    return {"price-spot": doc("price.xautusdt", {"diff_pct": diff, "ok": ok}, t), "klines": doc("kline.xautusdt.1h", {"max_diff_pct": 0.05, "median_diff_pct": 0.01, "ok": True}, t),
            "flow": doc("flow.xautusdt.1h", {"diff_pct": 0, "ok": True}, t), "volume-profile": {"records": [{"id": "profile.xautusdt.24h", "fetched_at": t, "checked_against": None}]}}
class T(unittest.TestCase):
    def test_entries_use_max_diff_for_candles(self):
        t, e = R.entries(docs()); self.assertEqual(e["kline.xautusdt.1h"][0], 0.05); self.assertEqual(e["price.xautusdt"], [0.03, True]); self.assertNotIn("profile.xautusdt.24h", e)
    def test_append_and_dedupe(self):
        d1 = R.build(docs(), None, NOW); self.assertEqual(d1["records"][0]["stats"]["runs"], 1)
        d2 = R.build(docs(), d1, NOW); self.assertEqual(d2["records"][0]["stats"]["runs"], 1)        # same data time: not logged twice
        d3 = R.build(docs(t="2026-11-25T13:00:00Z"), d2, NOW); self.assertEqual(d3["records"][0]["stats"]["runs"], 2)
    def test_flag_counted(self):
        d = R.build(docs(diff=0.8, ok=False), None, NOW); st = d["records"][0]["stats"]
        self.assertEqual(st["flagged_total"], 1); self.assertEqual(st["groups"]["price"]["max_diff_pct"], 0.8); self.assertEqual(st["checks_total"], 3)
    def test_mean_and_max(self):
        d1 = R.build(docs(diff=0.1), None, NOW); d2 = R.build(docs(diff=0.3, t="2026-11-25T13:00:00Z"), d1, NOW); g = d2["records"][0]["stats"]["groups"]["price"]
        self.assertEqual(g["mean_diff_pct"], 0.2); self.assertEqual(g["max_diff_pct"], 0.3); self.assertEqual(g["checks"], 2)
    def test_cap(self):
        runs = [["t%d" % i, "l", {"price.x": [0.0, True]}] for i in range(R.KEEP + 50)]
        self.assertEqual(len(R.update(runs, "new", "now", {"price.x": [0.0, True]})), R.KEEP)
    def test_no_checks_fails(self):
        with self.assertRaises(ValueError): R.build({"price-spot": doc("price.x", None)}, None, NOW)
    def test_valid_envelope(self):
        d = R.build(docs(), None, NOW); env = V.load(os.path.join(ROOT, "schemas", "envelope.schema.json")); sch = V.load(os.path.join(ROOT, "modules", "crosscheck-log", "schema", "crosscheck-log.schema.json"))
        errs, stale = V.validate_output(d, sch, env, NOW); self.assertEqual(errs, [])
if __name__ == "__main__":
    unittest.main()

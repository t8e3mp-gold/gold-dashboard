import os, sys, unittest
from datetime import datetime, timezone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline")); sys.path.insert(0, os.path.join(ROOT, "modules", "demo-results")); sys.path.insert(0, os.path.join(ROOT, "modules", "recommendation"))
import validate as V, importlib.util
def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
R = _load("demo_run", os.path.join(ROOT, "modules", "demo-results", "run.py")); REC = _load("rec_run", os.path.join(ROOT, "modules", "recommendation", "run.py"))
NOW = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc)
D = {"as_of": "2026-11-28T10:00:00Z", "trades": 3, "open_trades": 1, "wins": 2, "total_net_pct": 0.4, "max_drawdown_pct": 0.2, "fee_per_side_pct": 0.1}
def rec_doc():
    return {"records": [{"stats": {"stages": list(REC.STAGES), "stage_min_trades": {str(k): v for k, v in REC.STAGE_MIN_TRADES.items()}, "full_level": REC.FULL_LEVEL},
                         "value": {"edge": {"full_dd_pct": REC.FULL_DD_PCT}}}]}
class T(unittest.TestCase):
    def test_small_sample_is_stage_zero_and_counts_open(self):
        r = R.build(D, rec_doc(), NOW)["records"][0]["value"]
        self.assertEqual(r["stage"], 0); self.assertEqual(r["trades"], 3); self.assertEqual(r["open_trades"], 1); self.assertEqual(r["closed_trades"], 2)
        self.assertEqual(r["next_stage"], 60); self.assertEqual(r["min_trades_for_next"], 100); self.assertAlmostEqual(r["win_rate"], 0.6667, 4)
    def test_stage_parity_with_recommendation_gate(self):
        st = list(REC.STAGES); mins = {str(k): v for k, v in REC.STAGE_MIN_TRADES.items()}
        for n in (50, 99, 100, 150, 199, 200, 400):
            for wr in (0.5, 0.6, 0.7, 0.9, 0.98, 1.0):
                for net in (-1.0, 0.0, 2.0):
                    for dd in (5.0, 19.9, 20.0):
                        w = round(n * wr); row = {"trades": n, "win_rate": w / n, "total_net_pct": net, "max_drawdown_pct": dd}
                        want = max([s for s in st if REC.qualifies(row, s)] or [0])
                        self.assertEqual(R.stage_of(n, w, net, dd, st, mins, REC.FULL_LEVEL, REC.FULL_DD_PCT), want, (n, w, net, dd))
    def test_negative_net_never_opens_a_stage(self):
        d = dict(D, trades=500, wins=490, open_trades=0, total_net_pct=-0.1); self.assertEqual(R.build(d, rec_doc(), NOW)["records"][0]["value"]["stage"], 0)
    def test_rejects_extra_keys_so_nothing_private_rides_along(self):
        for extra in ("balance", "account", "order_id", "price"):
            with self.assertRaises(ValueError): R.check(dict(D, **{extra: 1}))
    def test_rejects_missing_or_inconsistent(self):
        d = dict(D); d.pop("wins")
        with self.assertRaises(ValueError): R.check(d)
        with self.assertRaises(ValueError): R.check(dict(D, wins=4))
        with self.assertRaises(ValueError): R.check(dict(D, open_trades=4))
        with self.assertRaises(ValueError): R.check(dict(D, as_of="yesterday"))
        with self.assertRaises(ValueError): R.check(dict(D, trades=2.5))
    def test_output_valid(self):
        d = R.build(D, rec_doc(), NOW); env = V.load(os.path.join(ROOT, "schemas", "envelope.schema.json")); sch = V.load(os.path.join(ROOT, "modules", "demo-results", "schema", "demo-results.schema.json"))
        errs, stale = V.validate_output(d, sch, env, NOW); self.assertEqual(errs, [])
if __name__ == "__main__":
    unittest.main()

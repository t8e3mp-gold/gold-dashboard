import os, sys, unittest, math
from datetime import datetime, timezone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline")); sys.path.insert(0, os.path.join(ROOT, "modules", "intent"))
import validate as V, run as R
H = R.H
NOW = datetime(2026, 11, 25, 12, 30, tzinfo=timezone.utc); NMS = int(NOW.timestamp() * 1000)
class T(unittest.TestCase):
    def test_percentile_hand_computed(self):
        q = [1, 2, 3, 4, 5]
        self.assertEqual(R.pct(q, 50), 3); self.assertEqual(R.pct(q, 0), 1); self.assertEqual(R.pct(q, 100), 5); self.assertAlmostEqual(R.pct(q, 25), 2.0)
        self.assertAlmostEqual(R.pct([10, 20], 50), 15.0)
    def test_large_trade_split(self):
        t0 = 0; tr = [(i * 100, 1.0, i % 2 == 0) for i in range(990)] + [(99000 + i, 50.0, True) for i in range(5)] + [(99100 + i, 50.0, False) for i in range(5)]
        rows, st = R.size_record(tr, t0, 1)
        self.assertEqual(st["large_trades"], 10); self.assertEqual(st["large_net_buy"], 0.0)       # 5 big buys vs 5 big sells
        self.assertEqual(st["sample_trades"], 1000); self.assertAlmostEqual(st["large_volume_share_pct"], 500 / (990 + 500) * 100, places=2)
        self.assertEqual(rows[0][4], 10)
    def test_too_few_trades(self):
        with self.assertRaises(ValueError): R.size_record([(0, 1.0, True)] * 10, 0, 1)
    def test_wilson(self):
        lo, hi = R.wilson(5, 10); self.assertTrue(lo < 50 < hi); self.assertEqual(R.wilson(0, 0), (None, None))
        lo, hi = R.wilson(50, 50); self.assertGreater(lo, 90)
    def _series(self, n, f):
        kl, fl = [], []
        for i in range(n):
            o = 100.0 + f(i)[0]; c = 100.0 + f(i)[1]; t = i * H
            kl.append([t, o, max(o, c), min(o, c), c, 10.0]); d = f(i)[2]; fl.append([t, 10.0, 5 + d / 2, 5 - d / 2, d, 0.0])
        return kl, fl
    def test_divergence_detected(self):
        # last 6 hours: price rises 1 per hour but delta is -3 per hour (30% of volume) -> divergence
        def f(i):
            if i >= 94: return (i * 0.01 + (i - 94), i * 0.01 + (i - 93), -3.0)
            return (i * 0.01, i * 0.01, 0.0)
        kl, fl = self._series(100, f)
        v, h = R.divergence(kl, fl)
        self.assertEqual(v["state"], "price up while net taker flow is selling"); self.assertGreater(v["price_change_pct"], 0.3); self.assertAlmostEqual(v["net_delta_pct_of_volume"], -30.0, places=1)
    def test_no_divergence_when_aligned(self):
        kl, fl = self._series(100, lambda i: (i * 0.5, i * 0.5 + 0.5, 3.0))
        v, h = R.divergence(kl, fl); self.assertEqual(v["state"], "no divergence"); self.assertEqual(h["past_events"], 0); self.assertEqual(h["reading"], "no evidence")
    def test_history_counts_followthrough(self):
        # repeating 12-hour pattern: 6h price up with selling delta, then next 6h price down => delta direction (down) followed every time
        def f(i):
            ph = (i // 6) % 2
            return ((i % 6) * 1.0 + 0.0, (i % 6) * 1.0 + 1.0, -3.0) if ph == 0 else (6 - (i % 6), 5 - (i % 6), -3.0)
        kl, fl = self._series(120, f)
        v, h = R.divergence(kl, fl)
        self.assertGreater(h["past_events"], 3); self.assertEqual(h["next_window_followed_delta_direction"], h["past_events"])
    def test_short_history_fails(self):
        kl, fl = self._series(30, lambda i: (0, 0, 0))
        with self.assertRaises(ValueError): R.divergence(kl, fl)
    def test_build_valid(self):
        kl, fl = self._series(300, lambda i: (i * 0.01, i * 0.01 + 0.01, 1.0))
        kd = {"records": [{"id": "kline.%susdt.1h" % s.lower(), "value": kl} for s in R.SYMS]}; fd = {"records": [{"id": "flow.%susdt.1h" % s.lower(), "value": fl} for s in R.SYMS]}
        tr = lambda s, a, b: [(a + i * 1000, 1.0 + (i % 7), i % 2 == 0) for i in range(5000)]
        d = R.build(tr, kd, fd, NOW)
        env = V.load(os.path.join(ROOT, "schemas", "envelope.schema.json")); sch = V.load(os.path.join(ROOT, "modules", "intent", "schema", "intent.schema.json"))
        errs, stale = V.validate_output(d, sch, env, NOW); self.assertEqual(errs, []); self.assertEqual(len(d["records"]), 5)
        self.assertTrue(all(r["label"] == "hypothesis" for r in d["records"]))
if __name__ == "__main__":
    unittest.main()

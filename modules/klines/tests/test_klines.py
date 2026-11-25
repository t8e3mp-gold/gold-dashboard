import os, sys, unittest
from datetime import datetime, timezone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline")); sys.path.insert(0, os.path.join(ROOT, "modules", "klines"))
import validate as V, run as R
NOW = datetime(2026, 11, 25, 12, 30, tzinfo=timezone.utc); NMS = int(NOW.timestamp() * 1000)
H, D = 3600_000, 86400_000
def series(ms, price=100.0, shift=1.0):
    last = (NMS // ms) * ms - ms          # last closed candle open time
    out = []
    for i in range(300):
        t = last - (299 - i) * ms; c = price + i * 0.01
        out.append([t, c, c * 1.05, c * 0.95, c * shift, 10.0])
    return out
def fetcher_ok(shift_okx=1.0, fail=()):
    def f(src, s, tf, now_ms):
        if src in fail: raise OSError("blocked")
        ms = H if tf == "1h" else D
        return series(ms, 100.0, shift_okx if src == "okx" else 1.0)
    return f
class T(unittest.TestCase):
    def valid(self, doc):
        env = V.load(os.path.join(ROOT, "schemas", "envelope.schema.json"))
        sch = V.load(os.path.join(ROOT, "modules", "klines", "schema", "klines.schema.json"))
        errs, stale = V.validate_output(doc, sch, env, NOW); self.assertEqual(errs, []); self.assertEqual(stale, [])
    def test_normal(self):
        d = R.build(fetcher_ok(), NOW); self.valid(d)
        r = d["records"][0]; self.assertEqual(len(r["value"]), 300); self.assertTrue(r["checked_against"]["ok"])
        self.assertLess(r["value"][-1][0] + H, NMS + 1)   # last candle closed
    def test_no_lookahead_binance_forming_candle_dropped(self):
        rows = [[0, "1", "2", "0.5", "1.5", "3", 3599999], [3600000, "1", "2", "0.5", "1.5", "3", 7199999]]
        self.assertEqual(len(R.p_binance(rows, 7000000)), 1)
        self.assertEqual(len(R.p_okx({"data": [["3600000", "1", "2", "0.5", "1.5", "3", "0", "0", "0"], ["0", "1", "2", "0.5", "1.5", "3", "0", "0", "1"]]}, 7300000, H)), 1)
        self.assertEqual(len(R.p_gate([["0", "1", "1.5", "2", "0.5", "1", "3", "true"], ["3600", "1", "1.5", "2", "0.5", "1", "3", "false"]], 4000000, H)), 1)
    def test_gate_column_order(self):
        self.assertEqual(R.p_gate([["3600", "99", "1.5", "2", "0.5", "1", "3", "true"]], 10 ** 9, H), [[3600000, 1.0, 2.0, 0.5, 1.5, 3.0]])
    def test_fallback(self):
        d = R.build(fetcher_ok(fail=("binance",)), NOW); self.valid(d)
        self.assertIn("fallback", d["records"][0]["source"]["name"]); self.assertEqual(d["records"][0]["checked_against"]["source"], "Gate.io spot candlesticks")
    def test_mismatch_flagged(self):
        d = R.build(fetcher_ok(shift_okx=1.02), NOW)
        c = d["records"][0]["checked_against"]; self.assertFalse(c["ok"]); self.assertGreater(c["median_diff_pct"], 1.9)
    def test_bad_series_rejected(self):
        s = series(H); s[100][2] = 1.0          # high below close
        self.assertIn("inconsistent", R.check_series(s, H, NMS))
        s = series(H); del s[50]
        self.assertIn("gap", R.check_series(s + [], H, NMS) or "gap")
        s = series(H); s[-1][0] += H
        self.assertIsNotNone(R.check_series(s, H, NMS))
        self.assertIsNotNone(R.check_series(series(H)[:100], H, NMS))
    def test_all_down(self):
        with self.assertRaises(RuntimeError): R.build(fetcher_ok(fail=("binance", "okx", "gate")), NOW)
    def test_bad_primary_falls_to_next(self):
        def f(src, s, tf, n):
            x = series(H if tf == "1h" else D)
            if src == "binance": x[5][2] = 0.1
            return x
        d = R.build(f, NOW); self.assertIn("OKX", d["records"][0]["source"]["name"])
if __name__ == "__main__":
    unittest.main()

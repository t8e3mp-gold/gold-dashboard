import os, sys, unittest
from datetime import datetime, timezone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline")); sys.path.insert(0, os.path.join(ROOT, "modules", "flow"))
import validate as V, run as R
NOW = datetime(2026, 11, 25, 12, 30, tzinfo=timezone.utc); NMS = int(NOW.timestamp() * 1000)
H, D = 3600_000, 86400_000
def rows(ms, buy_frac=0.6):
    last = (NMS // ms) * ms - ms
    return [[last - (299 - i) * ms, 10.0, buy_frac * 10.0] for i in range(300)]
def fk(buy=0.6):
    return lambda s, tf, n: rows(H if tf == "1h" else D, buy)
def agg_ok(s, a, b): return (6.0, 50)       # matches 0.6 * 10
class T(unittest.TestCase):
    def test_hand_computed_delta(self):
        f = R.to_flow([[0, 10.0, 7.0], [1, 10.0, 4.0]])
        self.assertEqual(f[0], [0, 10.0, 7.0, 3.0, 4.0, 4.0])        # delta = 7-3
        self.assertEqual(f[1], [1, 10.0, 4.0, 6.0, -2.0, 2.0])       # delta = 4-6, cvd = 4-2
    def test_parse_drops_forming_and_rejects_bad(self):
        r = [[0, "1", "1", "1", "1", "10", 3599999, "0", 5, "6", "0"], [3600000, "1", "1", "1", "1", "10", 7199999, "0", 5, "6", "0"]]
        self.assertEqual(len(R.parse(r, 7000000)), 1)
        with self.assertRaises(ValueError): R.parse([[0, "1", "1", "1", "1", "10", 1, "0", 5, "11", "0"]], 100)
    def test_build_valid_and_check_ok(self):
        d = R.build(fk(), agg_ok, None, NOW)
        env = V.load(os.path.join(ROOT, "schemas", "envelope.schema.json")); sch = V.load(os.path.join(ROOT, "modules", "flow", "schema", "flow.schema.json"))
        errs, stale = V.validate_output(d, sch, env, NOW); self.assertEqual(errs, []); self.assertEqual(stale, [])
        r = d["records"][0]; self.assertTrue(r["checked_against"]["ok"]); self.assertAlmostEqual(r["value"][-1][4], 2.0)
    def test_agg_mismatch_flagged(self):
        d = R.build(fk(), lambda s, a, b: (5.0, 9), None, NOW)
        self.assertFalse(d["records"][0]["checked_against"]["ok"])
    def test_agg_too_many_pages_skipped(self):
        d = R.build(fk(), lambda s, a, b: None, None, NOW)
        self.assertIsNone(d["records"][0]["checked_against"]); self.assertIn("XAUT.1h", d["meta"]["notes"])
    def test_klines_volume_consistency(self):
        kd = {"records": [{"id": "kline.xautusdt.1d", "source": {"name": "Binance public data mirror"}, "value": [[r[0], 0, 0, 0, 0, r[1]] for r in rows(D)]}]}
        d = R.build(fk(), agg_ok, kd, NOW); c = d["records"][1]["checked_against"]; self.assertTrue(c["ok"]); self.assertEqual(c["value"], 300)
        kd["records"][0]["value"][10][5] = 99.0
        d = R.build(fk(), agg_ok, kd, NOW); self.assertFalse(d["records"][1]["checked_against"]["ok"])
    def test_stale_or_short_series_fails(self):
        with self.assertRaises(RuntimeError): R.build(lambda s, tf, n: rows(H)[:50], agg_ok, None, NOW)
    def test_agg_sum_pagination(self):
        pages = [[{"a": i, "T": 100 + i, "m": i % 2 == 0, "q": "1"} for i in range(1000)], [{"a": 1000 + i, "T": 2000 + i, "m": False, "q": "2"} for i in range(5)]]
        it = iter(pages); b, n = R.agg_buy_volume("ETH", 0, 10 ** 6, lambda u: next(it))
        self.assertEqual(n, 1005); self.assertAlmostEqual(b, 500 * 1 + 5 * 2)
if __name__ == "__main__":
    unittest.main()

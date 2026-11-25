import os, sys, unittest
from datetime import datetime, timezone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline")); sys.path.insert(0, os.path.join(ROOT, "modules", "levels"))
import validate as V, run as R
NOW = datetime(2026, 11, 25, 12, 30, tzinfo=timezone.utc)
def candle(i, o, h, l, c): return [i * 3600000, o, h, l, c, 1.0]
class T(unittest.TestCase):
    def test_swings_hand_computed(self):
        hs = [10, 11, 12, 20, 12, 11, 10]; c = [candle(i, h, h, h - 1, h) for i, h in enumerate(hs)]
        H, L = R.swings(c, 3, 2, 3); self.assertEqual([p for _, p in H], [20]); self.assertEqual(L, [])
        ls = [10, 9, 8, 1, 8, 9, 10]; c = [candle(i, 10, 10, l, 10) for i, l in enumerate(ls)]
        H, L = R.swings(c, 3, 2, 3); self.assertEqual([p for _, p in L], [1])
    def test_merge_within_tolerance(self):
        z = R.merge([(100.0, "profile", "a"), (100.1, "swing", "b"), (105.0, "swing", "c")])
        self.assertEqual(len(z), 2); self.assertEqual(z[0]["types"], ["profile", "swing"]); self.assertAlmostEqual(z[0]["mid"], 100.05)
    def test_nodes(self):
        rows = [[i, i + 1, v, 0] for i, v in enumerate([1, 1, 9, 1, 1, 1, 7, 1])]
        self.assertEqual(R.nodes(rows), [2.5, 6.5])
    def test_atr(self):
        c = [candle(i, 10, 11, 9, 10) for i in range(20)]; self.assertEqual(R.atr(c), 2.0)
    def test_history_bounce_from_above(self):
        # price at 110, dips to zone 100 on candle 5 and then rises by more than one ATR (atr=2) -> 1 episode, 1 bounce
        c = [candle(i, 110, 111, 109, 110) for i in range(5)] + [candle(5, 110, 110, 100, 101)] + [candle(6 + j, 101, 104 + j, 100.5, 103) for j in range(8)]
        z = {"lo": 99.9, "hi": 100.1, "mid": 100.0}
        self.assertEqual(R.history(z, c, 2.0), (1, 1))
    def test_history_break_is_not_a_bounce(self):
        c = [candle(i, 110, 111, 109, 110) for i in range(5)] + [candle(5, 110, 110, 100, 101)] + [candle(6 + j, 98, 99, 90, 95) for j in range(8)]
        z = {"lo": 99.9, "hi": 100.1, "mid": 100.0}
        self.assertEqual(R.history(z, c, 2.0), (1, 0))
    def test_forming_support(self):
        c = [candle(i, 110, 111, 109, 110) for i in range(10)] + [candle(10, 110, 110, 100, 101), candle(11, 101, 106, 101, 105)]
        f = R.forming([{"lo": 99.9, "hi": 100.1, "mid": 100.0}], c, 105)
        self.assertEqual(f, {"side": "support", "zone_mid": 100.0})
        self.assertIsNone(R.forming([{"lo": 99.9, "hi": 100.1, "mid": 100.0}], [candle(i, 110, 111, 109, 110) for i in range(12)], 110))
    def test_build_valid_on_synthetic(self):
        import math
        c1 = [candle(i, 100, 100 + 3 * math.sin(i / 5) + 2, 100 + 3 * math.sin(i / 5) - 2, 100 + 3 * math.sin(i / 5)) for i in range(300)]
        d1 = [candle(i, 100, 105, 95, 100 + (i % 7)) for i in range(100)]
        km = {"records": [{"id": "kline.%susdt.%s" % (s.lower(), tf), "value": v} for s in R.SYMS for tf, v in (("1h", c1), ("1d", d1))]}
        rows = [[90 + i, 91 + i, 10 + (i % 5) * 3, 5] for i in range(60)]
        pr = {"records": [{"id": "profile.%susdt.%s" % (s.lower(), w), "value": rows, "stats": {"poc": 100, "vah": 105, "val": 95, "price_high": 150, "price_low": 90}} for s in R.SYMS for w in ("24h", "7d")]}
        d = R.build(km, pr, NOW)
        env = V.load(os.path.join(ROOT, "schemas", "envelope.schema.json")); sch = V.load(os.path.join(ROOT, "modules", "levels", "schema", "levels.schema.json"))
        errs, _ = V.validate_output(d, sch, env, NOW); self.assertEqual(errs, [])
        z = d["records"][0]["value"]["zones"]; self.assertTrue(len(z) >= 3); self.assertTrue(all(x["lo"] <= x["mid"] <= x["hi"] for x in z))
if __name__ == "__main__":
    unittest.main()

import os, sys, unittest, random
from datetime import datetime, timezone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline")); sys.path.insert(0, os.path.join(ROOT, "modules", "volume-profile"))
import validate as V, run as R
NOW = datetime(2026, 11, 25, 12, 30, tzinfo=timezone.utc); NMS = int(NOW.timestamp() * 1000)

def brute(bars, lo, hi, nb, slices=2000):
    """Independent implementation: cut every candle into thin slices and drop each slice into its bin."""
    w = (hi - lo) / nb; vol = [0.0] * nb
    for _, h, l, v, _ in bars:
        for k in range(slices):
            p = l + (h - l) * (k + 0.5) / slices
            vol[min(nb - 1, int((p - lo) / w))] += v / slices
    return vol

class T(unittest.TestCase):
    def test_hand_computed(self):
        # one candle 10..20 volume 100, window 10..20 with 2 bins: 50 each
        rows, lo, hi = R.profile([[0, 20.0, 10.0, 100.0, 60.0]], nb=2)
        self.assertEqual([round(r[2], 9) for r in rows], [50.0, 50.0]); self.assertEqual([round(r[3], 9) for r in rows], [30.0, 30.0])
        # two candles: A 10..15 vol 10, B 15..20 vol 30 with 2 bins: bins hold 10 and 30; POC = upper bin
        rows, _, _ = R.profile([[0, 15.0, 10.0, 10.0, 0.0], [1, 20.0, 15.0, 30.0, 0.0]], nb=2)
        self.assertEqual([round(r[2], 9) for r in rows], [10.0, 30.0]); st = R.stats(rows)
        self.assertEqual(st["poc"], 17.5)
        self.assertEqual(st["val"], 15.0); self.assertEqual(st["vah"], 20.0)   # 30 of 40 = 75% >= 70% already needs only POC... see next
    def test_value_area_growth(self):
        rows = [[i, i + 1, v, 0.0] for i, v in enumerate([5, 10, 40, 30, 15])]          # total 100, POC bin 2
        st = R.stats(rows)       # 40, then larger neighbour 30 (70) -> stop at 70%
        self.assertEqual((st["val"], st["vah"]), (2, 4)); self.assertEqual(st["value_area_share_pct"], 70.0)
        rows = [[i, i + 1, v, 0.0] for i, v in enumerate([20, 10, 40, 10, 20])]         # 40 -> tie 10/10 goes up -> 50 -> then 20 below(70)
        st = R.stats(rows); self.assertEqual(st["value_area_share_pct"], 70.0)
    def test_matches_brute_force(self):
        random.seed(1); bars = []
        for i in range(60):
            c = 100 + random.uniform(-3, 3); l = c - random.uniform(0.1, 1); h = c + random.uniform(0.1, 1)
            bars.append([i, h, l, random.uniform(1, 10), 0.0])
        rows, lo, hi = R.profile(bars, nb=30); ref = brute(bars, lo, hi, 30)
        tot = sum(ref)
        for r, x in zip(rows, ref): self.assertAlmostEqual(r[2] / tot, x / tot, delta=0.002)
        self.assertAlmostEqual(sum(r[2] for r in rows), sum(b[3] for b in bars), places=9)    # no volume lost
    def test_flat_candle_and_buy_volume_conserved(self):
        rows, _, _ = R.profile([[0, 10.0, 10.0, 5.0, 2.0], [1, 12.0, 11.0, 7.0, 3.0]], nb=10)
        self.assertAlmostEqual(sum(r[2] for r in rows), 12.0); self.assertAlmostEqual(sum(r[3] for r in rows), 5.0)
    def test_clean_rejects_bad(self):
        with self.assertRaises(ValueError): R.clean([[0, 1.0, 2.0, 1.0, 0.0]])        # high < low
        with self.assertRaises(ValueError): R.clean([[0, 2.0, 1.0, 1.0, 2.0]])        # buy > volume
        self.assertEqual(len(R.clean([[0, 2.0, 1.0, 1.0, 0.5], [0, 2.0, 1.0, 1.0, 0.5]])), 1)   # duplicate dropped
    def _fetch(self, fail=False, gaps=False):
        def f(s, minutes, now_ms):
            if fail: raise OSError("blocked")
            end = (now_ms // 60000) * 60000; out = []
            for i in range(minutes):
                if gaps and i % 2: continue
                t = end - (minutes - i) * 60000; p = 100 + (i % 50) * 0.1
                out.append([t, p + 0.3, p - 0.3, 2.0, 1.0])
            return out, end - minutes * 60000
        return f
    def _kl(self):
        H = 3600000; last = (NMS // H) * H - H
        return {"records": [{"id": "kline.%susdt.1h" % s.lower(), "source": {"name": "Binance public data mirror"}, "value": [[last - (299 - i) * H, 0, 0, 0, 0, 120.0] for i in range(300)]} for s in R.SYMS]}
    def test_build_valid_and_volume_check(self):
        d = R.build(self._fetch(), self._kl(), NOW)
        env = V.load(os.path.join(ROOT, "schemas", "envelope.schema.json")); sch = V.load(os.path.join(ROOT, "modules", "volume-profile", "schema", "volume-profile.schema.json"))
        errs, stale = V.validate_output(d, sch, env, NOW); self.assertEqual(errs, []); self.assertEqual(stale, [])
        r = d["records"][0]; self.assertTrue(r["checked_against"]["ok"], r["checked_against"])      # 60 min * 2.0 = 120 per hour
        self.assertAlmostEqual(sum(x[2] for x in r["value"]), 1440 * 2.0, delta=2.1)
    def test_fallback_to_hourly(self):
        d = R.build(self._fetch(fail=True), self._kl(), NOW)
        r = d["records"][0]; self.assertEqual(r["stats"]["bar_size"], "1h"); self.assertIn("fallback", r["source"]["name"]); self.assertIn("XAUT", d["meta"]["notes"])
    def test_sparse_minutes_fall_back(self):
        d = R.build(self._fetch(gaps=True), self._kl(), NOW); self.assertEqual(d["records"][0]["stats"]["bar_size"], "1h")
    def test_no_data_at_all_fails(self):
        with self.assertRaises(RuntimeError): R.build(self._fetch(fail=True), None, NOW)
if __name__ == "__main__":
    unittest.main()

import os, sys, unittest
from datetime import datetime, timezone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline")); sys.path.insert(0, os.path.join(ROOT, "modules", "watch"))
import validate as V, run as R
D = 86400000
def day(i, c): return [i * D, c, c, c, c, 1.0]
def docs(closes, hour_close=None):
    k1d = [day(i, c) for i, c in enumerate(closes)]
    last = len(closes) - 1
    k1h = [[last * D + 23 * 3600000, 1, 1, 1, closes[-1] if hour_close is None else hour_close, 1.0]]
    return {"records": [{"id": "kline.xautusdt.1d", "value": k1d}, {"id": "kline.xautusdt.1h", "value": k1h}]}
class T(unittest.TestCase):
    def test_state(self):
        self.assertEqual(R.state_of(3661, 3660, 3600), "above"); self.assertEqual(R.state_of(3660, 3660, 3600), "between")
        self.assertEqual(R.state_of(3600, 3660, 3600), "between"); self.assertEqual(R.state_of(3599.9, 3660, 3600), "below")
    def test_streak_counts_newest_first(self):
        self.assertEqual(R.streak([3700, 3500, 3670, 3680, 3690], "above", 3660, 3600), 3)
        self.assertEqual(R.streak([3700, 3650], "above", 3660, 3600), 0)
        self.assertEqual(R.streak([3650, 3590, 3580], "below", 3660, 3600), 2)
    def test_forming_candle_is_ignored(self):
        k = [day(i, 3000 + i) for i in range(3)]; now_ms = 2 * D + 5 * 3600000   # candle 2 still forming
        self.assertEqual(len(R.closed_days(k, now_ms)), 2)
        self.assertEqual(len(R.closed_days(k, 3 * D)), 3)
    def test_build_valid_and_crosscheck(self):
        now = datetime.fromtimestamp(4 * D / 1000 + 600, tz=timezone.utc)
        d = R.build(docs([3500, 3650, 3670, 3680]), now); r = d["records"][0]
        self.assertEqual(r["value"]["state"], "above"); self.assertEqual(r["value"]["streak_above"], 2)
        self.assertTrue(r["checked_against"]["ok"])
        env = V.load(os.path.join(ROOT, "schemas", "envelope.schema.json")); sch = V.load(os.path.join(ROOT, "modules", "watch", "schema", "watch.schema.json"))
        errs, stale = V.validate_output(d, sch, env, now); self.assertEqual(errs, [])
    def test_crosscheck_flags_mismatch(self):
        now = datetime.fromtimestamp(4 * D / 1000 + 600, tz=timezone.utc)
        r = R.build(docs([3500, 3650, 3670, 3680], 3700), now)["records"][0]; self.assertFalse(r["checked_against"]["ok"])
if __name__ == "__main__":
    unittest.main()

"""Standby archive fallback (not wired into the pipeline): unit checks with a fake archive, no network."""
import importlib.util, os, unittest
from datetime import datetime, timezone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sp = importlib.util.spec_from_file_location("af", os.path.join(ROOT, "standby", "archive-fallback", "archive_fallback.py"))
af = importlib.util.module_from_spec(sp); sp.loader.exec_module(af)
NOW = datetime(2026, 11, 26, 12, 30, tzinfo=timezone.utc)

def row(t_ms, us, vol=10.0, buy=4.0):
    k = 1000 if us else 1
    return [str(t_ms * k), "1", "2", "0.5", "1.5", str(vol), str(((t_ms + 3600_000) * k) - 1), "0", "5", str(buy), "0", "0"]

class T(unittest.TestCase):
    def test_microseconds_and_forming_candle_and_missing_file(self):
        day = int(datetime(2026, 11, 26, tzinfo=timezone.utc).timestamp() * 1000)
        rows = [row(day + h * 3600_000, True) for h in range(13)]      # 00:00..12:00 open; the 12:00 candle is still forming at 12:30
        def fetch(url): return rows if url.endswith("2026-11-26.zip") else None   # every other day: 404
        out = af.kl_rows("XAUT", "1h", NOW, 2, fetch=fetch)
        self.assertEqual(len(out), 12)                                  # forming candle dropped
        self.assertEqual(out[0][0], day)                                # microseconds turned into milliseconds
        self.assertEqual(out[0][9], 4.0)                                # taker buy volume kept
    def test_milliseconds_also_accepted(self):
        self.assertEqual(af.ms(1700000000000), 1700000000000); self.assertEqual(af.ms(1700000000000000), 1700000000000)
    def test_trades_taker_side(self):
        t0 = int(datetime(2026, 11, 25, 18, tzinfo=timezone.utc).timestamp() * 1000)
        csvrows = [["1", "10", "2.5", "1", "1", str(t0 * 1000 + 5), "False", "True"], ["2", "10", "1.0", "2", "2", str(t0 * 1000 + 6), "True", "True"]]
        tr = af.trades_from_archive("XAUT", t0, t0 + 3600_000, fetch=lambda u: csvrows)
        self.assertEqual(tr, [(t0, 2.5, True), (t0, 1.0, False)])       # buyer_maker False = taker bought
    def test_unpublished_day_fails_loudly(self):
        with self.assertRaises(RuntimeError): af.trades_from_archive("XAUT", 0, 3600_000, fetch=lambda u: None)

if __name__ == "__main__": unittest.main()

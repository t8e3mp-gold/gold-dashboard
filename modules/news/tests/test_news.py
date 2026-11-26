import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from datetime import datetime, timezone, timedelta
import run
RSS = '''<rss><channel><item><title> Fed &amp; rates   </title><link>http://x/1</link><pubDate>Wed, 25 Nov 2026 20:00:00 +0000</pubDate></item>
<item><title>older</title><link>http://x/2</link><pubDate>Tue, 24 Nov 2026 10:00:00 +0200</pubDate></item><item><title>no date</title></item></channel></rss>'''
BEA = "x December 23 8:30 AM N ews Personal Income and Outlays, November 2026 June 2 9:00 AM N ews Foo Bar Quick Links y"
FOMC = '<h4>2026 FOMC Meetings</h4><div class="fomc-meeting__month col"><strong>March</strong></div><div class="fomc-meeting__date col">17-18*</div><h4>2027 FOMC Meetings</h4><div class="fomc-meeting__month"><strong>January</strong></div><div class="fomc-meeting__date">26-27</div>'
def K(closes): return [[0, c, c * 1.001, c * 0.999, c, 1] for c in closes]
class T(unittest.TestCase):
    def test_rss(self):
        r = run.parse_rss(RSS); self.assertEqual([x["title"] for x in r], ["Fed & rates", "older"])
        self.assertEqual(r[1]["published"], "2026-11-24T08:00:00Z")   # +0200 converted to UTC
    def test_bea_time_zone(self):   # Dec 23 8:30 EST = 13:30 UTC ; the June item is inferred as next year
        e = run.parse_bea(BEA, datetime(2026, 11, 26, tzinfo=timezone.utc))
        self.assertEqual(e[0]["start"], "2026-12-23T13:30:00Z"); self.assertEqual(e[0]["title"], "Personal Income and Outlays, November 2026")
        self.assertEqual(e[1]["start"], "2027-06-02T13:00:00Z")      # June 9:00 AM EDT = 13:00 UTC
    def test_fomc(self):   # March 18 14:00 EDT = 18:00 UTC ; January 27 2027 14:00 EST = 19:00 UTC ; hour is assumed
        f = run.parse_fomc(FOMC, datetime(2026, 11, 26, tzinfo=timezone.utc))
        self.assertEqual([x["start"] for x in f], ["2026-03-18T18:00:00Z", "2027-01-27T19:00:00Z"]); self.assertTrue(f[0]["time_assumed"])
    def test_wait_window_and_leak(self):
        now = datetime(2026, 12, 23, 12, 0, tzinfo=timezone.utc); ev = [{"title": "PCE", "start": "2026-12-23T13:30:00Z"}]   # 1.5h ahead
        flat = K([100] * 30); s = run.stance(now, ev, flat)
        self.assertTrue(s["wait"]); self.assertFalse(s["leak_trap"])
        jump = K([100] * 28 + [100, 103]); s = run.stance(now, ev, jump)   # +3% in 2 candles, ATR ~0.2%
        self.assertTrue(s["leak_trap"]); self.assertGreaterEqual(s["move_in_atr"], 2)
        far = datetime(2026, 12, 22, 12, 0, tzinfo=timezone.utc); s = run.stance(far, ev, jump)
        self.assertFalse(s["wait"]); self.assertFalse(s["leak_trap"])   # event more than 2h away: a move is not flagged as pre-release
        after = datetime(2026, 12, 23, 15, 0, tzinfo=timezone.utc); self.assertFalse(run.stance(after, ev, flat)["wait"])  # 1.5h after the 1h window
if __name__ == "__main__": unittest.main()

import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from datetime import date
import calendar_sync as C
ICS = "BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nSUMMARY:Employment Situation for November 2026\r\nDTSTART;VALUE=DATE:20261204\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nSUMMARY:Consumer Price Index for\r\n  November 2026\r\nDTSTART;VALUE=DATE:20261210\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nSUMMARY:Employment Situation for October 2026\r\nDTSTART;VALUE=DATE:20261106\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nSUMMARY:Productivity\r\nDTSTART;VALUE=DATE:20261205\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
class T(unittest.TestCase):
    def test_parse_future_only_and_kinds(self):
        r = C.parse(ICS, date(2026, 11, 26)); self.assertEqual([(e["date"], e["title"]) for e in r], [("2026-12-04", "US jobs report (NFP)"), ("2026-12-10", "US CPI inflation")])
    def test_merge_keeps_other_sources_replaces_bls_drops_past(self):
        cal = {"checked": "x", "note": "n", "events": [{"title": "PCE", "date": "2026-12-23", "source": "https://www.bea.gov/x"}, {"title": "old", "date": "2026-11-01", "source": "https://www.bea.gov/x"}, {"title": "US CPI inflation", "date": "2027-01-13", "source": "https://www.bls.gov/cpi"}]}
        m = C.merge(cal, C.parse(ICS, date(2026, 11, 26)), date(2026, 11, 26))
        self.assertEqual([e["date"] for e in m["events"]], ["2026-12-04", "2026-12-10", "2026-12-23", "2027-01-13"]); self.assertEqual(m["checked"], "2026-11-26")
if __name__ == "__main__": unittest.main()

"""tools/archive_logs.py (monthly archive of the forward log): the workflow runs it for real only once a month, so test it here on synthetic data.
Checks: old records move, recent stay, nothing is lost or counted twice, re-run is a no-op, a half-finished run is safe to re-run."""
import copy, importlib.util, json, os, shutil, tempfile, unittest
from datetime import datetime, timedelta, timezone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sp = importlib.util.spec_from_file_location("al", os.path.join(ROOT, "tools", "archive_logs.py")); al = importlib.util.module_from_spec(sp); sp.loader.exec_module(al)
NOW = datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)
def iso(d): return d.strftime("%Y-%m-%dT%H:%M:%SZ")
def log_rec(coin, t): return {"id": "forward.%susdt" % coin.lower(), "fetched_at": iso(t), "label": "measured", "value": {"coin": coin, "stance": "wait"}}
def score_rec(coin, t, status, net): return {"id": "score.%susdt" % coin.lower(), "fetched_at": iso(t), "label": "measured", "value": {"coin": coin, "entry_time": iso(t), "buy_status": status, "net_pct": net}}

def make(d):
    logs, scores = [], []
    for days_ago in (100, 80, 50, 10, 1):       # 3 older than 45 days, 2 recent
        for c in ("XAUT", "BNB"):
            t = NOW - timedelta(days=days_ago)
            logs.append(log_rec(c, t)); scores.append(score_rec(c, t, "target_first", 0.5) if days_ago != 80 else score_rec(c, t, "no_plan", None))
    for name, recs in (("forward-log", logs), ("forward-score", scores)):
        al.jsave(os.path.join(d, name + ".json"), {"meta": {}, "records": recs})
    return len(logs), len(scores)

class T(unittest.TestCase):
    def setUp(self): self.d = tempfile.mkdtemp(); self.nl, self.ns = make(self.d)
    def tearDown(self): shutil.rmtree(self.d)
    def count_all(self, name):
        live = len(al.jload(os.path.join(self.d, name + ".json"), {"records": []})["records"]); arch = 0; ad = os.path.join(self.d, "archive")
        for f in (os.listdir(ad) if os.path.isdir(ad) else []):
            if f.startswith(name + "-"): arch += len(al.jload(os.path.join(ad, f), {"records": []})["records"])
        return live, arch
    def test_moves_old_keeps_recent_loses_nothing(self):
        r = al.run(self.d, NOW)
        self.assertEqual(r["moved"], 12)                                     # 6 log + 6 score older than 45 days
        for name, n in (("forward-log", self.nl), ("forward-score", self.ns)):
            live, arch = self.count_all(name); self.assertEqual((live, arch), (4, 6)); self.assertEqual(live + arch, n)
        c = al.jload(os.path.join(self.d, "forward-archive.json"), None)["records"][0]["value"]["coins"]
        self.assertEqual(c["XAUT"]["logged"] + c["BNB"]["logged"], 6); self.assertEqual(c["XAUT"]["scored"] + c["BNB"]["scored"], 6)
        self.assertEqual(c["XAUT"]["with_plan"], 2)                          # the 100 and 50 days ago ones; the 80 days ago one has no plan
    def test_rerun_is_a_no_op(self):
        al.run(self.d, NOW); before = open(os.path.join(self.d, "forward-archive.json")).read()
        self.assertEqual(al.run(self.d, NOW), {"moved": 0}); self.assertEqual(open(os.path.join(self.d, "forward-archive.json")).read(), before)
    def test_half_finished_run_is_safe(self):
        saved = {n: open(os.path.join(self.d, n + ".json")).read() for n in ("forward-log", "forward-score")}
        al.run(self.d, NOW); counters = al.jload(os.path.join(self.d, "forward-archive.json"), None)
        for n, s in saved.items(): open(os.path.join(self.d, n + ".json"), "w").write(s)   # as if the run stopped before trimming the live files
        al.run(self.d, NOW)
        self.assertEqual(al.jload(os.path.join(self.d, "forward-archive.json"), None)["records"][0]["value"]["coins"], counters["records"][0]["value"]["coins"])   # not counted twice
        for name, n in (("forward-log", self.nl), ("forward-score", self.ns)):
            live, arch = self.count_all(name); self.assertEqual(live + arch, n)

if __name__ == "__main__": unittest.main()

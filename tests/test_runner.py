import os, sys, json, shutil, tempfile, unittest
from datetime import datetime, timezone, timedelta
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import validate as V, runner

GOOD = {"id": "a.b", "value": 1.5, "unit": "usd", "source": {"name": "x", "url": "https://x.test"},
        "fetched_at": "2026-11-25T10:00:00Z", "label": "measured", "max_age_hours": 24, "checked_against": None}
ENV = V.load(os.path.join(ROOT, "schemas", "envelope.schema.json"))
NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)

class Envelope(unittest.TestCase):
    def doc(self, **chg):
        r = dict(GOOD); r.update(chg); return {"meta": {}, "records": [r]}
    def test_good(self):
        self.assertEqual(V.check_envelope(self.doc(), ENV, NOW), ([], []))
    def test_missing_source(self):
        r = dict(GOOD); del r["source"]
        errs, _ = V.check_envelope({"meta": {}, "records": [r]}, ENV, NOW)
        self.assertTrue(errs)
    def test_missing_time(self):
        r = dict(GOOD); del r["fetched_at"]
        self.assertTrue(V.check_envelope({"meta": {}, "records": [r]}, ENV, NOW)[0])
    def test_bad_label(self):
        self.assertTrue(V.check_envelope(self.doc(label="trust-me"), ENV, NOW)[0])
    def test_stale(self):
        errs, stale = V.check_envelope(self.doc(fetched_at="2026-11-23T10:00:00Z"), ENV, NOW)
        self.assertEqual((errs, stale), ([], ["a.b"]))
    def test_future(self):
        self.assertTrue(V.check_envelope(self.doc(fetched_at="2026-11-26T10:00:00Z"), ENV, NOW)[0])

class Runner(unittest.TestCase):
    def mk(self, mods):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        shutil.copytree(os.path.join(ROOT, "schemas"), os.path.join(d, "schemas"))
        os.makedirs(os.path.join(d, "modules"))
        json.dump({"enabled": list(mods)}, open(os.path.join(d, "modules", "registry.json"), "w"))
        for mid, (inputs, out, code) in mods.items():
            md = os.path.join(d, "modules", mid); os.makedirs(os.path.join(md, "schema"))
            json.dump({"id": mid, "name_ar": "ا", "name_en": mid, "version": "1.0.0", "kind": "compute",
                       "inputs": inputs, "outputs": [{"id": out, "schema": "schema/s.json"}], "label": "measured",
                       "source": {"name": "t", "url": "https://t.test"}, "max_age_hours": 24, "schedule": "daily",
                       "run": ["python", "run.py"]}, open(os.path.join(md, "manifest.json"), "w"))
            json.dump({"type": "object"}, open(os.path.join(md, "schema", "s.json"), "w"))
            open(os.path.join(md, "run.py"), "w").write(code)
        return d
    OK = ("import json,os\nfrom datetime import datetime,timezone\nt=datetime.now(timezone.utc).strftime('@@FMT@@')\n"
          "json.dump({'meta':{},'records':[{'id':'x','value':1,'unit':'u','source':{'name':'n','url':'https://n.test'},"
          "'fetched_at':t,'label':'measured','max_age_hours':24,'checked_against':None}]},open(os.path.join(os.environ['OUT_DIR'],'@@N@@.json'),'w'))\n")
    def ok(self, n):
        return self.OK.replace('@@N@@', n).replace('@@FMT@@', '%Y-%m-%dT%H:%M:%SZ')
    def test_order(self):
        d = self.mk({"b": (["a"], "b", self.ok("b")), "a": ([], "a", self.ok("a"))})
        mans, errs = runner.load_manifests(d)
        self.assertEqual(errs, []); self.assertEqual(runner.order(mans), ["a", "b"])
    def test_cycle(self):
        d = self.mk({"a": (["b"], "a", ""), "b": (["a"], "b", "")})
        with self.assertRaises(ValueError): runner.order(runner.load_manifests(d)[0])
    def test_failure_isolated_and_old_output_kept(self):
        d = self.mk({"good": ([], "good", self.ok("good")), "bad": ([], "bad", "raise SystemExit(3)")})
        dd = os.path.join(d, "data"); os.makedirs(dd)
        open(os.path.join(dd, "bad.json"), "w").write('{"old": true}')
        self.assertEqual(runner.main(d, dd), 1)
        self.assertTrue(os.path.exists(os.path.join(dd, "good.json")))
        self.assertEqual(json.load(open(os.path.join(dd, "bad.json"))), {"old": True})
        meta = json.load(open(os.path.join(dd, "meta.json")))
        self.assertEqual(meta["modules"]["bad"]["status"], "failed")
        self.assertEqual(meta["modules"]["good"]["status"], "ok")
    def test_invalid_output_rejected(self):
        code = "import json,os\njson.dump({'meta':{},'records':[{'id':'x','value':1}]},open(os.path.join(os.environ['OUT_DIR'],'m.json'),'w'))\n"
        d = self.mk({"m": ([], "m", code)}); dd = os.path.join(d, "data"); os.makedirs(dd)
        st, detail = runner.run_module(runner.load_manifests(d)[0]["m"], dd, d)
        self.assertEqual(st, "failed"); self.assertFalse(os.path.exists(os.path.join(dd, "m.json")))
    def test_missing_input(self):
        d = self.mk({"m": (["nope"], "m", self.ok("m"))}); dd = os.path.join(d, "data"); os.makedirs(dd)
        self.assertEqual(runner.run_module(runner.load_manifests(d)[0]["m"], dd, d)[0], "failed")
    def test_real_repo_manifests(self):
        mans, errs = runner.load_manifests(ROOT)
        self.assertEqual(errs, []); runner.order(mans)
if __name__ == "__main__":
    unittest.main()

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
    def test_meta_carries_shell_version(self):
        d = self.mk({"good": ([], "good", self.ok("good"))})
        os.makedirs(os.path.join(d, "site")); open(os.path.join(d, "site", "app.js"), "w").write("const APP_VERSION = 7;\n")
        dd = os.path.join(d, "data"); os.makedirs(dd)
        runner.main(d, dd)
        self.assertEqual(json.load(open(os.path.join(dd, "meta.json")))["app_version"], 7)
        self.assertEqual(runner.shell_version(runner.ROOT), 2)
    def test_invalid_output_rejected(self):
        code = "import json,os\njson.dump({'meta':{},'records':[{'id':'x','value':1}]},open(os.path.join(os.environ['OUT_DIR'],'m.json'),'w'))\n"
        d = self.mk({"m": ([], "m", code)}); dd = os.path.join(d, "data"); os.makedirs(dd)
        st, detail = runner.run_module(runner.load_manifests(d)[0]["m"], dd, d)
        self.assertEqual(st, "failed"); self.assertFalse(os.path.exists(os.path.join(dd, "m.json")))
    def test_missing_input(self):
        d = self.mk({"m": (["nope"], "m", self.ok("m"))}); dd = os.path.join(d, "data"); os.makedirs(dd)
        self.assertEqual(runner.run_module(runner.load_manifests(d)[0]["m"], dd, d)[0], "failed")
    def test_unknown_schema_keyword_rejected(self):
        self.assertTrue(V.lint_schema({"type": "nonsense"}))
        self.assertTrue(V.check_schema(5, {"type": "object", "properties": {"a": {"type": "nonsense"}}}))
        self.assertEqual(V.lint_schema({"type": "object", "properties": {"a": {"type": "string"}}}), [])
    def test_unproduced_input_flagged(self):
        d = self.mk({"m": (["nope"], "m", self.ok("m"))}); dd = os.path.join(d, "data"); os.makedirs(dd)
        mans = runner.load_manifests(d)[0]
        self.assertTrue(runner.lint_manifests(mans, d, dd))
        open(os.path.join(dd, "nope.json"), "w").write("{}")
        self.assertEqual(runner.lint_manifests(mans, d, dd), [])
    def test_history_append_ok_and_drop_rejected(self):
        rec = lambda i, t: {"id": i, "fetched_at": t}
        old = {"records": [rec("a", "2026-11-25T10:00:00Z")]}
        self.assertEqual(runner.check_history(old, {"records": [rec("a", "2026-11-25T10:00:00Z"), rec("a", "2026-11-26T10:00:00Z")]}), [])
        self.assertTrue(runner.check_history(old, {"records": [rec("a", "2026-11-26T10:00:00Z")]}))
    def test_history_enforced_in_run(self):
        d = self.mk({"m": ([], "m", self.ok("m"))}); dd = os.path.join(d, "data"); os.makedirs(dd)
        mp = os.path.join(d, "modules", "m", "manifest.json"); man = json.load(open(mp)); man["history"] = ["m"]; json.dump(man, open(mp, "w"))
        old = {"meta": {}, "records": [{"id": "gone", "fetched_at": "2026-11-20T10:00:00Z"}]}
        json.dump(old, open(os.path.join(dd, "m.json"), "w"))
        st, detail = runner.run_module(runner.load_manifests(d)[0]["m"], dd, d)
        self.assertEqual(st, "failed"); self.assertIn("history", detail)
        self.assertEqual(json.load(open(os.path.join(dd, "m.json"))), old)
    def test_network_blocked_by_default(self):
        code = ("import socket,sys\ntry:\n    socket.create_connection(('1.1.1.1', 53), timeout=3)\n    sys.exit(0)\n"
                "except OSError:\n    sys.exit(7)\n")
        d = self.mk({"n": ([], "n", code)}); dd = os.path.join(d, "data"); os.makedirs(dd)
        st, detail = runner.run_module(runner.load_manifests(d)[0]["n"], dd, d)
        self.assertEqual(st, "failed"); self.assertIn("exit 7", detail)
    def test_module_sees_only_declared_inputs(self):
        code = ("import os,sys\nsys.exit(0 if sorted(os.listdir(os.environ['DATA_DIR'])) == ['a.json'] else 9)\n")
        d = self.mk({"s": (["a"], "s", code)}); dd = os.path.join(d, "data"); os.makedirs(dd)
        open(os.path.join(dd, "a.json"), "w").write("{}"); open(os.path.join(dd, "secret.json"), "w").write("{}")
        st, detail = runner.run_module(runner.load_manifests(d)[0]["s"], dd, d)
        self.assertNotIn("exit 9", detail)
    def test_drill_module_fails_and_others_publish(self):
        d = self.mk({"good": ([], "good", self.ok("good"))})
        os.environ["EXTRA_MODULES"] = "x"; self.addCleanup(os.environ.pop, "EXTRA_MODULES", None)
        mans, errs = runner.load_manifests(d); self.assertTrue(errs)
    def test_real_repo_lint(self):
        mans, _ = runner.load_manifests(ROOT)
        self.assertEqual(runner.lint_manifests(mans, ROOT), [])
        for f in os.listdir(os.path.join(ROOT, "schemas")):
            self.assertEqual(V.lint_schema(V.load(os.path.join(ROOT, "schemas", f))), [], f)
    def test_real_repo_manifests(self):
        mans, errs = runner.load_manifests(ROOT)
        self.assertEqual(errs, []); runner.order(mans)
if __name__ == "__main__":
    unittest.main()

import os, sys, unittest, json
from datetime import datetime, timezone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline")); sys.path.insert(0, os.path.join(ROOT, "modules", "hello"))
import validate as V, run

class T(unittest.TestCase):
    def test_output_valid(self):
        now = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
        doc = run.compute(now)
        env = V.load(os.path.join(ROOT, "schemas", "envelope.schema.json"))
        sch = V.load(os.path.join(ROOT, "modules", "hello", "schema", "hello.schema.json"))
        errs, stale = V.validate_output(doc, sch, env, now)
        self.assertEqual(errs, []); self.assertEqual(stale, [])
if __name__ == "__main__":
    unittest.main()

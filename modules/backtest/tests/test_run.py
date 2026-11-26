import sys, os, json, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import run
class T(unittest.TestCase):
    def test_build_from_committed_results(self):
        res = json.load(open(os.path.join(os.path.dirname(__file__), "..", "results.json")))
        d = run.build(res)
        self.assertEqual(len(d["records"]), 4)
        for r in d["records"]:
            self.assertEqual(r["label"], "simulated"); self.assertIn("support_bounce", r["value"]["strategies"])
if __name__ == "__main__": unittest.main()

import os, sys, unittest
from datetime import datetime, timezone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline")); sys.path.insert(0, os.path.join(ROOT, "modules", "price-spot"))
import validate as V, run as R
NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)

def mk(p):  # {sym: price}
    return {s: (v, 1.5) for s, v in p.items()}
A = mk({"XAUT": 4000.0, "BNB": 600.0, "ETH": 3000.0, "SOL": 150.0})

class T(unittest.TestCase):
    def valid(self, doc):
        env = V.load(os.path.join(ROOT, "schemas", "envelope.schema.json"))
        sch = V.load(os.path.join(ROOT, "modules", "price-spot", "schema", "price-spot.schema.json"))
        errs, stale = V.validate_output(doc, sch, env, NOW)
        self.assertEqual(errs, []); self.assertEqual(stale, [])
    def test_parsers(self):
        self.assertEqual(R.parse_binance([{"symbol": "XAUTUSDT", "lastPrice": "4000.5", "priceChangePercent": "1.2"}, {"symbol": "BTCUSDT", "lastPrice": "1", "priceChangePercent": "0"}]), {"XAUT": (4000.5, 1.2)})
        p = R.parse_okx({"data": [{"instId": "BNB-USDT", "last": "110", "open24h": "100"}, {"instId": "BNB-USDC", "last": "1", "open24h": "1"}]})
        self.assertAlmostEqual(p["BNB"][1], 10.0); self.assertEqual(list(p), ["BNB"])
        self.assertEqual(R.parse_gate([{"currency_pair": "SOL_USDT", "last": "150", "change_percentage": "-2.5"}]), {"SOL": (150.0, -2.5)})
        with self.assertRaises(ValueError): R.parse_binance([{"symbol": "ETHUSDT", "lastPrice": "0", "priceChangePercent": "0"}])
    def test_primary_and_crosscheck_ok(self):
        doc = R.build({"binance": A, "okx": mk({"XAUT": 4004.0, "BNB": 600.0, "ETH": 3000.0, "SOL": 150.0})}, {}, NOW)
        self.valid(doc)
        r = doc["records"][0]
        self.assertEqual(r["value"], 4000.0); self.assertTrue(r["checked_against"]["ok"])
        self.assertAlmostEqual(r["checked_against"]["diff_pct"], 0.1, places=3)
    def test_mismatch_flagged_not_blended(self):
        doc = R.build({"binance": A, "okx": mk({"XAUT": 4100.0, "BNB": 600.0, "ETH": 3000.0, "SOL": 150.0})}, {}, NOW)
        r = doc["records"][0]
        self.assertEqual(r["value"], 4000.0); self.assertFalse(r["checked_against"]["ok"])
    def test_fallback_when_binance_down(self):
        doc = R.build({"okx": A, "gate": A}, {"binance": "HTTPError: 451"}, NOW)
        self.valid(doc)
        self.assertIn("OKX", doc["records"][0]["source"]["name"]); self.assertIn("fallback", doc["records"][0]["source"]["name"])
        self.assertIn("Gate", doc["records"][0]["checked_against"]["source"])
    def test_single_source_has_no_crosscheck(self):
        doc = R.build({"gate": A}, {"binance": "x", "okx": "y"}, NOW)
        self.assertIsNone(doc["records"][0]["checked_against"])
    def test_all_down_fails(self):
        with self.assertRaises(RuntimeError): R.build({}, {"binance": "x"}, NOW)
    def test_missing_symbol_in_primary_uses_next(self):
        part = {k: v for k, v in A.items() if k != "ETH"}
        doc = R.build({"binance": part, "okx": A}, {}, NOW)
        eth = [r for r in doc["records"] if r["id"] == "price.ethusdt"][0]
        self.assertIn("OKX", eth["source"]["name"]); self.assertIsNone(eth["checked_against"])
    def test_collect_survives_a_failing_source(self):
        def bad(): raise OSError("blocked")
        got, errs = R.collect([("binance", bad), ("okx", lambda: A)])
        self.assertEqual(list(got), ["okx"]); self.assertIn("binance", errs)
if __name__ == "__main__":
    unittest.main()

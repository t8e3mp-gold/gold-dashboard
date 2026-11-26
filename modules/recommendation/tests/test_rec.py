import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import run
def Z(mid, lo=None, hi=None, strength=5): return {"lo": lo or mid, "hi": hi or mid, "mid": mid, "strength": strength, "episodes": 4, "bounces": 2, "why": ["x"]}
ZONES = [Z(90, 89, 91), Z(95, strength=9), Z(108, strength=3), Z(112, 111, 113, 8)]
OK_EDGE = {"proven": True, "best": None, "rules_tested": 4, "rules_positive": 1, "min_trades": 100}
NO_EDGE = {"proven": False, "best": {"rule": "a", "trades": 50, "avg_net_pct": -0.1}, "rules_tested": 4, "rules_positive": 0, "min_trades": 100}
class T(unittest.TestCase):
    def test_pick(self):
        pk = run.pick(ZONES, 100)
        self.assertEqual(pk["sup1"]["mid"], 95); self.assertEqual(pk["res1"]["mid"], 108)
        self.assertEqual(pk["sup_strong"]["mid"], 95); self.assertIsNone(pk["res_strong"])   # 108 and 112 are 8% and 12% away: outside the 5% band
    def test_edge_gate(self):
        bt = {"a": {"out_of_sample": {"trades": 300, "win_rate": .5, "avg_net_per_trade_pct": 0.2, "max_drawdown_pct": 10}},
              "b": {"out_of_sample": {"trades": 40, "win_rate": .9, "avg_net_per_trade_pct": 0.9, "max_drawdown_pct": 5}}}
        e = run.edge(bt); self.assertTrue(e["proven"]); self.assertEqual(e["best"]["rule"], "b")   # best is shown even when too few trades to count
        bt["a"]["out_of_sample"]["avg_net_per_trade_pct"] = -0.1; self.assertFalse(run.edge(bt)["proven"])  # small sample never proves an edge
    def test_wait_without_edge(self):
        pk = run.pick(ZONES, 96); s, r = run.decide(96, 1.0, pk, {"x": 1}, {"wait": False, "leak_trap": False}, NO_EDGE)
        self.assertEqual(s, "wait"); self.assertEqual(r[0]["code"], "no_edge")
    def test_buy_watch_needs_edge_forming_near_and_quiet_news(self):
        pk = run.pick(ZONES, 96); q = {"wait": False, "leak_trap": False}
        self.assertEqual(run.decide(96, 1.0, pk, {"x": 1}, q, OK_EDGE)[0], "buy_watch")
        self.assertEqual(run.decide(96, 1.0, pk, None, q, OK_EDGE)[0], "wait")                       # no forming bounce
        self.assertEqual(run.decide(96, 1.0, pk, {"x": 1}, {"wait": True, "leak_trap": False}, OK_EDGE)[0], "wait")   # news window
        self.assertEqual(run.decide(96, 1.0, pk, {"x": 1}, {"wait": False, "leak_trap": True}, OK_EDGE)[0], "wait")   # leak/trap
    def test_sell_watch_near_resistance(self):
        pk = run.pick(ZONES, 107.5); self.assertEqual(run.decide(107.5, 1.0, pk, None, {"wait": False, "leak_trap": False}, OK_EDGE)[0], "sell_watch")
    def test_buy_plan_numbers(self):   # zone 89-91 strong? price 100: sup_strong is 95 (single point). entry zone hi 95, invalidation 95-2=93, risk 2/95
        pk = run.pick(ZONES, 100); p = run.buy_plan(pk, 100, 2.0)
        self.assertAlmostEqual(p["invalidation"], 93.0); self.assertAlmostEqual(p["risk_pct"], round(100 * 2 / 95, 3), 3)
        self.assertAlmostEqual(p["reward_pct"], round(100 * (108 - 95) / 95, 3), 3)
        self.assertAlmostEqual(p["rr_after_fees"], round((13 / 95 - 0.003) / (2 / 95 + 0.003), 2), 2)
    def test_sell_plan_hold_rest(self):
        pk = run.pick(ZONES, 100); p = run.sell_plan(pk, 100, 2.0); self.assertEqual(p["tranches"][0]["mid"], 108); self.assertAlmostEqual(p["hold_rest_above"], 110.0)
if __name__ == "__main__": unittest.main()

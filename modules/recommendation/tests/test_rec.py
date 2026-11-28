import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import run
def Z(mid, lo=None, hi=None, strength=5): return {"lo": lo or mid, "hi": hi or mid, "mid": mid, "strength": strength, "episodes": 4, "bounces": 2, "why": ["x"]}
ZONES = [Z(90, 89, 91), Z(95, strength=9), Z(108, strength=3), Z(112, 111, 113, 8)]
OK_EDGE = {"proven": True, "stage": 98, "stage_rule": None, "best": None, "rules_tested": 4, "rules_positive": 1, "min_trades": 200}
NO_EDGE = {"proven": False, "stage": 0, "stage_rule": None, "best": {"rule": "a", "trades": 50, "avg_net_pct": -0.1}, "rules_tested": 4, "rules_positive": 0, "min_trades": 200}
class T(unittest.TestCase):
    def test_pick(self):
        pk = run.pick(ZONES, 100)
        self.assertEqual(pk["sup1"]["mid"], 95); self.assertEqual(pk["res1"]["mid"], 108)
        self.assertEqual(pk["sup_strong"]["mid"], 95); self.assertIsNone(pk["res_strong"])   # 108 and 112 are 8% and 12% away: outside the 5% band
    def row(self, n, win, tot, dd=10, avg=0.1): return {"out_of_sample": {"trades": n, "win_rate": win, "avg_net_per_trade_pct": avg, "total_net_pct": tot, "max_drawdown_pct": dd}}
    def test_staged_gate(self):
        e = run.edge({"a": self.row(300, .65, 5.0)}); self.assertEqual(e["stage"], 60); self.assertFalse(e["proven"])
        e = run.edge({"a": self.row(300, .91, 5.0)}); self.assertEqual(e["stage"], 90); self.assertFalse(e["proven"])
        e = run.edge({"a": self.row(300, .98, 5.0, dd=19.9)}); self.assertEqual(e["stage"], 98); self.assertTrue(e["proven"])
    def test_stage_trade_minimums(self):    # 60 needs 100; 70, 80, 90, 98 need 200
        self.assertEqual(run.edge({"a": self.row(99, .65, 9.0)})["stage"], 0)
        self.assertEqual(run.edge({"a": self.row(100, .65, 9.0)})["stage"], 60)
        self.assertEqual(run.edge({"a": self.row(199, .99, 9.0)})["stage"], 60)     # 99% win but only 199 trades: clears 60 only
        self.assertEqual(run.edge({"a": self.row(200, .99, 9.0)})["stage"], 98)
        self.assertEqual(run.edge({"a": self.row(150, .75, 9.0)})["stage"], 60)     # 75% on 150 trades: not enough for 70
    def test_stage_needs_positive_total_net(self):
        self.assertEqual(run.edge({"a": self.row(500, .95, 0.0)})["stage"], 0)
        self.assertEqual(run.edge({"a": self.row(500, .95, -1.0)})["stage"], 0)
        self.assertEqual(run.edge({"a": self.row(500, .95, None)})["stage"], 0)      # unknown total never opens a stage
    def test_full_level_needs_drawdown_under_20(self):
        e = run.edge({"a": self.row(500, .99, 9.0, dd=20.0)}); self.assertEqual(e["stage"], 90); self.assertFalse(e["proven"])   # 99% still clears 90, not the full level
    def test_old_100_trade_positive_average_rule_no_longer_opens_anything(self):
        e = run.edge({"a": self.row(150, .55, 3.0, avg=0.2)}); self.assertEqual(e["stage"], 0); self.assertFalse(e["proven"])
    def test_best_rule_shown_even_when_no_stage(self):
        e = run.edge({"a": self.row(50, .9, 1.0, avg=0.9), "b": self.row(300, .4, -5.0, avg=-0.1)}); self.assertEqual(e["best"]["rule"], "a"); self.assertEqual(e["stage"], 0)
    def test_observation_stage_is_not_a_recommendation(self):
        ed = run.edge({"a": self.row(300, .65, 5.0)}); pk = run.pick(ZONES, 96)
        s, r = run.decide(96, 1.0, pk, {"x": 1}, {"wait": False, "leak_trap": False}, ed)
        self.assertEqual(s, "wait"); self.assertEqual(r[0]["code"], "stage_observation"); self.assertEqual(r[0]["stage"], 60)
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

import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import r1
def C(o, h, l, c): return [0, o, h, l, c]
class T(unittest.TestCase):
    def test_tp_hit(self):   # entry open 100, tp 1% = 101, high 101.5 -> exit 101, net = 0.01 - RT
        c = [C(100, 100, 100, 100), C(100, 100, 100, 100), C(100, 101.5, 99.5, 101)]
        tr = r1.simulate(c, [(0, 0)], 0.01, 0.02, 5, 0, 3)
        self.assertAlmostEqual(tr[0], 101 / 100 - 1 - r1.RT, 9)
    def test_stop_first_when_both(self):   # same candle touches stop and target -> stop (conservative)
        c = [C(100, 100, 100, 100), C(100, 100, 100, 100), C(100, 102, 97, 100)]
        tr = r1.simulate(c, [(0, 0)], 0.01, 0.02, 5, 0, 3)
        self.assertAlmostEqual(tr[0], 98 / 100 - 1 - r1.RT, 9)
    def test_time_stop(self):
        c = [C(100, 100, 100, 100)] + [C(100, 100.2, 99.9, 100.1)] * 4
        tr = r1.simulate(c, [(0, 0)], 0.05, 0.05, 2, 0, 5)
        self.assertAlmostEqual(tr[0], 100.1 / 100 - 1 - r1.RT, 9)
    def test_no_lookahead(self):  # a swing low at i is unknown before i+K
        c = [C(10, 11, 10, 10.5)] * 20; c[10] = C(10, 11, 5, 10.5)
        self.assertEqual(r1.swing_low_idx(c), [10])
        sg = r1.signals(c, 1)
        self.assertTrue(all(t >= 10 + r1.K for t, _ in sg))
    def test_wilson(self):
        lo, hi = r1.wilson(50, 100); self.assertLess(lo, 0.5); self.assertGreater(hi, 0.5)
    def test_tranche(self):  # entry 100, tp 2% -> half at 101, stop to entry, rest at 102
        c = [C(100, 100, 100, 100), C(100, 100, 100, 100), C(100, 101.2, 99.9, 101), C(101, 102.5, 100.5, 102)]
        tr = r1.simulate(c, [(0, 0)], 0.02, 0.05, 5, 0, 4, True)
        self.assertAlmostEqual(tr[0], 0.5 * 0.01 + 0.5 * 0.02 - r1.RT, 9)
    def test_tranche_breakeven_stop(self):  # half at +1%, then price falls to entry -> rest exits at entry
        c = [C(100, 100, 100, 100), C(100, 100, 100, 100), C(100, 101.2, 99.9, 100.5), C(100.5, 100.6, 99.0, 99.5)]
        tr = r1.simulate(c, [(0, 0)], 0.02, 0.05, 5, 0, 4, True)
        self.assertAlmostEqual(tr[0], 0.5 * 0.01 + 0.5 * 0.0 - r1.RT, 9)
    def test_rsi_all_up_is_100(self):
        c = [C(i, i, i, i + 1) for i in range(1, 40)]
        self.assertEqual(r1.rsi_series(c)[-1], 100.0)
class R2(unittest.TestCase):
    def cc(self, i, o, h, l, c, v=1.0, tb=0.5): return [i * 3600000, o, h, l, c, v, tb]
    def test_taker_cross_up_only_once(self):   # shares: .40 .40 .60 .60 -> crosses up through .55 at t=2 only
        c = [self.cc(i, 1, 1, 1, 1, 10, b) for i, b in enumerate([4, 4, 6, 6])]
        self.assertEqual(r1.sig_taker(c, 1, 0.55), [(2, 0)])
    def test_taker_uses_window_sum_not_average_of_shares(self):  # t=2: (4+0.2)/12=.35; t=3: (0.2+9.5)/12=.808 (average of shares would be .525)
        c = [self.cc(0, 1, 1, 1, 1, 10, 4.0), self.cc(1, 1, 1, 1, 1, 10, 4.0), self.cc(2, 1, 1, 1, 1, 2, 0.2), self.cc(3, 1, 1, 1, 1, 10, 9.5)]
        self.assertEqual(r1.sig_taker(c, 2, 0.8), [(3, 0)])
    def test_poc_excludes_current_candle_and_finds_peak(self):
        win = 20; c = [self.cc(i, 100, 101, 99, 100, 1.0) for i in range(win)]
        c[5][5] = 100.0                                  # all the volume sits around typical price 100
        c.append(self.cc(win, 100, 200, 50, 90, 1e9))     # current candle must not move its own POC
        d = r1.poc_dist(c, win=win, bins=40)
        self.assertIsNone(d[win - 1]); self.assertAlmostEqual(d[win], 90 / 100.0 - 1, delta=0.02)
    def test_poc_signal_is_recovery_through_threshold(self):
        win = 20; c = [self.cc(i, 100, 101, 99, 100, 1.0) for i in range(win)]
        for i, cl in enumerate([95, 95, 99.9]): c.append(self.cc(win + i, cl, cl + .1, cl - .1, cl, 1.0))
        sg = r1.sig_poc(c, 0.02, win); self.assertEqual([t for t, _ in sg], [win + 2])
    def test_session_signal_is_candle_before_the_open_hour(self):
        c = [self.cc(i, 1, 1, 1, 1) for i in range(48)]
        self.assertEqual([t for t, _ in r1.sig_session(c, 8)], [7, 31])
        self.assertEqual([t for t, _ in r1.sig_session(c, 0)], [23, 47])
    def test_new_rules_registered(self):
        for k in ("taker_flow", "poc_recover", "session_open"): self.assertIn(k, r1.STRATS)
if __name__ == "__main__": unittest.main()

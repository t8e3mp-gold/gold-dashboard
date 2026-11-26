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
if __name__ == "__main__": unittest.main()

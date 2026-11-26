"""R1b: two TREND families (no mean reversion) under the SAME harness, costs and 60/40 split as r1.py. SIMULATED, research only.
Donchian breakout (close above the highest high of N candles, N=24 or 72) and EMA cross-up (fast over slow, 12/26 or 24/72)."""
import json, sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r1
def sig_donchian(c, n):
    return [(t, 0) for t in range(n + 1, len(c)) if c[t][4] > max(x[2] for x in c[t - n:t]) and c[t - 1][4] <= max(x[2] for x in c[t - 1 - n:t - 1])] if len(c) > n + 2 else []
def ema(vals, n):
    k = 2 / (n + 1); out = [vals[0]]
    for v in vals[1:]: out.append(out[-1] + k * (v - out[-1]))
    return out
def sig_ema(c, f, s):
    cl = [x[4] for x in c]; a, b = ema(cl, f), ema(cl, s)
    return [(t, 0) for t in range(s, len(c)) if a[t] > b[t] and a[t - 1] <= b[t - 1]]
r1.STRATS = {
    "donchian_breakout": {"name_ar": "اختراق أعلى سعر", "params": [{"n": 24}, {"n": 72}], "gen": lambda c, p: sig_donchian(c, p["n"])},
    "ema_cross": {"name_ar": "تقاطع متوسطين", "params": [{"f": 12, "s": 26}, {"f": 24, "s": 72}], "gen": lambda c, p: sig_ema(c, p["f"], p["s"])},
}
if __name__ == "__main__":
    two_years = int((time.time() - 2 * 365 * 86400) * 1000); out = {}
    for s in ["XAUTUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]:
        c = r1.fetch(s, 0 if s.startswith("XAUT") else two_years); out[s] = r1.run_symbol(s, c)["strategies"]
        for k, v in out[s].items():
            o = v.get("out_of_sample") or {}; b = v.get("baseline_oos_same_exits") or {}
            print(s, k, "oos_trades", o.get("trades"), "avg_net%", o.get("avg_net_per_trade_pct"), "baseline%", b.get("avg_net_per_trade_pct"), "win", o.get("win_rate"), "dd%", o.get("max_drawdown_pct"))
    json.dump({"label": "simulated", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "symbols": out}, open(os.environ.get("R1B_OUT", "/tmp/r1b.json"), "w"), indent=1)

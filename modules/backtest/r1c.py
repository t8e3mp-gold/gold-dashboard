"""R1c: two NEW families under the SAME harness, costs and 60/40 split as r1.py. SIMULATED, research only.
Bollinger squeeze breakout (bandwidth in the lowest 20% of last 120 candles, then close above upper band, n=20)
and volume-spike momentum (volume > k x 24h mean, green candle, k=3 or 5)."""
import json, sys, time, os, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r1
def sig_squeeze(c, n=20):
    cl = [x[4] for x in c]; bw = [None] * len(c); up = [None] * len(c)
    for t in range(n, len(c)):
        w = cl[t - n:t]; m = sum(w) / n; sd = statistics.pstdev(w)
        bw[t] = 4 * sd / m if m else None; up[t] = m + 2 * sd
    out = []
    for t in range(n + 120, len(c)):
        hist = sorted(b for b in bw[t - 120:t] if b is not None)
        if hist and bw[t - 1] is not None and bw[t - 1] <= hist[len(hist) // 5] and cl[t] > up[t] and cl[t - 1] <= up[t - 1]:
            out.append((t, 0))
    return out
def sig_volspike(c, k):
    v = [float(x[5]) for x in c]
    return [(t, 0) for t in range(25, len(c)) if v[t] > k * (sum(v[t - 24:t]) / 24) and c[t][4] > c[t][1]]
def fetch_v(sym, start_ms=0, retries=3):
    import urllib.request
    out, t = [], start_ms
    while True:
        for a in range(retries):
            try:
                with urllib.request.urlopen(r1.URL % (sym, t), timeout=30) as r: rows = json.load(r); break
            except Exception:
                if a == retries - 1: raise
                time.sleep(2)
        if not rows: break
        out += [[r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])] for r in rows]
        t = rows[-1][0] + 3600000
        if len(rows) < 1000: break
    return out
r1.STRATS = {
    "bb_squeeze": {"name_ar": "اختراق بعد انضغاط", "params": [{"n": 20}], "gen": lambda c, p: sig_squeeze(c, p["n"])},
    "vol_spike": {"name_ar": "قفزة حجم", "params": [{"k": 3}, {"k": 5}], "gen": lambda c, p: sig_volspike(c, p["k"])},
}
if __name__ == "__main__":
    two_years = int((time.time() - 2 * 365 * 86400) * 1000); out = {}
    for s in ["XAUTUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]:
        c = fetch_v(s, 0 if s.startswith("XAUT") else two_years); out[s] = r1.run_symbol(s, c)["strategies"]
        for k, v in out[s].items():
            o = v.get("out_of_sample") or {}; b = v.get("baseline_oos_same_exits") or {}
            print(s, k, "oos_trades", o.get("trades"), "avg_net%", o.get("avg_net_per_trade_pct"), "baseline%", b.get("avg_net_per_trade_pct"), "win", o.get("win_rate"), "dd%", o.get("max_drawdown_pct"))
    json.dump({"label": "simulated", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "symbols": out}, open(os.environ.get("R1C_OUT", "/tmp/r1c.json"), "w"), indent=1)

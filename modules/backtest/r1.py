"""R1 backtest harness (research only, demo money, spot, long-only). Everything here is SIMULATED on past data.
Rule under test ("support bounce"): a candle wicks into a confirmed support zone (swing low, fractal k=5) and closes back above it.
Entry = next candle open. Exit = take-profit, stop, or time stop. Fees and slippage are charged. One position at a time.
No look-ahead: a swing low at candle i is only known from candle i+K. Parameters are picked on the first 60% of time only and
reported on the last 40% (out-of-sample). The baseline enters whenever flat, with the same exits, to show whether levels add anything."""
import json, math, sys, time, urllib.request
K, LOOKBACK, MERGE = 5, 300, 0.002
FEE, SLIP = 0.001, 0.0005          # per side
RT = 2 * (FEE + SLIP)              # round trip cost fraction
URL = "https://data-api.binance.vision/api/v3/klines?symbol=%s&interval=1h&limit=1000&startTime=%d"

def fetch(sym, start_ms=0, retries=3):
    out, t = [], start_ms
    while True:
        for a in range(retries):
            try:
                with urllib.request.urlopen(URL % (sym, t), timeout=30) as r: rows = json.load(r); break
            except Exception:
                if a == retries - 1: raise
                time.sleep(2)
        if not rows: break
        out += [[r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4])] for r in rows]
        t = rows[-1][0] + 3600000
        if len(rows) < 1000: break
    now = int(time.time() * 1000)
    return [c for c in out if c[0] + 3600000 <= now]   # closed candles only

def swing_low_idx(c):
    """Indices i where low[i] is strictly below the K lows on each side. Known only at i+K."""
    res = []
    for i in range(K, len(c) - K):
        l = c[i][3]
        if all(l < c[i - j][3] and l < c[i + j][3] for j in range(1, K + 1)): res.append(i)
    return res

def signals(c, min_touch):
    """Indices t (candle close) where entry is triggered, using only information up to t."""
    sl = swing_low_idx(c); out = []; p = 0; known = []
    for t in range(len(c)):
        while p < len(sl) and sl[p] + K <= t: known.append(sl[p]); p += 1
        act = [c[i][3] for i in known if t - LOOKBACK <= i <= t - K]
        if not act: continue
        act.sort(); zones = []
        for x in act:
            if zones and x <= zones[-1][1] * (1 + MERGE): zones[-1][1] = x; zones[-1][2] += 1
            else: zones.append([x, x, 1])
        cl, lo = c[t][4], c[t][3]
        for zlo, zhi, n in zones:
            if n >= min_touch and lo <= zhi * 1.001 and cl > zhi * 1.001 and lo >= zlo * 0.995: out.append((t, zlo)); break
    return out

def simulate(c, sigs, tp, sl_pct, hold, lo_i, hi_i):
    """sigs: list of (t, zone_lo) or None for baseline (enter whenever flat). Returns list of net returns."""
    trades = []; t = lo_i; sg = {s[0]: s for s in sigs} if sigs is not None else None
    while t < hi_i - 1:
        if sg is not None and t not in sg: t += 1; continue
        e = t + 1; entry = c[e][1]; stop = entry * (1 - sl_pct); target = entry * (1 + tp); exit_p = None; x = e
        for x in range(e, min(e + hold, hi_i)):
            o, h, l, cl = c[x][1:5]
            if l <= stop: exit_p = min(o, stop); break
            if h >= target: exit_p = max(o, target) if o >= target else target; break
        if exit_p is None: exit_p = c[x][4]
        trades.append(exit_p / entry - 1 - RT); t = x + 1
    return trades

def wilson(w, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = w / n; d = 1 + z * z / n; m = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(m - h, 4), round(m + h, 4))

def stats(tr):
    n = len(tr)
    if n == 0: return {"trades": 0}
    w = sum(1 for x in tr if x > 0); eq = 1.0; peak = 1.0; dd = 0.0
    for x in tr: eq *= 1 + x; peak = max(peak, eq); dd = max(dd, 1 - eq / peak)
    return {"trades": n, "win_rate": round(w / n, 4), "win_rate_ci95": wilson(w, n), "avg_net_per_trade_pct": round(100 * sum(tr) / n, 4),
            "total_net_pct": round(100 * (eq - 1), 2), "max_drawdown_pct": round(100 * dd, 2)}

GRID = [(tp, sl, 48, mt) for tp in (0.005, 0.01, 0.015, 0.02) for sl in (0.01, 0.02, 0.04) for mt in (1, 2)]

def run_symbol(sym, c, split=0.6):
    cut = int(len(c) * split); res = {"candles": len(c), "from": c[0][0], "to": c[-1][0], "split_index": cut, "grid": []}
    sig_cache = {mt: signals(c, mt) for mt in (1, 2)}
    best = None
    for tp, sl, hold, mt in GRID:
        ins = [s for s in sig_cache[mt] if s[0] < cut]
        tr = simulate(c, ins, tp, sl, hold, 0, cut); st = stats(tr); row = {"tp": tp, "sl": sl, "min_touch": mt, "in_sample": st}
        res["grid"].append(row)
        if st["trades"] >= 20 and (best is None or st["avg_net_per_trade_pct"] > best[1]["in_sample"]["avg_net_per_trade_pct"]): best = (None, row)
    res["grid_size"] = len(GRID)
    if best:
        row = best[1]; tp, sl, mt = row["tp"], row["sl"], row["min_touch"]
        oos_sig = [s for s in sig_cache[mt] if s[0] >= cut]
        res["chosen_in_sample"] = {k: row[k] for k in ("tp", "sl", "min_touch", "in_sample")}
        res["out_of_sample_levels"] = stats(simulate(c, oos_sig, tp, sl, 48, cut, len(c)))
        res["out_of_sample_baseline_same_exits"] = stats(simulate(c, None, tp, sl, 48, cut, len(c)))
        res["in_sample_baseline_same_exits"] = stats(simulate(c, None, tp, sl, 48, 0, cut))
    else: res["chosen_in_sample"] = None
    return res

if __name__ == "__main__":
    syms = sys.argv[1:] or ["XAUTUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]; two_years = int((time.time() - 2 * 365 * 86400) * 1000)
    out = {"label": "simulated", "rule": "support bounce, long only, spot", "fee_per_side": FEE, "slippage_per_side": SLIP, "split": 0.6,
           "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "source": "https://data-api.binance.vision/api/v3/klines", "symbols": {}}
    for s in syms:
        c = fetch(s, 0 if s.startswith("XAUT") else two_years); out["symbols"][s] = run_symbol(s, c); print(s, len(c), file=sys.stderr)
    json.dump(out, open("/tmp/hist/r1.json", "w"), indent=1)

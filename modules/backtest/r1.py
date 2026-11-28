"""R1 backtest harness (research only, demo money, spot, long-only). Everything here is SIMULATED on past data.
Rule under test ("support bounce"): a candle wicks into a confirmed support zone (swing low, fractal k=5) and closes back above it.
Entry = next candle open. Exit = take-profit, stop, or time stop. Fees and slippage are charged. One position at a time.
No look-ahead: a swing low at candle i is only known from candle i+K. Parameters are picked on the first 60% of time only and
reported on the last 40% (out-of-sample). The baseline enters whenever flat, with the same exits, to show whether levels add anything."""
import json, math, os, sys, time, urllib.request
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
        out += [[r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]), float(r[9])] for r in rows]   # [5]=volume, [6]=taker buy base volume
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

def simulate(c, sigs, tp, sl_pct, hold, lo_i, hi_i, tranche=False, info=None):
    """sigs: list of (t, zone_lo) or None for baseline (enter whenever flat). tranche=True: sell half at tp/2, stop of the rest moves to entry,
    sell the rest at tp. info (optional dict) counts how trades ended: target, stop, time (48h time stop, i.e. stuck), open_end (still open when the data ends, marked at the last close). Returns list of net returns (fees and slippage charged on each sold part). Same-candle stop and target: stop counts."""
    trades = []; t = lo_i; sg = {s[0]: s for s in sigs} if sigs is not None else None
    while t < hi_i - 1:
        if sg is not None and t not in sg: t += 1; continue
        e = t + 1; entry = c[e][1]; stop = entry * (1 - sl_pct); t1 = entry * (1 + tp / 2); t2 = entry * (1 + tp)
        got = 0.0; left = 1.0; x = e; closed = False; tag = None
        for x in range(e, min(e + hold, hi_i)):
            o, h, l, cl = c[x][1:5]
            if l <= stop: got += left * (min(o, stop) / entry - 1); left = 0; closed = True; tag = "stop"; break
            if tranche and left == 1.0 and h >= t1:
                got += 0.5 * (max(o, t1) / entry - 1); left = 0.5; stop = max(stop, entry)
            if h >= t2:
                got += left * (max(o, t2) / entry - 1); left = 0; closed = True; tag = "target"; break
        if not closed:
            got += left * (c[x][4] / entry - 1); tag = "time" if e + hold <= hi_i else "open_end"
        if info is not None: info[tag] = info.get(tag, 0) + 1
        trades.append(got - RT); t = x + 1
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


def rsi_series(c, n=14):
    r = [None] * len(c); g = l = 0.0
    for i in range(1, len(c)):
        d = c[i][4] - c[i - 1][4]; up, dn = max(d, 0), max(-d, 0)
        if i <= n: g += up / n; l += dn / n
        else: g = (g * (n - 1) + up) / n; l = (l * (n - 1) + dn) / n
        if i >= n: r[i] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    return r

def sig_rsi(c, thr):
    r = rsi_series(c); return [(t, 0) for t in range(1, len(c)) if r[t - 1] is not None and r[t] is not None and r[t - 1] < thr <= r[t]]

def sig_boll(c, n=20, k=2.0):
    out = []; prev_below = False
    for t in range(n, len(c)):
        w = [x[4] for x in c[t - n + 1:t + 1]]; m = sum(w) / n; sd = (sum((x - m) ** 2 for x in w) / n) ** 0.5
        below = c[t][4] < m - k * sd
        if prev_below and not below and c[t][4] < m: out.append((t, 0))
        prev_below = below
    return out

def sig_support(c, mt): return signals(c, mt)

# ---- R2 (Nov 28 2026): three alternatives to RSI. Same harness, costs, 60/40 split and exits. SIMULATED. Columns: c[5]=volume, c[6]=taker buy volume.
def sig_taker(c, n, thr):
    """Taker-buy share of volume over the last n candles crosses up through thr (0.5 = balanced). Uses candles up to t only."""
    out = []; prev = None
    for t in range(n, len(c)):
        v = sum(x[5] for x in c[t - n + 1:t + 1]); b = sum(x[6] for x in c[t - n + 1:t + 1])
        cur = b / v if v > 0 else None
        if prev is not None and cur is not None and prev < thr <= cur: out.append((t, 0))
        prev = cur
    return out

_POC = {}
def poc_dist(c, win=168, bins=40):
    """Distance of each close from the volume-profile POC of the previous win candles (candle t itself excluded). None if unknown."""
    key = (len(c), c[0][0], c[-1][0], c[len(c) // 2][4], c[-1][4], win, bins)
    if key in _POC: return _POC[key]
    out = [None] * len(c)
    for t in range(win, len(c)):
        w = c[t - win:t]; lo = min(x[3] for x in w); hi = max(x[2] for x in w)
        if hi <= lo: continue
        step = (hi - lo) / bins; vol = [0.0] * bins
        for x in w:
            i = min(bins - 1, int(((x[2] + x[3] + x[4]) / 3 - lo) / step)); vol[i] += x[5]
        j = max(range(bins), key=lambda i: vol[i]); poc = lo + (j + 0.5) * step
        out[t] = c[t][4] / poc - 1
    _POC[key] = out; return out

def sig_poc(c, d, win=168):
    """Close recovers up through (POC - d), i.e. was more than d below the 7-day POC on the previous candle and no longer is."""
    x = poc_dist(c, win)
    return [(t, 0) for t in range(1, len(c)) if x[t - 1] is not None and x[t] is not None and x[t - 1] < -d <= x[t]]

def sig_session(c, h):
    """Entry at the open of the UTC hour h every day (signal = the candle before it closes). Tests whether a time of day adds anything over the baseline."""
    return [(t, 0) for t in range(len(c)) if (c[t][0] // 3600000) % 24 == (h - 1) % 24]

STRATS = {
    "support_bounce": {"name_ar": "ارتداد من دعم", "params": [{"mt": m} for m in (1, 2)], "gen": lambda c, p: signals(c, p["mt"])},
    "strict_support": {"name_ar": "دعم مشدد (3 لمسات فأكثر)", "params": [{"mt": 3}], "gen": lambda c, p: signals(c, p["mt"])},
    "rsi_oversold": {"name_ar": "RSI يعود فوق حد التشبع", "params": [{"thr": t} for t in (25, 30, 35)], "gen": lambda c, p: sig_rsi(c, p["thr"])},
    "bollinger_reclaim": {"name_ar": "عودة داخل نطاق بولينجر", "params": [{}], "gen": lambda c, p: sig_boll(c)},
    "taker_flow": {"name_ar": "حصة المشترين في الحجم ترتفع (تدفق)", "params": [{"n": 6, "thr": 0.52}, {"n": 6, "thr": 0.55}, {"n": 24, "thr": 0.52}], "gen": lambda c, p: sig_taker(c, p["n"], p["thr"])},
    "poc_recover": {"name_ar": "عودة من تحت أكثر سعر تداولا 7 أيام (POC)", "params": [{"d": 0.005}, {"d": 0.01}, {"d": 0.02}], "gen": lambda c, p: sig_poc(c, p["d"])},
    "session_open": {"name_ar": "دخول عند فتح جلسة (توقيت UTC)", "params": [{"h": 0}, {"h": 8}, {"h": 14}], "gen": lambda c, p: sig_session(c, p["h"])},
}
EXITS = [(tp, sl, 48, tr) for tp in (0.005, 0.01, 0.015, 0.02) for sl in (0.01, 0.02, 0.04) for tr in (False, True)]

def run_strategy(c, strat, split=0.6):
    cut = int(len(c) * split); cands = []
    for p in strat["params"]:
        sigs = strat["gen"](c, p); ins = [x for x in sigs if x[0] < cut]
        for tp, sl, hold, tr in EXITS:
            st = stats(simulate(c, ins, tp, sl, hold, 0, cut, tr)); cands.append((p, sigs, tp, sl, hold, tr, st))
    ok = [x for x in cands if x[6]["trades"] >= 20]
    res = {"tested_in_sample": len(cands)}
    if not ok: res["chosen"] = None; return res
    p, sigs, tp, sl, hold, tr, st = max(ok, key=lambda x: x[6]["avg_net_per_trade_pct"])
    oos = [x for x in sigs if x[0] >= cut]
    res["chosen"] = {"params": p, "tp": tp, "sl": sl, "tranche": tr, "in_sample": st}
    ex = {}; res["out_of_sample"] = stats(simulate(c, oos, tp, sl, hold, cut, len(c), tr, ex)); res["out_of_sample"]["exits"] = {k: ex.get(k, 0) for k in ("target", "stop", "time", "open_end")}
    res["baseline_oos_same_exits"] = stats(simulate(c, None, tp, sl, hold, cut, len(c), tr))
    return res

def run_symbol(sym, c):
    return {"candles": len(c), "from": c[0][0], "to": c[-1][0], "strategies": {k: run_strategy(c, v) for k, v in STRATS.items()}}

if __name__ == "__main__":
    syms = sys.argv[1:] or ["XAUTUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]; two_years = int((time.time() - 2 * 365 * 86400) * 1000)
    out = {"label": "simulated", "fee_per_side": FEE, "slippage_per_side": SLIP, "split": 0.6, "stop_rule": "same candle touching stop and target counts as stop",
           "strategies": {k: v["name_ar"] for k, v in STRATS.items()}, "exit_grid": "take-profit 0.5/1/1.5/2%, stop 1/2/4%, single or two-tranche (half at half target, stop to entry), 48h time stop",
           "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "source": "https://data-api.binance.vision/api/v3/klines", "symbols": {}}
    for s in syms:
        c = fetch(s, 0 if s.startswith("XAUT") else two_years); out["symbols"][s] = run_symbol(s, c); print(s, len(c), file=sys.stderr)
    json.dump(out, open(os.environ.get("R1_OUT", "/tmp/hist/r2.json"), "w"), indent=1)

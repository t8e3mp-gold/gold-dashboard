"""intent: honest proxies for trader behaviour, all labelled HYPOTHESIS. They describe trades, not people.
1) trade-size distribution and large-trade share for XAUT from raw aggTrades over the last 6 closed hours.
   Large trade = quantity at or above the 99th percentile of that window's trade sizes (an arbitrary cut-off, stated on the card).
2) divergence between price and net taker delta over the last 6 closed hours, for all 4 symbols, together with how often the same
   signal appeared before in the 300-hour history and what price did next (sample size and 95% interval always reported).
Plan A: aggTrades for XAUT. Plan B: if aggTrades fails, XAUT trade-size record is built from candle trade counts is NOT possible here, so the
record is omitted by failing the module (last good file stays, flagged stale). Plan C: the page shows delta and volume profile only."""
import json, math, os, urllib.request
from datetime import datetime, timezone

SYMS = ["XAUT", "BNB", "ETH", "SOL"]
H = 3600_000
HOURS = 6
MAX_PAGES = 120
BASE = "https://data-api.binance.vision/api/v3/aggTrades"
MIN_CHG_PCT, MIN_DELTA_PCT = 0.3, 5.0

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "gold-dashboard-refresh"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def fetch_trades(sym, t0, t1, get=get):
    out, url = [], "%s?symbol=%sUSDT&startTime=%d&endTime=%d&limit=1000" % (BASE, sym, t0, t1 - 1)
    for _ in range(MAX_PAGES):
        rows = get(url)
        out += [(int(t["T"]), float(t["q"]), not t["m"]) for t in rows if int(t["T"]) < t1]   # (time, qty, taker_is_buyer)
        if len(rows) < 1000 or int(rows[-1]["T"]) >= t1: return out
        url = "%s?symbol=%sUSDT&fromId=%d&limit=1000" % (BASE, sym, int(rows[-1]["a"]) + 1)
    raise RuntimeError("too many trade pages")

def pct(sorted_q, p):
    k = (len(sorted_q) - 1) * p / 100.0; f = int(math.floor(k)); c = min(f + 1, len(sorted_q) - 1)
    return sorted_q[f] + (sorted_q[c] - sorted_q[f]) * (k - f)

def size_record(trades, t0, hours):
    if len(trades) < 500: raise ValueError("only %d trades" % len(trades))
    q = sorted(t[1] for t in trades); thr = pct(q, 99)
    rows = []
    for h in range(hours):
        a, b = t0 + h * H, t0 + (h + 1) * H
        tr = [t for t in trades if a <= t[0] < b]
        vol = sum(t[1] for t in tr); lg = [t for t in tr if t[1] >= thr]
        lb = sum(t[1] for t in lg if t[2]); ls = sum(t[1] for t in lg if not t[2])
        rows.append([a, len(tr), round(vol, 6), round(vol / len(tr), 6) if tr else 0.0, len(lg), round(lb, 6), round(ls, 6),
                     round((lb + ls) / vol * 100, 3) if vol else 0.0])
    tot = sum(t[1] for t in trades); lgall = [t for t in trades if t[1] >= thr]
    lbv = sum(t[1] for t in lgall if t[2]); lsv = sum(t[1] for t in lgall if not t[2])
    st = {"sample_trades": len(trades), "window_hours": hours, "p50": round(pct(q, 50), 6), "p90": round(pct(q, 90), 6), "p99_threshold": round(thr, 6),
          "mean_size": round(tot / len(trades), 6), "large_trades": len(lgall), "large_volume_share_pct": round((lbv + lsv) / tot * 100, 3),
          "large_net_buy": round(lbv - lsv, 6), "large_buy_share_pct": round(lbv / (lbv + lsv) * 100, 2) if lbv + lsv else None,
          "definition": "large = trade size at or above the 99th percentile of this window's trades (arbitrary cut-off); size is not a person",
          "columns": "[hour_open_ms, trades, volume, avg_size, large_trades, large_buy_vol, large_sell_vol, large_share_pct]"}
    return rows, st

def wilson(k, n, z=1.96):
    if n == 0: return None, None
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round((c - m) / d * 100, 1), round((c + m) / d * 100, 1)

def sign(x): return (x > 0) - (x < 0)

def window_stat(op, cl, dl, vo, a, b):
    chg = (cl[b] / op[a] - 1) * 100; v = sum(vo[a:b + 1]); dp = sum(dl[a:b + 1]) / v * 100 if v else 0.0
    return chg, dp

def divergence(kl, fl, hours=HOURS):
    """kl: klines rows [t,o,h,l,c,v]; fl: flow rows [t,vol,buy,sell,delta,cvd]. Aligned on open time."""
    fm = {r[0]: r for r in fl}; rows = [(r, fm[r[0]]) for r in kl if r[0] in fm]
    for i in range(1, len(rows)):
        if rows[i][0][0] - rows[i - 1][0][0] != H: rows = rows[i:]; break
    op = [r[0][1] for r in rows]; cl = [r[0][4] for r in rows]; dl = [r[1][4] for r in rows]; vo = [r[1][1] for r in rows]
    n = len(rows)
    if n < hours * 10: raise ValueError("history too short: %d hours" % n)
    chg, dp = window_stat(op, cl, dl, vo, n - hours, n - 1)
    div = sign(chg) != sign(dp) and abs(chg) >= MIN_CHG_PCT and abs(dp) >= MIN_DELTA_PCT
    state = "no divergence"
    if div: state = "price up while net taker flow is selling" if chg > 0 else "price down while net taker flow is buying"
    ev, agree, i = 0, 0, n - 1 - hours            # past windows, non-overlapping, stepping back by `hours`
    while i - hours + 1 >= 0:
        c, d = window_stat(op, cl, dl, vo, i - hours + 1, i)
        if sign(c) != sign(d) and abs(c) >= MIN_CHG_PCT and abs(d) >= MIN_DELTA_PCT and i + hours <= n - 1:
            nxt = (cl[i + hours] / cl[i] - 1) * 100
            ev += 1; agree += (sign(nxt) == sign(d))
        i -= hours
    lo, hi = wilson(agree, ev)
    hist = {"past_events": ev, "next_window_followed_delta_direction": agree, "hit_rate_pct": round(agree / ev * 100, 1) if ev else None,
            "ci95_low_pct": lo, "ci95_high_pct": hi, "coin_flip_pct": 50,
            "reading": "no evidence" if ev == 0 or (lo is not None and lo <= 50 <= hi) else "interval excludes 50%, still not proven",
            "history_hours": n, "windows": "non-overlapping %d-hour windows" % hours}
    return {"price_change_pct": round(chg, 3), "net_delta_pct_of_volume": round(dp, 3), "state": state, "window_hours": hours}, hist

def build(fetch, klines_doc, flow_doc, now):
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ"); t1 = (int(now.timestamp() * 1000) // H) * H; t0 = t1 - HOURS * H
    km = {r["id"]: r for r in klines_doc["records"]}; fm = {r["id"]: r for r in flow_doc["records"]}
    base = {"source": {"name": "Binance public data mirror", "url": BASE}, "fetched_at": ts, "label": "hypothesis", "max_age_hours": 8, "checked_against": None}
    recs = []
    rows, st = size_record(fetch("XAUT", t0, t1), t0, HOURS)
    recs.append(dict(base, id="intent.xautusdt.trade-size", value=rows, unit="intent-size [hour_open_ms, trades, volume, avg_size, large_trades, large_buy_vol, large_sell_vol, large_share_pct]",
                     stats=st, title_ar="حجم الصفقات والصفقات الكبيرة XAUT (فرضية)"))
    for s in SYMS:
        k = km["kline.%susdt.1h" % s.lower()]; f = fm["flow.%susdt.1h" % s.lower()]
        v, hist = divergence(k["value"], f["value"])
        recs.append(dict(base, id="intent.%susdt.divergence" % s.lower(), value=v, unit="divergence", stats=hist,
                         source={"name": "klines and flow modules (Binance)", "url": "https://data-api.binance.vision/api/v3/klines"},
                         title_ar="تباعد السعر والدلتا %s (فرضية)" % s))
    return {"meta": {"module": "intent", "version": "1.0.0", "window": [t0, t1]}, "records": recs}

def main():
    d = os.environ["DATA_DIR"]
    kd = json.load(open(os.path.join(d, "klines.json"), encoding="utf-8")); fd = json.load(open(os.path.join(d, "flow.json"), encoding="utf-8"))
    doc = build(fetch_trades, kd, fd, datetime.now(timezone.utc))
    with open(os.path.join(os.environ["OUT_DIR"], "intent.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()

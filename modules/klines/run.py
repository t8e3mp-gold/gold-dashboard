"""klines: last 300 CLOSED candles, 1h and 1d, for XAUT, BNB, ETH, SOL (vs USDT).
Candle row: [open_time_ms, open, high, low, close, base_volume]. The still-forming candle is never kept
(no look-ahead). Plan A Binance public mirror, Plan B OKX, Plan C Gate.io. Cross-check: the same closes
from the next source over the last 24 candles."""
import json, os, urllib.request, statistics
from datetime import datetime, timezone

SYMS = ["XAUT", "BNB", "ETH", "SOL"]
TFS = {"1h": 3600_000, "1d": 86400_000}
N = 300
MAX_DIFF_PCT = 0.5   # limit on the MEDIAN close difference over the last 24 candles
SRC = {"binance": ("Binance public data mirror", "https://data-api.binance.vision/api/v3/klines"),
       "okx": ("OKX spot candles", "https://www.okx.com/api/v5/market/candles"),
       "gate": ("Gate.io spot candlesticks", "https://api.gateio.ws/api/v4/spot/candlesticks")}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "gold-dashboard-refresh"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def p_binance(rows, now_ms):
    out = []
    for r in rows:
        if int(r[6]) < now_ms:   # close time already passed = candle is closed
            out.append([int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])])
    return out

def p_okx(d, now_ms, ms):
    out = []
    for r in d["data"]:
        if r[8] == "1" and int(r[0]) + ms <= now_ms:
            out.append([int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])])
    return sorted(out)

def p_gate(rows, now_ms, ms):
    out = []
    for r in rows:
        t = int(r[0]) * 1000
        if t + ms <= now_ms:   # [ts, quote_vol, close, high, low, open, base_vol, closed]
            out.append([t, float(r[5]), float(r[3]), float(r[4]), float(r[2]), float(r[6])])
    return sorted(out)

def fetch(src, sym, tf, now_ms, get=get):
    ms = TFS[tf]
    if src == "binance":
        return p_binance(get("%s?symbol=%sUSDT&interval=%s&limit=%d" % (SRC[src][1], sym, tf, N + 1)), now_ms)
    if src == "okx":
        return p_okx(get("%s?instId=%s-USDT&bar=%s&limit=%d" % (SRC[src][1], sym, "1H" if tf == "1h" else "1Dutc", N + 1)), now_ms, ms)
    return p_gate(get("%s?currency_pair=%s_USDT&interval=%s&limit=%d" % (SRC[src][1], sym, tf, N + 1)), now_ms, ms)

def check_series(c, ms, now_ms):
    """Returns error text or None."""
    if len(c) < 200: return "only %d candles" % len(c)
    for i, r in enumerate(c):
        t, o, h, l, cl, v = r
        if min(o, h, l, cl) <= 0 or v < 0: return "non-positive value at %d" % i
        if h < max(o, cl) or l > min(o, cl) or h < l: return "high/low inconsistent at %d" % i
        if i and t - c[i - 1][0] != ms: return "gap or duplicate at index %d" % i
        if t % ms: return "misaligned open time at %d" % i
    if c[-1][0] + ms > now_ms: return "last candle not closed"
    if now_ms - (c[-1][0] + ms) > 2 * ms: return "last closed candle too old"
    return None

def crosscheck(a, b, srcb):
    bm = {r[0]: r[4] for r in b}
    d = [abs(r[4] - bm[r[0]]) / bm[r[0]] * 100 for r in a[-24:] if r[0] in bm]
    if len(d) < 12: return None
    med = statistics.median(d)
    return {"source": SRC[srcb][0], "url": SRC[srcb][1], "candles_compared": len(d), "median_diff_pct": round(med, 4),
            "max_diff_pct": round(max(d), 4), "ok": med <= MAX_DIFF_PCT, "limit_pct": MAX_DIFF_PCT}

def build(fetcher, now):
    now_ms = int(now.timestamp() * 1000); ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    recs, report, errs = [], {}, {}
    for s in SYMS:
        for tf, ms in TFS.items():
            ok = {}
            for src in ("binance", "okx", "gate"):
                try:
                    c = fetcher(src, s, tf, now_ms)[-N:]
                    e = check_series(c, ms, now_ms)
                    if e: errs[f"{src}:{s}:{tf}"] = e
                    else: ok[src] = c
                except Exception as ex:
                    errs[f"{src}:{s}:{tf}"] = type(ex).__name__ + ": " + str(ex)[:60]
                if len(ok) == 2: break
            if not ok: raise RuntimeError("no valid candles for %s %s; %s" % (s, tf, errs))
            names = list(ok); a = names[0]
            chk = crosscheck(ok[a], ok[names[1]], names[1]) if len(names) > 1 else None
            src = {"name": SRC[a][0] + ("" if a == "binance" else " (fallback)"), "url": SRC[a][1]}
            recs.append({"id": "kline.%susdt.%s" % (s.lower(), tf), "value": ok[a], "unit": "candles [open_time_ms, o, h, l, c, base_volume]",
                         "source": src, "fetched_at": ts, "label": "measured", "max_age_hours": 8, "checked_against": chk,
                         "title_ar": "شموع %s (%s)" % (s, "ساعة" if tf == "1h" else "يوم")})
            report["%s.%s" % (s, tf)] = {"used": a, "crosscheck": names[1] if len(names) > 1 else None, "candles": len(ok[a])}
    return {"meta": {"module": "klines", "version": "1.0.0", "per_series": report, "source_errors": errs}, "records": recs}

def main():
    doc = build(fetch, datetime.now(timezone.utc))
    print("source errors:", doc["meta"]["source_errors"])
    with open(os.path.join(os.environ["OUT_DIR"], "klines.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()

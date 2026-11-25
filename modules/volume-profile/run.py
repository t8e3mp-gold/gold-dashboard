"""volume-profile: volume traded at each price level, for the last 24 hours and 7 days.
Method (labelled approximation): each 1-minute candle's volume (and taker-buy volume) is spread evenly over the candle's
[low, high] range, in proportion to the overlap with each price bin. 60 bins between the window's lowest low and highest high.
POC = bin with the most volume. Value area = the smallest set of bins grown from the POC (taking the larger neighbour first)
that holds at least 70% of the volume. Row: [bin_low, bin_high, volume, buy_volume].
Plan A: 1m candles from the Binance mirror. Plan B: 1h candles from the klines module (coarser, flagged). Plan C: module fails, last good file stays, flagged stale."""
import json, os, urllib.request
from datetime import datetime, timezone

SYMS = ["XAUT", "BNB", "ETH", "SOL"]
WINDOWS = {"24h": 1440, "7d": 10080}
NB = 60
VA = 0.70
BASE = "https://data-api.binance.vision/api/v3/klines"
MIN_COVER = 0.80   # share of expected minutes that must exist (Binance omits minutes without trades)

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "gold-dashboard-refresh"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def profile(bars, nb=NB):
    """bars: [[open_time, high, low, volume, buy_volume]]. Returns (rows, lo, hi)."""
    lo = min(b[2] for b in bars); hi = max(b[1] for b in bars)
    if hi <= lo: hi = lo * (1 + 1e-9) + 1e-9
    w = (hi - lo) / nb; vol = [0.0] * nb; buy = [0.0] * nb
    for _, h, l, v, bv in bars:
        if h - l < w * 1e-9:
            i = min(nb - 1, int((l - lo) / w)); vol[i] += v; buy[i] += bv; continue
        i0 = min(nb - 1, int((l - lo) / w)); i1 = min(nb - 1, int((h - lo) / w))
        for i in range(i0, i1 + 1):
            a = max(l, lo + i * w); b = min(h, lo + (i + 1) * w)
            if b > a:
                f = (b - a) / (h - l); vol[i] += v * f; buy[i] += bv * f
    rows = [[lo + i * w, lo + (i + 1) * w, vol[i], buy[i]] for i in range(nb)]
    return rows, lo, hi

def stats(rows):
    tot = sum(r[2] for r in rows)
    if tot <= 0: raise ValueError("no volume")
    p = max(range(len(rows)), key=lambda i: rows[i][2])
    lo = hi = p; acc = rows[p][2]
    while acc < VA * tot and (lo > 0 or hi < len(rows) - 1):
        up = rows[hi + 1][2] if hi < len(rows) - 1 else -1
        dn = rows[lo - 1][2] if lo > 0 else -1
        if up >= dn: hi += 1; acc += rows[hi][2]
        else: lo -= 1; acc += rows[lo][2]
    mid = lambda r: (r[0] + r[1]) / 2
    return {"poc": round(mid(rows[p]), 8), "vah": round(rows[hi][1], 8), "val": round(rows[lo][0], 8),
            "value_area_share_pct": round(acc / tot * 100, 2), "total_volume": round(tot, 8)}

def fetch_1m(sym, minutes, now_ms, get=get):
    end_open = (now_ms // 60000) * 60000          # the current minute is forming: excluded
    start = end_open - minutes * 60000; out = []; cur = start
    while cur < end_open:
        rows = get("%s?symbol=%sUSDT&interval=1m&startTime=%d&endTime=%d&limit=1000" % (BASE, sym, cur, end_open - 1))
        if not rows: break
        for r in rows:
            if int(r[6]) < now_ms and int(r[0]) < end_open:
                out.append([int(r[0]), float(r[2]), float(r[3]), float(r[5]), float(r[9])])
        cur = int(rows[-1][0]) + 60000
        if len(rows) < 1000: break
    return out, start

def clean(bars):
    seen, out = set(), []
    for b in bars:
        if b[0] in seen: continue
        seen.add(b[0]); t, h, l, v, bv = b
        if min(h, l) <= 0 or h < l or v < 0 or bv < 0 or bv > v * (1 + 1e-9): raise ValueError("bad candle %d" % t)
        out.append(b)
    return sorted(out)

def from_hourly(krec, hours):
    """Plan B: 1h candles from the klines module; buy volume unknown, so it is set to 0 and flagged."""
    c = krec["value"][-hours:]
    return [[r[0], r[2], r[3], r[5], 0.0] for r in c]

def build(fetch, klines_doc, now):
    now_ms = int(now.timestamp() * 1000); ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    kmap = {r["id"]: r for r in klines_doc["records"]} if klines_doc else {}
    recs, notes = [], {}
    for s in SYMS:
        try:
            one, _ = fetch(s, max(WINDOWS.values()), now_ms)
            one = clean(one)
            for wn2, m2 in WINDOWS.items():
                n2 = sum(1 for b in one if b[0] >= now_ms - m2 * 60000)
                if n2 < MIN_COVER * m2: raise ValueError("%s: only %d of %d minutes have trades" % (wn2, n2, m2))
            used = "binance-1m"
        except Exception as e:
            kr = kmap.get("kline.%susdt.1h" % s.lower())
            if not kr: raise RuntimeError("%s: no 1m data (%s) and no klines fallback" % (s, e))
            one = from_hourly(kr, 168); used = "klines-1h"; notes[s] = "1m unavailable (%s); coarse 1h-candle profile, buy volume unknown" % str(e)[:60]
        for wn, minutes in WINDOWS.items():
            lim = now_ms - minutes * 60000
            bars = [b for b in one if b[0] >= lim]
            if len(bars) < 10: raise RuntimeError("%s %s: too few bars" % (s, wn))
            rows, lo, hi = profile(bars); st = stats(rows)
            st.update({"bars_used": len(bars), "bar_size": "1m" if used == "binance-1m" else "1h", "window": wn,
                       "price_low": round(lo, 8), "price_high": round(hi, 8),
                       "coverage_pct": round(len(bars) / minutes * 100, 1) if used == "binance-1m" else None,
                       "method": "volume of each candle spread evenly over its low-high range; 60 bins; value area 70%"})
            chk = None
            kr = kmap.get("kline.%susdt.1h" % s.lower())
            if used == "binance-1m" and kr and kr["source"]["name"].startswith("Binance public"):
                hrs = minutes // 60
                t_first = (lim // 3600000 + 1) * 3600000
                t_last = min((now_ms // 3600000) * 3600000, kr["value"][-1][0] + 3600000)   # the klines file may be a little older
                km = sum(r[5] for r in kr["value"] if t_first <= r[0] < t_last)
                mm = sum(b[3] for b in bars if t_first <= b[0] < t_last)
                if km > 0:
                    d = abs(mm - km) / km * 100
                    chk = {"source": "klines module 1h volume over the same whole hours", "url": BASE, "value": round(km, 6), "diff_pct": round(d, 5), "ok": d <= 0.01, "limit_pct": 0.01}
            src = {"name": "Binance public data mirror, 1m candles" if used == "binance-1m" else "klines module 1h candles (fallback, coarse)", "url": BASE}
            recs.append({"id": "profile.%susdt.%s" % (s.lower(), wn), "value": [[round(r[0], 8), round(r[1], 8), round(r[2], 6), round(r[3], 6)] for r in rows],
                         "unit": "profile [price_low, price_high, volume, buy_volume]", "source": src, "fetched_at": ts, "label": "measured",
                         "max_age_hours": 8, "checked_against": chk, "stats": st,
                         "title_ar": "بروفايل الحجم %s (%s)" % (s, "24 ساعة" if wn == "24h" else "7 أيام")})
    return {"meta": {"module": "volume-profile", "version": "1.0.0", "notes": notes}, "records": recs}

def main():
    kp = os.path.join(os.environ.get("DATA_DIR", ""), "klines.json")
    kd = json.load(open(kp, encoding="utf-8")) if os.path.exists(kp) else None
    doc = build(fetch_1m, kd, datetime.now(timezone.utc))
    print("notes:", doc["meta"]["notes"])
    with open(os.path.join(os.environ["OUT_DIR"], "volume-profile.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()

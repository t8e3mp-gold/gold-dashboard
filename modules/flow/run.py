"""flow: buyer vs seller volume (delta) per CLOSED candle, 1h and 1d, from Binance taker-buy volume.
Row: [open_time_ms, volume, buy_volume, sell_volume, delta, cvd]. buy = volume bought by takers (market buys
hitting asks), sell = volume - buy, delta = buy - sell, cvd = running sum of delta from the first row (window-relative).
Plan A: kline taker-buy field. Plan B (check): aggTrades summed for the last closed hour (isBuyerMaker=false is a taker buy).
Plan C: if Binance is unreachable the module fails and the last good file stays published, flagged stale (no invented data)."""
import json, os, urllib.request
from datetime import datetime, timezone

SYMS = ["XAUT", "BNB", "ETH", "SOL"]
TFS = {"1h": 3600_000, "1d": 86400_000}
N = 300
AGG_MAX_PAGES = 15
AGG_TOL_PCT = 0.01   # kline taker-buy and the sum of aggTrades must agree this closely (same exchange, same trades)
BASE = "https://data-api.binance.vision/api/v3/"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "gold-dashboard-refresh"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def parse(rows, now_ms):
    out = []
    for r in rows:
        if int(r[6]) >= now_ms:
            continue                      # forming candle: never used
        vol, buy = float(r[5]), float(r[9])
        if vol < 0 or buy < 0 or buy > vol * (1 + 1e-9):
            raise ValueError("taker buy volume outside 0..volume at %s" % r[0])
        out.append([int(r[0]), vol, min(buy, vol)])
    return out

def to_flow(c):
    cvd, out = 0.0, []
    for t, vol, buy in c:
        sell = vol - buy; d = buy - sell; cvd += d
        out.append([t, round(vol, 8), round(buy, 8), round(sell, 8), round(d, 8), round(cvd, 8)])
    return out

def check_series(c, ms, now_ms):
    if len(c) < 200: return "only %d candles" % len(c)
    for i in range(1, len(c)):
        if c[i][0] - c[i - 1][0] != ms: return "gap or duplicate at %d" % i
    if c[-1][0] % ms: return "misaligned"
    if c[-1][0] + ms > now_ms or now_ms - (c[-1][0] + ms) > 2 * ms: return "last candle not the latest closed one"
    return None

def agg_buy_volume(sym, start, end, get=get):
    """Sum of taker-buy base volume from aggTrades in [start, end). Returns (buy_volume, trades) or None if too many pages."""
    buy, n, url = 0.0, 0, "%saggTrades?symbol=%sUSDT&startTime=%d&endTime=%d&limit=1000" % (BASE, sym, start, end - 1)
    for _ in range(AGG_MAX_PAGES):
        rows = get(url)
        for t in rows:
            if t["T"] < end:
                n += 1
                if not t["m"]: buy += float(t["q"])      # m = buyer is maker, so the taker sold
        if len(rows) < 1000: return buy, n
        url = "%saggTrades?symbol=%sUSDT&fromId=%d&limit=1000" % (BASE, sym, rows[-1]["a"] + 1)
        if rows[-1]["T"] >= end: return buy, n
    return None

def build(fetch_klines, agg, klines_doc, now):
    now_ms = int(now.timestamp() * 1000); ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    kmap = {r["id"]: r for r in klines_doc["records"]} if klines_doc else {}
    recs, notes = [], {}
    for s in SYMS:
        for tf, ms in TFS.items():
            c = fetch_klines(s, tf, now_ms)[-N:]
            e = check_series(c, ms, now_ms)
            if e: raise RuntimeError("%s %s: %s" % (s, tf, e))
            chk, note = None, None
            if tf == "1h":
                t0 = c[-1][0]
                r = agg(s, t0, t0 + ms)
                if r is None: note = "aggTrades check skipped: more than %d pages of trades" % AGG_MAX_PAGES
                else:
                    ab, n = r; kb = c[-1][2]
                    diff = abs(ab - kb) / kb * 100 if kb else (0.0 if ab == 0 else 100.0)
                    chk = {"source": "Binance aggTrades summed for the last closed hour", "url": BASE + "aggTrades", "value": round(ab, 8),
                           "kline_value": kb, "trades": n, "diff_pct": round(diff, 5), "ok": diff <= AGG_TOL_PCT, "limit_pct": AGG_TOL_PCT}
            else:
                kr = kmap.get("kline.%susdt.1d" % s.lower())
                if kr and kr["source"]["name"].startswith("Binance public"):
                    km = {x[0]: x[5] for x in kr["value"]}
                    common = [x for x in c if x[0] in km]
                    bad = sum(1 for x in common if abs(x[1] - km[x[0]]) > 1e-9 * max(1, x[1]))
                    chk = {"source": "klines module volume (same exchange)", "url": BASE + "klines", "value": len(common),
                           "diff_pct": round(bad / max(1, len(common)) * 100, 5), "ok": bad == 0, "limit_pct": 0}
                else: note = "no independent volume to compare (klines used another source)"
            if note: notes["%s.%s" % (s, tf)] = note
            recs.append({"id": "flow.%susdt.%s" % (s.lower(), tf), "value": to_flow(c),
                         "unit": "flow [open_time_ms, volume, buy_volume, sell_volume, delta, cvd]",
                         "source": {"name": "Binance public data mirror (taker buy volume)", "url": BASE + "klines"},
                         "fetched_at": ts, "label": "measured", "max_age_hours": 8, "checked_against": chk,
                         "title_ar": "تدفق %s (%s)" % (s, "ساعة" if tf == "1h" else "يوم")})
    return {"meta": {"module": "flow", "version": "1.0.0", "notes": notes}, "records": recs}

def fetch_klines(s, tf, now_ms):
    return parse(get("%sklines?symbol=%sUSDT&interval=%s&limit=%d" % (BASE, s, tf, N + 1)), now_ms)

def main():
    kp = os.path.join(os.environ.get("DATA_DIR", ""), "klines.json")
    kd = json.load(open(kp, encoding="utf-8")) if os.path.exists(kp) else None
    doc = build(fetch_klines, agg_buy_volume, kd, datetime.now(timezone.utc))
    print("notes:", doc["meta"]["notes"])
    with open(os.path.join(os.environ["OUT_DIR"], "flow.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()

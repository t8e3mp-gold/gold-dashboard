"""price-spot: last price and 24h change for XAUT, BNB, ETH, SOL (all vs USDT).
Plan A Binance public mirror, Plan B OKX, Plan C Gate.io. The first source that answers is the
published value; the next one that answers is the cross-check. Values are never blended.
If the two differ by more than MAX_DIFF_PCT the record says so (ok=false) and the page warns."""
import json, os, urllib.request
from datetime import datetime, timezone

SYMS = ["XAUT", "BNB", "ETH", "SOL"]
NAMES = {"XAUT": "الذهب XAUT", "BNB": "BNB", "ETH": "ETH", "SOL": "SOL"}
MAX_DIFF_PCT = 0.5
SRC = {
    "binance": ("Binance public data mirror", "https://data-api.binance.vision/api/v3/ticker/24hr"),
    "okx": ("OKX spot tickers", "https://www.okx.com/api/v5/market/tickers?instType=SPOT"),
    "gate": ("Gate.io spot tickers", "https://api.gateio.ws/api/v4/spot/tickers"),
}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "gold-dashboard-refresh"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def fetch_binance(get=get):
    syms = json.dumps([s + "USDT" for s in SYMS], separators=(",", ":"))
    d = get(SRC["binance"][1] + "?symbols=" + urllib.request.quote(syms))
    return parse_binance(d)

def fetch_okx(get=get):
    return parse_okx(get(SRC["okx"][1]))

def fetch_gate(get=get):
    return parse_gate(get(SRC["gate"][1]))

def _pos(x):
    v = float(x)
    if not v > 0 or v != v or v == float("inf"):
        raise ValueError("bad price")
    return v

def parse_binance(d):
    out = {}
    for t in d:
        s = t["symbol"][:-4]
        if t["symbol"].endswith("USDT") and s in SYMS:
            out[s] = (_pos(t["lastPrice"]), float(t["priceChangePercent"]))
    return out

def parse_okx(d):
    out = {}
    for t in d["data"]:
        a, _, q = t["instId"].partition("-")
        if q == "USDT" and a in SYMS:
            last, o = _pos(t["last"]), _pos(t["open24h"])
            out[a] = (last, (last - o) / o * 100)
    return out

def parse_gate(d):
    out = {}
    for t in d:
        a, _, q = t["currency_pair"].partition("_")
        if q == "USDT" and a in SYMS:
            out[a] = (_pos(t["last"]), float(t["change_percentage"]))
    return out

def collect(fetchers):
    """Returns ({source: {sym: (price, change)}}, {source: error})."""
    got, errs = {}, {}
    for name, fn in fetchers:
        try:
            got[name] = fn()
        except Exception as e:
            errs[name] = type(e).__name__ + ": " + str(e)[:80]
    return got, errs

def build(got, errs, now):
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    order = [k for k in ("binance", "okx", "gate") if k in got]
    recs, report = [], {}
    for s in SYMS:
        have = [k for k in order if s in got[k]]
        if not have:
            raise RuntimeError("no source returned %s; errors: %s" % (s, errs))
        a = have[0]
        price, chg = got[a][s]
        chk = None
        if len(have) > 1:
            b = have[1]
            bp = got[b][s][0]
            diff = abs(price - bp) / bp * 100
            chk = {"source": SRC[b][0], "url": SRC[b][1], "value": bp, "diff_pct": round(diff, 4),
                   "ok": diff <= MAX_DIFF_PCT, "limit_pct": MAX_DIFF_PCT}
        src = {"name": SRC[a][0] + ("" if a == "binance" else " (fallback: earlier source unavailable)"), "url": SRC[a][1]}
        base = {"unit": "USDT", "source": src, "fetched_at": ts, "label": "measured", "max_age_hours": 8}
        recs.append(dict(base, id="price." + s.lower() + "usdt", value=price, title_ar="سعر " + NAMES[s], checked_against=chk))
        recs.append(dict(base, id="change24h." + s.lower() + "usdt", value=round(chg, 4), unit="% (24h)",
                         title_ar="تغيّر 24 ساعة " + NAMES[s], checked_against=None))
        report[s] = {"used": a, "crosscheck": have[1] if len(have) > 1 else None}
    return {"meta": {"module": "price-spot", "version": "1.0.0", "sources_ok": order,
                     "sources_failed": errs, "per_symbol": report}, "records": recs}

def main():
    got, errs = collect([("binance", fetch_binance), ("okx", fetch_okx), ("gate", fetch_gate)])
    doc = build(got, errs, datetime.now(timezone.utc))
    print("sources ok:", list(got), "failed:", errs)
    with open(os.path.join(os.environ["OUT_DIR"], "price-spot.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()

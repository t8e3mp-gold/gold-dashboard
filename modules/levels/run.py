"""levels: support/resistance zones from data we already collect. Everything is a HYPOTHESIS and describes the past.
Candidates: volume-profile POC, value-area edges and high-volume nodes (24h and 7d), 1h swing highs/lows (5 candles each side),
1d swing highs/lows (3 each side), 24h and 7d extremes. Candidates within 0.2% of each other are merged into one zone.
For each zone we count how often price entered it from the other side in the last 300 1h candles (episodes) and how often it
then moved at least one ATR away within 6 candles (bounces). Small counts are shown as small counts. No prediction is made."""
import json, os
from datetime import datetime, timezone

SYMS = ["XAUT", "BNB", "ETH", "SOL"]
MERGE_PCT = 0.2
K1H, K1D = 5, 3
LOOK = 6

def load(p):
    with open(p, encoding="utf-8") as f: return json.load(f)

def swings(c, k, hi_idx, lo_idx):
    """Fractal swings on closed candles: a high strictly above the k candles on each side (same for lows)."""
    H, L = [], []
    for i in range(k, len(c) - k):
        h = c[i][hi_idx]; l = c[i][lo_idx]
        if all(h > c[i - j][hi_idx] and h > c[i + j][hi_idx] for j in range(1, k + 1)): H.append((c[i][0], h))
        if all(l < c[i - j][lo_idx] and l < c[i + j][lo_idx] for j in range(1, k + 1)): L.append((c[i][0], l))
    return H, L

def atr(c, n=14):
    tr = []
    for i in range(1, len(c)):
        tr.append(max(c[i][2] - c[i][3], abs(c[i][2] - c[i - 1][4]), abs(c[i][3] - c[i - 1][4])))
    t = tr[-n:]; return sum(t) / len(t)

def nodes(rows, top=3):
    """Top local maxima of the volume profile rows [lo, hi, vol, buy], not adjacent, at least 1.25x the mean bin."""
    mean = sum(r[2] for r in rows) / len(rows); out = []
    for i in range(len(rows)):
        v = rows[i][2]
        if (i == 0 or v >= rows[i - 1][2]) and (i == len(rows) - 1 or v > rows[i + 1][2]) and v >= 1.25 * mean:
            out.append((v, (rows[i][0] + rows[i][1]) / 2))
    out.sort(reverse=True); return [p for _, p in out[:top]]

def candidates(sym, k1h, k1d, prof):
    c = []
    for w in ("24h", "7d"):
        p = prof.get("profile.%susdt.%s" % (sym.lower(), w))
        if not p: continue
        s = p["stats"]
        c += [(s["poc"], "profile", "أكثر سعر تداولا " + w), (s["vah"], "profile", "أعلى منطقة القيمة " + w), (s["val"], "profile", "أدنى منطقة القيمة " + w),
              (s["price_high"], "extreme", "أعلى سعر " + w), (s["price_low"], "extreme", "أدنى سعر " + w)]
        if w == "7d":
            c += [(x, "profile", "عقدة حجم عالٍ " + w) for x in nodes(p["value"])]
    H, L = swings(k1h, K1H, 2, 3)
    c += [(p, "swing", "قمة ساعة") for _, p in H[-6:]] + [(p, "swing", "قاع ساعة") for _, p in L[-6:]]
    H, L = swings(k1d, K1D, 2, 3)
    c += [(p, "swing", "قمة يومية") for _, p in H[-4:]] + [(p, "swing", "قاع يومي") for _, p in L[-4:]]
    return c

def merge(cands):
    cands = sorted(cands, key=lambda x: x[0]); zones = []
    for p, typ, why in cands:
        if zones and p <= zones[-1]["hi"] * (1 + MERGE_PCT / 100):
            z = zones[-1]; z["hi"] = max(z["hi"], p); z["pts"].append(p)
        else: zones.append({"lo": p, "hi": p, "pts": [p]})
        z = zones[-1]; z.setdefault("src", []).append((typ, why))
    out = []
    for z in zones:
        out.append({"lo": min(z["pts"]), "hi": max(z["pts"]), "mid": sum(z["pts"]) / len(z["pts"]),
                    "types": sorted({t for t, _ in z["src"]}), "why": sorted({w for _, w in z["src"]})})
    return out

def history(z, c, a):
    """Episodes: a 1h candle whose range enters the zone coming from outside it. Bounce = price moves at least one ATR away from
    the zone mid within LOOK candles on the side it came from, without closing beyond the far edge first."""
    pad = z["mid"] * MERGE_PCT / 100; lo, hi = z["lo"] - pad, z["hi"] + pad
    ep = bo = 0; i = 1
    while i < len(c) - LOOK:
        enter_from_above = c[i - 1][3] > hi and c[i][3] <= hi and c[i][4] >= lo
        enter_from_below = c[i - 1][2] < lo and c[i][2] >= lo and c[i][4] <= hi
        if enter_from_above or enter_from_below:
            ep += 1; nxt = c[i + 1:i + 1 + LOOK]
            if enter_from_above:
                broke = False; ok = False
                for r in nxt:
                    if r[4] < lo: broke = True; break
                    if r[2] >= z["mid"] + a: ok = True; break
                bo += 1 if ok and not broke else 0
            else:
                broke = False; ok = False
                for r in nxt:
                    if r[4] > hi: broke = True; break
                    if r[3] <= z["mid"] - a: ok = True; break
                bo += 1 if ok and not broke else 0
            i += LOOK
        else: i += 1
    return ep, bo

def forming(zones, c, price):
    """A bounce 'forming': one of the last 3 closed candles dipped into a zone below price and the last close is back above it
    (or the mirror at a zone above price). Descriptive only."""
    last = c[-3:]
    for z in zones:
        if z["mid"] < price and any(r[3] <= z["hi"] for r in last) and c[-1][4] > z["hi"] and min(r[4] for r in last) >= z["lo"] * (1 - MERGE_PCT / 100):
            return {"side": "support", "zone_mid": round(z["mid"], 6)}
        if z["mid"] > price and any(r[2] >= z["lo"] for r in last) and c[-1][4] < z["lo"] and max(r[4] for r in last) <= z["hi"] * (1 + MERGE_PCT / 100):
            return {"side": "resistance", "zone_mid": round(z["mid"], 6)}
    return None

def build(klines_doc, prof_doc, now):
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    km = {r["id"]: r for r in klines_doc["records"]}; prof = {r["id"]: r for r in prof_doc["records"]}
    recs = []
    for s in SYMS:
        k1h = km["kline.%susdt.1h" % s.lower()]["value"]; k1d = km["kline.%susdt.1d" % s.lower()]["value"]
        price = k1h[-1][4]; a = atr(k1h)
        zones = merge(candidates(s, k1h, k1d, prof))
        for z in zones:
            z["episodes"], z["bounces"] = history(z, k1h, a)
            z["strength"] = len(z["types"]) * 2 + min(z["episodes"], 6)
            for k in ("lo", "hi", "mid"): z[k] = round(z[k], 6)
        recs.append({"id": "levels.%susdt" % s.lower(), "title_ar": "المستويات %s (فرضية)" % s, "unit": "levels",
                     "value": {"price_ref": price, "price_ref_time": k1h[-1][0], "zones": zones, "forming": forming(zones, k1h, price)},
                     "stats": {"atr_1h": round(a, 6), "candles": len(k1h), "merge_pct": MERGE_PCT, "lookahead_candles": LOOK,
                               "method": "profile POC/value area/nodes + 1h and 1d swings + extremes, merged within 0.2%%; episodes and bounces counted over the last %d 1h candles" % len(k1h)},
                     "source": {"name": "klines and volume-profile modules (Binance public data)", "url": "https://data-api.binance.vision/api/v3/klines"},
                     "fetched_at": ts, "label": "hypothesis", "max_age_hours": 8, "checked_against": None})
    return {"meta": {"module": "levels", "version": "1.0.0"}, "records": recs}

def main():
    d = os.environ["DATA_DIR"]
    doc = build(load(os.path.join(d, "klines.json")), load(os.path.join(d, "volume-profile.json")), datetime.now(timezone.utc))
    with open(os.path.join(os.environ["OUT_DIR"], "levels.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()

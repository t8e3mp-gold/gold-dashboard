"""forward-log (R6): appends what the recommendation said (at most once an hour per coin) and, once 24 hours of REAL later candles exist,
appends how it turned out. Both logs are append-only (the runner rejects a run that drops or changes an old record).
Nothing is simulated here: scores use real closed 1h candles after the entry. Entries one hour apart overlap, so the summary also
counts independent days. Fees: 0.3% round trip, same as the backtest."""
import json, os
from datetime import datetime, timezone, timedelta

SYMS = ["XAUT", "BNB", "ETH", "SOL"]
COST = 0.3          # percent, round trip
MIN_GAP_MIN = 55
HORIZON_H = 24
KEEP = 87600        # max_age_hours for log records (they are history, not live data)
SRC = {"name": "recommendation and klines modules (Binance public data), scored on real later candles", "url": "https://data-api.binance.vision/api/v3/klines"}

def load(p):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except FileNotFoundError: return {"meta": {}, "records": []}

def iso(dt): return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
def parse(s): return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

def new_entries(rec_doc, old_log, now):
    """Entries to append: one per coin, skipped if the last logged entry for that coin is under MIN_GAP_MIN old. Never changes old ones."""
    last = {}
    for r in old_log["records"]:
        last[r["value"]["coin"]] = max(last.get(r["value"]["coin"], ""), r["fetched_at"])
    out = []
    for s in SYMS:
        rec = next(r for r in rec_doc["records"] if r["id"] == "recommendation.%susdt" % s.lower()); v = rec["value"]
        if s in last and now - parse(last[s]) < timedelta(minutes=MIN_GAP_MIN): continue
        bp = v.get("buy_plan"); buy = None
        if bp: buy = {k: bp.get(k) for k in ("zone_lo", "zone_hi", "invalidation", "target", "risk_pct", "reward_pct")}
        out.append({"id": "forward.%susdt" % s.lower(), "title_ar": "سجل أمامي %s" % s, "unit": "forward-entry",
                    "value": {"coin": s, "stance": v["stance"], "price": v["price_ref"], "price_time": v["price_ref_time"], "edge_proven": v["edge"]["proven"], "buy": buy,
                              "news_wait": v["news"]["wait"], "leak_trap": v["news"]["leak_trap"]},
                    "stats": {}, "source": SRC, "fetched_at": iso(now), "label": "measured", "max_age_hours": KEEP, "checked_against": None})
    return out

def score(entry, k1h, now_ms=None):
    """Score one logged entry with real candles after it. Returns a dict or None if 24h of closed candles do not exist yet (or are missing).
    Candles considered: open_time >= entry time, for HORIZON_H candles. buy_status: no_plan | no_touch | target_first | invalid_first | open.
    Same candle touching invalidation and target counts as invalid_first (conservative)."""
    t0 = int(parse(entry["fetched_at"]).timestamp() * 1000); hz = HORIZON_H * 3600_000
    cs = [c for c in k1h if t0 <= c[0] < t0 + hz and (now_ms is None or c[0] + 3600_000 <= now_ms)]   # closed candles only
    if len(cs) < HORIZON_H or cs[0][0] - t0 > 3600_000: return None
    v = entry["value"]; p0 = v["price"]; close = cs[-1][4]; res = {"coin": v["coin"], "entry_time": entry["fetched_at"], "stance": v["stance"], "price0": p0,
        "ret_24h_pct": round(100 * (close / p0 - 1), 3), "buy_status": "no_plan", "net_pct": None}
    b = v.get("buy")
    if not b: return res
    touched = False; status = "no_touch"; net = None
    for c in cs:
        if not touched and c[3] <= b["zone_hi"]: touched = True; status = "open"
        if touched:
            if c[3] <= b["invalidation"]: status = "invalid_first"; net = -b["risk_pct"] - COST; break
            if b.get("target") and c[2] >= b["target"]: status = "target_first"; net = b["reward_pct"] - COST; break
    if status == "open": net = 100 * (close / b["zone_hi"] - 1) - COST
    res["buy_status"] = status; res["net_pct"] = None if net is None else round(net, 3)
    return res

def new_scores(log, old_scores, k1h, now_ms=None):
    done = {(r["value"]["coin"], r["value"]["entry_time"]) for r in old_scores["records"]}; out = []
    for e in log["records"]:
        key = (e["value"]["coin"], e["fetched_at"])
        if key in done: continue
        sc = score(e, k1h[e["value"]["coin"]], now_ms)
        if sc: out.append({"id": "forwardscore.%susdt" % sc["coin"].lower(), "title_ar": "نتيجة سجل أمامي %s" % sc["coin"], "unit": "forward-score", "value": sc, "stats": {},
                           "source": SRC, "fetched_at": e["fetched_at"], "label": "measured", "max_age_hours": KEEP, "checked_against": None})
    return out

def empty_archive(now):
    """Archive counters record (envelope). Written by tools/archive_logs.py; this module only passes it through and reads it for the all-time summary."""
    return {"meta": {"module": "forward-log", "version": "1.0.0"}, "records": [{"id": "forwardarchive.stats", "title_ar": "عدّادات السجل المؤرشف", "unit": "forward-archive", "value": {"coins": {}, "archived_through": None},
            "stats": {}, "source": SRC, "fetched_at": iso(now), "label": "measured", "max_age_hours": KEEP, "checked_against": None}]}

def accum(entries, scores):
    """Per-coin raw counters from log and score records. Pure; used for the live window and by the archive tool (tools/archive_logs.py)."""
    out = {c: {"logged": 0, "scored": 0, "days": [], "with_plan": 0, "touched": 0, "wins": 0, "net_sum": 0.0, "net_n": 0, "target_first": 0, "invalid_first": 0, "first_logged": None} for c in SYMS}
    for r in entries:
        a = out[r["value"]["coin"]]; a["logged"] += 1
        if a["first_logged"] is None or r["fetched_at"] < a["first_logged"]: a["first_logged"] = r["fetched_at"]
    for r in scores:
        v = r["value"]; a = out[v["coin"]]; a["scored"] += 1
        if v["entry_time"][:10] not in a["days"]: a["days"].append(v["entry_time"][:10])
        if v["buy_status"] == "no_plan": continue
        a["with_plan"] += 1
        if v["buy_status"] == "no_touch": continue
        a["touched"] += 1
        if v["net_pct"] is not None:
            a["net_sum"] += v["net_pct"]; a["net_n"] += 1
            if v["net_pct"] > 0: a["wins"] += 1
        if v["buy_status"] == "target_first": a["target_first"] += 1
        if v["buy_status"] == "invalid_first": a["invalid_first"] += 1
    return out

def merge_acc(x, y):
    """Add two per-coin counter dicts (archive + live window)."""
    z = {k: x[k] + y[k] for k in ("logged", "scored", "with_plan", "touched", "wins", "net_n", "target_first", "invalid_first")}
    z["net_sum"] = x["net_sum"] + y["net_sum"]; z["days"] = sorted(set(x["days"]) | set(y["days"]))
    fl = [t for t in (x["first_logged"], y["first_logged"]) if t]; z["first_logged"] = min(fl) if fl else None
    return z

def summarize(coin, entries, scores, ts, arch=None):
    a = accum(entries, scores)[coin]
    if arch and coin in arch.get("coins", {}): a = merge_acc(arch["coins"][coin], a)
    st = {"coin": coin, "logged": a["logged"], "scored": a["scored"], "independent_days": len(a["days"]), "with_plan": a["with_plan"], "touched": a["touched"], "wins": a["wins"],
          "win_rate": round(a["wins"] / a["touched"], 4) if a["touched"] else None, "avg_net_pct": round(a["net_sum"] / a["net_n"], 3) if a["net_n"] else None,
          "target_first": a["target_first"], "invalid_first": a["invalid_first"], "first_logged": a["first_logged"], "target": {"win_rate": 0.98, "trades": 1000, "max_drawdown_pct": 20}}
    return {"id": "forwardsummary.%susdt" % coin.lower(), "title_ar": "ملخص السجل الأمامي %s" % coin, "unit": "forward-summary", "value": st, "stats": {"cost_pct": COST, "horizon_h": HORIZON_H},
            "source": SRC, "fetched_at": ts, "label": "measured", "max_age_hours": 8, "checked_against": None}

def main():
    d = os.environ["DATA_DIR"]; o = os.environ["OUT_DIR"]; now = datetime.now(timezone.utc)
    rec = load(os.path.join(d, "recommendation.json")); kl = load(os.path.join(d, "klines.json"))
    old_log = load(os.path.join(d, "forward-log.json")); old_sc = load(os.path.join(d, "forward-score.json"))
    k1h = {s: next(r["value"] for r in kl["records"] if r["id"] == "kline.%susdt.1h" % s.lower()) for s in SYMS}
    log = {"meta": {"module": "forward-log", "version": "1.0.0"}, "records": old_log["records"] + new_entries(rec, old_log, now)}
    sc = {"meta": {"module": "forward-log", "version": "1.0.0"}, "records": old_sc["records"] + new_scores(log, old_sc, k1h, int(now.timestamp() * 1000))}
    adoc = load(os.path.join(d, "forward-archive.json")); adoc = adoc if adoc["records"] else empty_archive(now); arch = adoc["records"][0]["value"]
    summ = {"meta": {"module": "forward-log", "version": "1.0.0"}, "records": [summarize(s, log["records"], sc["records"], iso(now), arch) for s in SYMS]}
    for name, doc in (("forward-log", log), ("forward-score", sc), ("forward-summary", summ), ("forward-archive", adoc)):
        with open(os.path.join(o, name + ".json"), "w", encoding="utf-8") as f: json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()

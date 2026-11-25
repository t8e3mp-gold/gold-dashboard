"""crosscheck-log: keeps the last 400 refreshes of real cross-check differences from every module, so a quiet check
(always near 0) can be told apart from a dead check (never logged). Reads only the other modules' output files and its own
previous output. Label: measured. Flagged = a check whose own 'ok' is false."""
import json, os
from datetime import datetime, timezone

KEEP = 400
SRC = {"price-spot": "price", "klines": "kline", "flow": "flow", "volume-profile": "profile"}

def load(path):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError): return None

def entries(docs):
    """-> (data_time, {record id: [diff_pct, ok]}) from the checked_against blocks."""
    out, t = {}, ""
    for name, doc in docs.items():
        if not doc: continue
        for r in doc.get("records", []):
            c = r.get("checked_against")
            if not c: continue
            d = c.get("max_diff_pct") if c.get("max_diff_pct") is not None else c.get("diff_pct")
            if d is None: continue
            out[r["id"]] = [float(d), bool(c.get("ok"))]
            t = max(t, r.get("fetched_at", ""))
    return t, out

def group(rid):
    return rid.split(".")[0] if rid.split(".")[0] in ("price", "kline", "flow", "profile") else "other"

def update(prev_runs, data_time, now_ts, ent):
    runs = list(prev_runs)
    if ent and not (runs and runs[-1][0] == data_time):          # same data time = same refresh, do not log twice
        runs.append([data_time or now_ts, now_ts, ent])
    return runs[-KEEP:]

def stats(runs):
    g, checks, flagged = {}, 0, 0
    for _, _, ent in runs:
        for rid, (d, ok) in ent.items():
            x = g.setdefault(group(rid), {"checks": 0, "flagged": 0, "max_diff_pct": 0.0, "sum": 0.0})
            x["checks"] += 1; x["sum"] += d; x["max_diff_pct"] = max(x["max_diff_pct"], d); checks += 1
            if not ok: x["flagged"] += 1; flagged += 1
    for x in g.values(): x["mean_diff_pct"] = round(x.pop("sum") / x["checks"], 5); x["max_diff_pct"] = round(x["max_diff_pct"], 5)
    return {"runs": len(runs), "checks_total": checks, "flagged_total": flagged, "groups": g,
            "first_run": runs[0][1] if runs else None, "last_run": runs[-1][1] if runs else None, "kept": KEEP}

def build(docs, prev, now):
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    prev_runs = prev["records"][0]["value"] if prev and prev.get("records") else []
    t, ent = entries(docs)
    if not ent: raise ValueError("no cross-check results found in the input modules")
    runs = update(prev_runs, t, ts, ent)
    return {"meta": {"module": "crosscheck-log", "version": "1.0.0"}, "records": [{
        "id": "crosscheck.log", "title_ar": "سجل الفروقات الحقيقية بين المصادر", "value": runs,
        "unit": "xcheck [data_time, logged_at, {record: [diff_pct, ok]}]", "stats": stats(runs),
        "source": {"name": "Cross-check results of the other modules", "url": "https://github.com/t8e3mp-gold/gold-dashboard/tree/main/data"},
        "fetched_at": ts, "label": "measured", "max_age_hours": 8, "checked_against": None}]}

def main():
    d = os.environ["DATA_DIR"]
    docs = {k: load(os.path.join(d, k + ".json")) for k in SRC}
    doc = build(docs, load(os.path.join(d, "crosscheck-log.json")), datetime.now(timezone.utc))
    with open(os.path.join(os.environ["OUT_DIR"], "crosscheck-log.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()

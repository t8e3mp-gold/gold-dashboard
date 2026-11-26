"""Monthly archive of the forward log (automatic, run by the Archive workflow; manual: run it by hand).
Moves log and score records older than KEEP_DAYS from data/forward-log.json and data/forward-score.json into
data/archive/<name>-YYYY-MM.json (append-only: existing archive records are never changed or dropped), and adds their counters to
data/forward-archive.json so the all-time summary stays right. The live files keep only the recent window, so the phone page stays light.
Safety: an archive file is written first, then the counters, then the trimmed live file; if the run stops half way, a re-run is safe
(records already in the archive are skipped, counters only count records newly archived)."""
import importlib.util, json, os, sys
from datetime import datetime, timedelta, timezone
KEEP_DAYS = 45
HERE = os.path.dirname(os.path.abspath(__file__))

def load_fwd():
    spec = importlib.util.spec_from_file_location("fwd", os.path.join(HERE, "..", "modules", "forward-log", "run.py")); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def jload(p, default):
    try: return json.load(open(p, encoding="utf-8"))
    except FileNotFoundError: return default
def jsave(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True); json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

def run(data, now, keep_days=KEEP_DAYS):
    fwd = load_fwd(); cut = (now - timedelta(days=keep_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    log = jload(os.path.join(data, "forward-log.json"), {"meta": {}, "records": []}); sc = jload(os.path.join(data, "forward-score.json"), {"meta": {}, "records": []})
    adoc = jload(os.path.join(data, "forward-archive.json"), None) or fwd.empty_archive(now); arch = adoc["records"][0]["value"]
    moved = {"forward-log": [], "forward-score": []}; keep = {"forward-log": [], "forward-score": []}
    for name, doc in (("forward-log", log), ("forward-score", sc)):
        for r in doc["records"]: (moved if r["fetched_at"] < cut else keep)[name].append(r)
    if not moved["forward-log"] and not moved["forward-score"]: return {"moved": 0}
    new = {"forward-log": [], "forward-score": []}
    for name in moved:
        by = {}
        for r in moved[name]: by.setdefault(r["fetched_at"][:7], []).append(r)
        for month, recs in by.items():
            p = os.path.join(data, "archive", "%s-%s.json" % (name, month)); ex = jload(p, {"meta": {"archive": name, "month": month}, "records": []})
            have = {(r["id"], r["fetched_at"]) for r in ex["records"]}; add = [r for r in recs if (r["id"], r["fetched_at"]) not in have]
            ex["records"] += add; new[name] += add; jsave(p, ex)
    cur = fwd.accum(new["forward-log"], new["forward-score"]); old = arch.get("coins") or {}
    for c in fwd.SYMS: arch.setdefault("coins", {})[c] = fwd.merge_acc(old[c], cur[c]) if c in old else cur[c]
    arch["archived_through"] = cut; adoc["records"][0]["fetched_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ"); jsave(os.path.join(data, "forward-archive.json"), adoc)
    for name, doc in (("forward-log", log), ("forward-score", sc)): doc["records"] = keep[name]; jsave(os.path.join(data, name + ".json"), doc)
    return {"moved": len(moved["forward-log"]) + len(moved["forward-score"]), "added_to_archive": len(new["forward-log"]) + len(new["forward-score"])}

if __name__ == "__main__":
    print(run(sys.argv[1] if len(sys.argv) > 1 else "data", datetime.now(timezone.utc)))

"""Writes docs/FORWARD_PATTERNS.md from the scored forward log (live window plus monthly archives). Facts only: counts and averages, with the sample size
next to every number. No claims about edge: under 100 scored entries per group the file says so."""
import glob, json, os, sys
from datetime import datetime, timezone
def load_scores(data):
    recs = []
    for p in [os.path.join(data, "forward-score.json")] + sorted(glob.glob(os.path.join(data, "archive", "forward-score-*.json"))):
        try: recs += json.load(open(p, encoding="utf-8"))["records"]
        except FileNotFoundError: pass
    return [r["value"] for r in recs]
def table(rows, keyname):
    g = {}
    for v in rows: g.setdefault(keyname(v), []).append(v)
    out = ["| group | scored | zone touched | wins | avg net % (touched) | note |", "|---|---|---|---|---|---|"]
    for k in sorted(g):
        vs = g[k]; t = [x for x in vs if x["buy_status"] not in ("no_plan", "no_touch") and x["net_pct"] is not None]; w = [x for x in t if x["net_pct"] > 0]
        avg = "%.2f" % (sum(x["net_pct"] for x in t) / len(t)) if t else "-"
        out.append("| %s | %d | %d | %d | %s | %s |" % (k, len(vs), len(t), len(w), avg, "sample too small to conclude" if len(vs) < 100 else ""))
    return "\n".join(out)
def build(rows, now):
    h = ["# Forward log patterns (auto-generated, %s UTC)" % now.strftime("%Y-%m-%d %H:%M"), "", "Source: data/forward-score.json plus data/archive/. Net is after 0.3% costs. Counts only; nothing here proves an edge.", "",
         "Scored entries: %d" % len(rows), ""]
    if not rows: return "\n".join(h + ["No scored entries yet (the first appear 24 hours after logging started)."]) + "\n"
    h += ["## By coin", table(rows, lambda v: v["coin"]), "", "## By stance when logged", table(rows, lambda v: v["stance"]), "",
          "## By buy-plan outcome", table(rows, lambda v: v["buy_status"]), "", "## By hour of day logged (UTC)", table(rows, lambda v: v["entry_time"][11:13])]
    return "\n".join(h) + "\n"
if __name__ == "__main__":
    data = sys.argv[1] if len(sys.argv) > 1 else "data"; out = sys.argv[2] if len(sys.argv) > 2 else "docs/FORWARD_PATTERNS.md"
    open(out, "w", encoding="utf-8").write(build(load_scores(data), datetime.now(timezone.utc))); print("patterns written:", out)

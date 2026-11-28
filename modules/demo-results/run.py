"""demo-results: a small honest summary of the DEMO account (virtual money, spot, no leverage). It publishes only counts and percentages:
trades (closed and still-open together, so stuck and open trades are counted), how many are open, wins, total net % after fees on the demo base with open
trades marked at the current price, and max drawdown. No balances, prices, order ids or account details. The numbers are written by hand into demo.json
(the page can only show what is committed) and the page shows their as-of time. The gate stage is computed here with the SAME rules the recommendation uses:
stage minimums, win-rate floor, positive total net, and drawdown under the limit at the full level. Everything is labelled simulated (demo)."""
import json, os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOWED = {"as_of", "trades", "open_trades", "wins", "total_net_pct", "max_drawdown_pct", "fee_per_side_pct"}

def load(p):
    with open(p, encoding="utf-8") as f: return json.load(f)

def check(d):
    """Strict input check: only the allowed keys (so nothing private can ride along), sane numbers."""
    extra = set(d) - ALLOWED; miss = ALLOWED - set(d)
    if extra or miss: raise ValueError("demo.json keys: extra %s missing %s" % (sorted(extra), sorted(miss)))
    n, o, w = d["trades"], d["open_trades"], d["wins"]
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in (n, o, w)): raise ValueError("counts must be integers")
    if not (0 <= w <= n and 0 <= o <= n): raise ValueError("counts inconsistent")
    for k in ("total_net_pct", "max_drawdown_pct", "fee_per_side_pct"):
        if not isinstance(d[k], (int, float)) or isinstance(d[k], bool): raise ValueError(k + " must be a number")
    if d["max_drawdown_pct"] < 0: raise ValueError("drawdown must be >= 0")
    datetime.strptime(d["as_of"], "%Y-%m-%dT%H:%M:%SZ")

def stage_of(trades, wins, total_net_pct, dd, stages, mins, full, dd_limit):
    """Highest stage cleared (0 if none). Same logic as recommendation.qualifies."""
    if trades <= 0: return 0
    wr = wins / trades; out = 0
    for s in stages:
        if trades < mins[str(s)] or wr * 100 < s or total_net_pct <= 0: continue
        if s >= full and dd >= dd_limit: continue
        out = s
    return out

def build(demo, rec_doc, now):
    check(demo)
    st = rec_doc["records"][0]["stats"]; ed = rec_doc["records"][0]["value"]["edge"]
    stages, mins, full, dd_limit = st["stages"], st["stage_min_trades"], st["full_level"], ed["full_dd_pct"]
    n, w = demo["trades"], demo["wins"]
    stage = stage_of(n, w, demo["total_net_pct"], demo["max_drawdown_pct"], stages, mins, full, dd_limit)
    nxt = next((s for s in stages if s > stage), None)
    val = {"as_of": demo["as_of"], "trades": n, "open_trades": demo["open_trades"], "closed_trades": n - demo["open_trades"], "wins": w,
           "win_rate": round(w / n, 4) if n else None, "total_net_pct": demo["total_net_pct"], "max_drawdown_pct": demo["max_drawdown_pct"],
           "fee_per_side_pct": demo["fee_per_side_pct"], "stage": stage, "next_stage": nxt, "min_trades_for_next": mins[str(nxt)] if nxt else None,
           "min_trades_first_stage": mins[str(stages[0])]}
    return {"meta": {"module": "demo-results", "version": "1.0.0"}, "records": [{
        "id": "demo.xautusdt", "title_ar": "نتائج الحساب التجريبي XAUT (ديمو، فلوس افتراضية)", "unit": "demo", "value": val,
        "stats": {"stages": stages, "stage_min_trades": mins, "full_level": full, "full_dd_pct": dd_limit, "open_trades_marked_at_current_price": True, "update": "manual"},
        "source": {"name": "Demo account summary numbers saved in this repo by hand, not fetched live", "url": "https://github.com/t8e3mp-gold/gold-dashboard/blob/main/docs/RECOMMENDATION_RULES.md"},
        "fetched_at": demo["as_of"], "label": "simulated", "max_age_hours": 72, "checked_against": None}]}

def main():
    d = os.environ["DATA_DIR"]
    doc = build(load(os.path.join(HERE, "demo.json")), load(os.path.join(d, "recommendation.json")), datetime.now(timezone.utc))
    with open(os.path.join(os.environ["OUT_DIR"], "demo-results.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()

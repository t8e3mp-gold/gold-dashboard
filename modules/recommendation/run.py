"""recommendation (R5): computed rules only, display only, no orders, no AI text. Spot, own the asset, buy dips and sell rallies in tranches.
Staged gate (user decision, Nov 28 2026): stages 60, 70, 80, 90, 98 (% win rate). A stage opens for a coin only if some rule has at least STAGE_MIN_TRADES[stage] (100 for the 60 stage, 200 for the others)
out-of-sample trades, a win rate at or above the stage, and a positive TOTAL net after fees; trades that ended by the time stop or were still open at the end of the
data are inside those counts. The 98 stage also needs max drawdown under FULL_DD_PCT. Stages 60 to 90 mean "under observation" only. The stance can leave "wait"
only at 98 (the full recommendation level). Until then the page shows a CONDITIONAL plan (what would have to happen, where the idea is invalid), never a call.
The UI writes the Arabic text from these numbers, so every number on screen is one computed here."""
import json, os
from datetime import datetime, timezone

SYMS = ["XAUT", "BNB", "ETH", "SOL"]
STAGES = (60, 70, 80, 90, 98)
FULL_LEVEL = 98
STAGE_MIN_TRADES = {60: 100, 70: 200, 80: 200, 90: 200, 98: 200}   # user decision Nov 28 2026 (04:00): the 60 stage needs 100, the others 200
FULL_DD_PCT = 20.0
EDGE_MIN_TRADES = STAGE_MIN_TRADES[FULL_LEVEL]   # kept for the old field name used by the page
RT_COST = 0.003          # round trip fee + slippage, same as the backtest
NEAR_ATR = 1.0           # price within this many ATR of a zone counts as "near"

def load(p):
    with open(p, encoding="utf-8") as f: return json.load(f)

def pick(zones, price):
    above = sorted([z for z in zones if z["mid"] > price], key=lambda z: z["mid"])
    below = sorted([z for z in zones if z["mid"] < price], key=lambda z: -z["mid"])
    near = lambda z: abs(z["mid"] - price) / price <= 0.05
    strong = lambda arr, sgn: sorted([z for z in arr if near(z)], key=lambda z: (-z["strength"], sgn * z["mid"]))[:1]
    return {"res1": above[0] if above else None, "sup1": below[0] if below else None,
            "res_strong": (strong(above, 1) or [None])[0], "sup_strong": (strong(below, -1) or [None])[0]}

def qualifies(row, stage):
    """One rule at one stage. Pure function (tested). Counts include time-stop and still-open trades because the backtest already does."""
    if row["trades"] < STAGE_MIN_TRADES[stage] or row["win_rate"] * 100 < stage: return False
    if row.get("total_net_pct") is None or row["total_net_pct"] <= 0: return False
    if stage >= FULL_LEVEL and row["max_drawdown_pct"] >= FULL_DD_PCT: return False
    return True

def edge(bt):
    """Best out-of-sample rule for the coin and the highest stage any rule clears. bt = backtest record value['strategies']."""
    rows = []
    for k, r in bt.items():
        o = r.get("out_of_sample")
        if o and o.get("trades"): rows.append({"rule": k, "trades": o["trades"], "win_rate": o["win_rate"], "avg_net_pct": o["avg_net_per_trade_pct"], "total_net_pct": o.get("total_net_pct"),
                                               "max_drawdown_pct": o["max_drawdown_pct"], "exits": o.get("exits")})
    best = max(rows, key=lambda x: x["avg_net_pct"]) if rows else None
    stage, rule = 0, None
    for st in STAGES:
        ok = [x for x in rows if qualifies(x, st)]
        if ok: stage, rule = st, max(ok, key=lambda x: x["total_net_pct"])
    return {"proven": stage >= FULL_LEVEL, "stage": stage, "stage_rule": rule, "stages": list(STAGES), "best": best, "rules_tested": len(rows),
            "rules_positive": len([x for x in rows if x["avg_net_pct"] > 0]), "min_trades": STAGE_MIN_TRADES[FULL_LEVEL], "stage_min_trades": {str(k): v for k, v in STAGE_MIN_TRADES.items()}, "full_level": FULL_LEVEL, "full_dd_pct": FULL_DD_PCT}

def buy_plan(pk, price, atr):
    z = pk["sup_strong"] or pk["sup1"]
    if not z or not atr: return None
    tgt = pk["res1"]; inval = z["lo"] - atr
    risk = (z["hi"] - inval) / z["hi"]; out = {"zone_lo": z["lo"], "zone_hi": z["hi"], "zone_why": z["why"][:3], "samples": z["episodes"], "bounces": z["bounces"],
           "confirm": "close_above_zone_1h", "invalidation": round(inval, 6), "risk_pct": round(100 * risk, 3), "dist_pct": round(100 * (price - z["hi"]) / price, 3)}
    if tgt: 
        rew = (tgt["mid"] - z["hi"]) / z["hi"]; out.update({"target": tgt["mid"], "reward_pct": round(100 * rew, 3), "rr_after_fees": round((rew - RT_COST) / (risk + RT_COST), 2)})
    return out

def sell_plan(pk, price, atr):
    tr = [z for z in (pk["res1"], pk["res_strong"]) if z]; seen = []; 
    for z in tr:
        if z["mid"] not in [s["mid"] for s in seen]: seen.append(z)
    if not seen or not atr: return None
    top = max(seen, key=lambda z: z["mid"])
    return {"tranches": [{"mid": z["mid"], "lo": z["lo"], "hi": z["hi"], "dist_pct": round(100 * (z["mid"] - price) / price, 3), "samples": z["episodes"], "bounces": z["bounces"]} for z in sorted(seen, key=lambda z: z["mid"])],
            "hold_rest_above": round(top["hi"] + atr, 6), "note": "sell_in_tranches_if_owned"}

def decide(price, atr, pk, forming, news, ed):
    """Pure function (tested). Returns (stance, reasons). stance in wait | buy_watch | sell_watch."""
    reasons = []
    if ed["stage"] == 0: reasons.append({"code": "no_edge", "best": ed["best"], "tested": ed["rules_tested"], "positive": ed["rules_positive"]})
    elif not ed["proven"]: reasons.append({"code": "stage_observation", "stage": ed["stage"], "rule": ed["stage_rule"], "tested": ed["rules_tested"]})
    if news.get("wait"): reasons.append({"code": "news_wait"})
    if news.get("leak_trap"): reasons.append({"code": "leak_trap"})
    near_sup = bool(pk["sup1"] and atr and (price - pk["sup1"]["hi"]) <= NEAR_ATR * atr)
    near_res = bool(pk["res1"] and atr and (pk["res1"]["lo"] - price) <= NEAR_ATR * atr)
    if near_sup: reasons.append({"code": "near_support"})
    if near_res: reasons.append({"code": "near_resistance"})
    if forming: reasons.append({"code": "forming_bounce"})
    blocked = (not ed["proven"]) or news.get("wait") or news.get("leak_trap")
    if blocked: return "wait", reasons
    if near_sup and forming: return "buy_watch", reasons
    if near_res: return "sell_watch", reasons
    return "wait", reasons

def build(levels, news, backtest, klines, now):
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ"); recs = []
    for s in SYMS:
        lv = next(r for r in levels["records"] if r["id"] == "levels.%susdt" % s.lower())
        nw = next(r for r in news["records"] if r["id"] == "news.%susdt" % s.lower())["value"]["stance"]
        bt = next(r for r in backtest["records"] if r["id"] == "backtest.%susdt" % s.lower())
        price = lv["value"]["price_ref"]; atr = lv["stats"]["atr_1h"]; pk = pick(lv["value"]["zones"], price)
        ed = edge(bt["value"]["strategies"]); forming = lv["value"].get("forming")
        stance, reasons = decide(price, atr, pk, forming, nw, ed)
        recs.append({"id": "recommendation.%susdt" % s.lower(), "title_ar": "التوصية %s (فرضية، عرض فقط)" % s, "unit": "recommendation",
                     "value": {"stance": stance, "reasons": reasons, "edge": ed, "price_ref": price, "price_ref_time": lv["value"]["price_ref_time"], "atr_1h": atr,
                               "buy_plan": buy_plan(pk, price, atr), "sell_plan": sell_plan(pk, price, atr),
                               "news": {"wait": nw["wait"], "leak_trap": nw["leak_trap"], "next_event": nw.get("next_event")},
                               "inputs_time": {"levels": lv["fetched_at"], "news": next(r for r in news["records"] if r["id"] == "news.%susdt" % s.lower())["fetched_at"], "backtest": bt["fetched_at"]}},
                     "stats": {"rules": "docs/RECOMMENDATION_RULES.md", "stages": list(STAGES), "stage_min_trades": {str(k): v for k, v in STAGE_MIN_TRADES.items()}, "full_level": FULL_LEVEL, "edge_min_trades": EDGE_MIN_TRADES, "round_trip_cost": RT_COST, "near_atr": NEAR_ATR},
                     "source": {"name": "levels, news and backtest modules (computed rules, no AI)", "url": "https://github.com/t8e3mp-gold/gold-dashboard/blob/main/docs/RECOMMENDATION_RULES.md"},
                     "fetched_at": ts, "label": "hypothesis", "max_age_hours": 8, "checked_against": None})
    return {"meta": {"module": "recommendation", "version": "1.0.0"}, "records": recs}

def main():
    d = os.environ["DATA_DIR"]
    doc = build(load(os.path.join(d, "levels.json")), load(os.path.join(d, "news.json")), load(os.path.join(d, "backtest.json")), load(os.path.join(d, "klines.json")), datetime.now(timezone.utc))
    with open(os.path.join(os.environ["OUT_DIR"], "recommendation.json"), "w", encoding="utf-8") as f: json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()

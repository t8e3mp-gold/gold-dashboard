"""recommendation (R5): computed rules only, display only, no orders, no AI text. Spot, own the asset, buy dips and sell rallies in tranches.
Honest gate: the stance can leave "wait" only if the backtest found a rule with a proven edge (EDGE_MIN_TRADES or more out-of-sample trades and a
positive average net after fees). Until then the page shows a CONDITIONAL plan (what would have to happen, where the idea is invalid), never a call.
The UI writes the Arabic text from these numbers, so every number on screen is one computed here."""
import json, os
from datetime import datetime, timezone

SYMS = ["XAUT", "BNB", "ETH", "SOL"]
EDGE_MIN_TRADES = 100
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

def edge(bt):
    """Best out-of-sample rule for the coin and whether any rule clears the gate. bt = backtest record value['strategies']."""
    rows = []
    for k, r in bt.items():
        o = r.get("out_of_sample")
        if o and o.get("trades"): rows.append({"rule": k, "trades": o["trades"], "win_rate": o["win_rate"], "avg_net_pct": o["avg_net_per_trade_pct"], "max_drawdown_pct": o["max_drawdown_pct"]})
    best = max(rows, key=lambda x: x["avg_net_pct"]) if rows else None
    proven = [x for x in rows if x["trades"] >= EDGE_MIN_TRADES and x["avg_net_pct"] > 0]
    return {"proven": bool(proven), "best": best, "rules_tested": len(rows), "rules_positive": len([x for x in rows if x["avg_net_pct"] > 0]), "min_trades": EDGE_MIN_TRADES}

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
    if not ed["proven"]: reasons.append({"code": "no_edge", "best": ed["best"], "tested": ed["rules_tested"], "positive": ed["rules_positive"]})
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
                     "stats": {"rules": "docs/RECOMMENDATION_RULES.md", "edge_min_trades": EDGE_MIN_TRADES, "round_trip_cost": RT_COST, "near_atr": NEAR_ATR},
                     "source": {"name": "levels, news and backtest modules (computed rules, no AI)", "url": "https://github.com/t8e3mp-gold/gold-dashboard/blob/main/docs/RECOMMENDATION_RULES.md"},
                     "fetched_at": ts, "label": "hypothesis", "max_age_hours": 8, "checked_against": None})
    return {"meta": {"module": "recommendation", "version": "1.0.0"}, "records": recs}

def main():
    d = os.environ["DATA_DIR"]
    doc = build(load(os.path.join(d, "levels.json")), load(os.path.join(d, "news.json")), load(os.path.join(d, "backtest.json")), load(os.path.join(d, "klines.json")), datetime.now(timezone.utc))
    with open(os.path.join(os.environ["OUT_DIR"], "recommendation.json"), "w", encoding="utf-8") as f: json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()

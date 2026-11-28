"""watch: where the last CLOSED UTC daily candle of XAUT sits against two levels the user chose.
The levels are the user's own hypotheses (not computed, not predictions). The closes are measured from Binance daily candles.
State: above (last close over the upper level), below (last close under the lower level), between. Streaks count consecutive
closed daily candles on the same side, newest first. No signal, no advice, no prediction."""
import json, os
from datetime import datetime, timezone

SYM = "XAUT"
UPPER, LOWER = 3660.0, 3600.0   # user levels, set 2026-11-28
DAY_MS = 86400000
SHOW = 10
LIMIT_PCT = 0.05

def load(p):
    with open(p, encoding="utf-8") as f: return json.load(f)

def closed_days(k1d, now_ms):
    """Daily candles whose 24 h are over. The newest candle from the API can still be forming."""
    return [c for c in k1d if c[0] + DAY_MS <= now_ms]

def streak(closes, side, upper, lower):
    n = 0
    for c in reversed(closes):
        if (side == "above" and c > upper) or (side == "below" and c < lower): n += 1
        else: break
    return n

def state_of(close, upper, lower):
    return "above" if close > upper else "below" if close < lower else "between"

def build(klines_doc, now):
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ"); now_ms = int(now.timestamp() * 1000)
    km = {r["id"]: r for r in klines_doc["records"]}
    k1d = km["kline.%susdt.1d" % SYM.lower()]["value"]; k1h = km["kline.%susdt.1h" % SYM.lower()]["value"]
    days = closed_days(k1d, now_ms)
    closes = [c[4] for c in days]; last = days[-1]
    st = state_of(last[4], UPPER, LOWER)
    h = {c[0]: c for c in k1h}.get(last[0] + DAY_MS - 3600000)
    ck = None
    if h:
        d = round(abs(h[4] - last[4]) / last[4] * 100, 4)
        ck = {"source": "1h candles, last hour of the same day", "url": "https://data-api.binance.vision/api/v3/klines",
              "value": h[4], "diff_pct": d, "ok": d <= LIMIT_PCT, "limit_pct": LIMIT_PCT}
    val = {"levels": {"upper": UPPER, "lower": LOWER, "set_by": "user", "set_on": "2026-11-28"},
           "last_close": {"open_time": last[0], "close": last[4]}, "state": st,
           "streak_above": streak(closes, "above", UPPER, LOWER), "streak_below": streak(closes, "below", UPPER, LOWER),
           "closes": [[c[0], c[4]] for c in days[-SHOW:]]}
    return {"meta": {"module": "watch", "version": "1.0.0"}, "records": [{
        "id": "watch.xautusdt", "title_ar": "متابعة الإغلاق اليومي XAUT (مستويات المستخدم)", "unit": "watch", "value": val,
        "stats": {"closed_days_available": len(days), "day": "UTC", "note": "last closed candle only; a forming candle is never used"},
        "source": {"name": "klines module (Binance public data), daily candles closed at 00:00 UTC", "url": "https://data-api.binance.vision/api/v3/klines"},
        "fetched_at": ts, "label": "measured", "max_age_hours": 8, "checked_against": ck}]}

def main():
    d = os.environ["DATA_DIR"]; k = load(os.path.join(d, "klines.json"))
    now = datetime.strptime(k["records"][0]["fetched_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    doc = build(k, now)
    with open(os.path.join(os.environ["OUT_DIR"], "watch.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()

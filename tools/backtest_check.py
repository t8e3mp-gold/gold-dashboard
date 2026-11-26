"""Sanity gate for an automatically re-run backtest (used by the Backtest workflow). Exit 1 = do not commit the new results."""
import json, sys
MIN = {"XAUTUSDT": 3000, "ETHUSDT": 10000, "SOLUSDT": 10000, "BNBUSDT": 10000}
def check(res):
    errs = []
    for s, n in MIN.items():
        r = res.get("symbols", {}).get(s)
        if not r: errs.append("missing " + s); continue
        if r["candles"] < n: errs.append("%s only %d candles" % (s, r["candles"]))
        if set(r["strategies"]) != set(res.get("strategies", {})): errs.append(s + " strategies differ")
        for k, v in r["strategies"].items():
            if v.get("chosen") and "out_of_sample" not in v: errs.append("%s/%s no out-of-sample" % (s, k))
    return errs
if __name__ == "__main__":
    e = check(json.load(open(sys.argv[1]))); print("OK" if not e else "REJECT: " + "; ".join(e)); sys.exit(1 if e else 0)

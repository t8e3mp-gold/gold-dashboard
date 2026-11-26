"""STANDBY ONLY. NOT wired into the pipeline, NOT in modules/registry.json, NOT referenced by any workflow. OFF by default.

Backup for the two modules that have no live fallback (flow and intent) when Binance's API blocks the runner (HTTP 451).
It rebuilds flow.json and intent.json from Binance's public daily archive files (https://data.binance.vision), which are
published once a day, so the data is DELAYED by up to about a day. It says so: the record time is the time of the last
candle it has (not "now"), so the page shows the true age and the stale badge appears by itself (8 h limit).
Honest limits: the archive is on a different host than the API, but it is still Binance, so it is not independent of a
Binance-wide block. No second source, so checked_against is empty (same as the backtest records).

How to switch it on (a human decision, see docs/STANDBY_ARCHIVE_FALLBACK.md): run
  DATA_DIR=<dir with klines.json> OUT_DIR=<output dir> python standby/archive-fallback/archive_fallback.py
It reads the repo's flow and intent code for the record shapes, so the output matches the live modules.
"""
import csv, importlib.util, io, json, os, sys, urllib.request, zipfile
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
A = "https://data.binance.vision/data/spot/"
SYMS = ["XAUT", "BNB", "ETH", "SOL"]
H, D = 3600_000, 86400_000
SRC = {"name": "Binance public daily archive files (delayed up to about a day)", "url": "https://data.binance.vision/"}

def load(name, rel):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def get_csv(url):
    """Rows of the single CSV inside a Binance archive zip, or None if the file does not exist yet (404)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "gold-dashboard-standby"})
        with urllib.request.urlopen(req, timeout=30) as r: data = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404: return None
        raise
    z = zipfile.ZipFile(io.BytesIO(data))
    return list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8")))

def ms(x):  # archive timestamps are microseconds from 2025 on, milliseconds before
    x = int(x); return x // 1000 if x > 10 ** 14 else x

def kl_rows(sym, tf, now, days, months=0, fetch=get_csv):
    """Closed candles [open_ms, open, high, low, close, volume, close_ms, ..., taker_buy_base at [9]] from daily (and monthly) files."""
    out = {}
    today = now.date()
    srcs = []
    if months:
        first = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        y, m = first.year, first.month
        for _ in range(months):
            srcs.append("%smonthly/klines/%sUSDT/%s/%sUSDT-%s-%04d-%02d.zip" % (A, sym, tf, sym, tf, y, m)); m -= 1
            if m == 0: y, m = y - 1, 12
        start = today.replace(day=1)
        srcs += ["%sdaily/klines/%sUSDT/%s/%sUSDT-%s-%s.zip" % (A, sym, tf, sym, tf, (start + timedelta(days=i)).isoformat()) for i in range((today - start).days + 1)]
    else:
        srcs = ["%sdaily/klines/%sUSDT/%s/%sUSDT-%s-%s.zip" % (A, sym, tf, sym, tf, (today - timedelta(days=i)).isoformat()) for i in range(days, -1, -1)]
    for u in srcs:
        rows = fetch(u)
        for r in rows or []:
            t = ms(r[0]); c = ms(r[6]) + (1 if ms(r[6]) % 1000 == 999 else 0)
            if c > int(now.timestamp() * 1000): continue      # never a forming candle
            out[t] = [t, float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]), c, 0, 0, float(r[9])]
    return [out[k] for k in sorted(out)]

def build_flow(flow_mod, series, now):
    recs, notes, last = [], {}, 0
    for s in SYMS:
        for tf, step in (("1h", H), ("1d", D)):
            c = series[(s, tf)][-flow_mod.N:]
            if len(c) < 200: raise RuntimeError("%s %s: only %d candles in the archive" % (s, tf, len(c)))
            for i in range(1, len(c)):
                if c[i][0] - c[i - 1][0] != step: raise RuntimeError("%s %s: gap in archive at %d" % (s, tf, i))
            c2 = flow_mod.parse([[r[0], 0, 0, 0, 0, r[5], r[6] - 1, 0, 0, r[9]] for r in c], 10 ** 18)
            last = max(last, c[-1][6])
            recs.append({"id": "flow.%susdt.%s" % (s.lower(), tf), "value": flow_mod.to_flow(c2),
                         "unit": "flow [open_time_ms, volume, buy_volume, sell_volume, delta, cvd]", "source": SRC,
                         "fetched_at": datetime.fromtimestamp(c[-1][6] / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "label": "measured", "max_age_hours": 8, "checked_against": None,
                         "title_ar": "تدفق %s (%s) من ملفات الأرشيف" % (s, "ساعة" if tf == "1h" else "يوم")})
    return {"meta": {"module": "flow", "version": "1.0.0-archive", "notes": {"all": "built from Binance daily archive files, delayed up to about a day, no second source"}}, "records": recs}, last

def trades_from_archive(sym, t0, t1, fetch=get_csv):
    day = datetime.fromtimestamp(t0 / 1000, timezone.utc).date(); out = []
    for d in {day, datetime.fromtimestamp((t1 - 1) / 1000, timezone.utc).date()}:
        rows = fetch("%sdaily/aggTrades/%sUSDT/%sUSDT-aggTrades-%s.zip" % (A, sym, sym, d.isoformat()))
        if rows is None: raise RuntimeError("aggTrades archive for %s not published yet" % d)
        for r in rows:
            t = ms(r[5])
            if t0 <= t < t1: out.append((t, float(r[2]), r[6] != "True"))      # taker is the buyer when buyer is not the maker
    return out

def main(argv=None, fetch=get_csv):
    out_dir = os.environ["OUT_DIR"]; now = datetime.now(timezone.utc)
    flow_mod = load("flow_run", "modules/flow/run.py"); intent_mod = load("intent_run", "modules/intent/run.py")
    series = {}
    for s in SYMS:
        series[(s, "1h")] = kl_rows(s, "1h", now, 14, fetch=fetch)
        series[(s, "1d")] = kl_rows(s, "1d", now, 0, months=11, fetch=fetch)
    flow_doc, last = build_flow(flow_mod, series, now)
    t1 = (last_h // H) * H                                   # end of the newest closed hour present for all symbols
    t1 = min(series[(s, "1h")][-1][6] for s in SYMS); t1 = (t1 // H) * H
    kd = {"records": [{"id": "kline.%susdt.1h" % s.lower(), "value": [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in series[(s, "1h")]]} for s in SYMS]}
    until = datetime.fromtimestamp(t1 / 1000, timezone.utc)
    doc = intent_mod.build(lambda sym, a, b: trades_from_archive(sym, a, b, fetch), kd, flow_doc, until)
    ts = datetime.fromtimestamp(t1 / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for r in doc["records"]:
        r["fetched_at"] = ts; r["source"] = SRC; r["checked_against"] = None
    for name, d in (("flow", flow_doc), ("intent", doc)):
        with open(os.path.join(out_dir, name + ".json"), "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    print("archive fallback wrote flow.json and intent.json; data through", ts)

if __name__ == "__main__":
    main()

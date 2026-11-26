"""news: headlines from free public RSS feeds, scheduled macro events, and two computed flags (wait around events; possible leak/trap).
Nothing here predicts anything. All text is copied from the sources with its time."""
import json, os, re, html, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
try: from zoneinfo import ZoneInfo
except Exception: ZoneInfo = None

SYMS = ["XAUT", "BNB", "ETH", "SOL"]
FEEDS = [("aljazeera-en", "Al Jazeera English", "https://www.aljazeera.com/xml/rss/all.xml", "media"),
         ("aljazeera-ar", "Al Jazeera Arabic", "https://www.aljazeera.net/aljazeerarss/a7c186be-1baa-4bd4-9d80-a84db769f779/73d0e1b4-532f-45ef-b135-bfdff8b8cab9", "media"),
         ("fed", "Federal Reserve press releases", "https://www.federalreserve.gov/feeds/press_all.xml", "official"),
         ("ecb", "ECB press", "https://www.ecb.europa.eu/rss/press.html", "official")]
FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
BEA_URL = "https://www.bea.gov/news/schedule"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
WAIT_BEFORE_H, WAIT_AFTER_H, LEAK_ATR, LEAK_AHEAD_H = 2, 1, 2.0, 2

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (gold-dashboard refresh)"})
    with urllib.request.urlopen(req, timeout=25) as r: return r.status, r.read().decode("utf-8", errors="replace")

def parse_rss(text, limit=40):
    root = ET.fromstring(text.lstrip("\ufeff")); out = []
    for it in root.iter("item"):
        t = (it.findtext("title") or "").strip(); l = (it.findtext("link") or "").strip(); d = it.findtext("pubDate")
        if not t or not d: continue
        try: dt = parsedate_to_datetime(d.strip())
        except Exception: continue
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        out.append({"title": html.unescape(re.sub(r"\s+", " ", t)), "link": l, "published": dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    out.sort(key=lambda x: x["published"], reverse=True); return out[:limit]

def parse_bea(page, now):
    """BEA schedule: '<Month> <day> <h:mm> <AM|PM> N ews <title>' in ET (America/New_York). Year inferred from now."""
    t = re.sub(r"<[^>]+>", " ", page); t = html.unescape(re.sub(r"\s+", " ", t)); out = []
    mo = "|".join(MONTHS)
    for m in re.finditer(r"(%s) (\d{1,2}) (\d{1,2}:\d{2}) (AM|PM) N ews (.+?)(?= (?:%s) \d{1,2} \d{1,2}:\d{2} (?:AM|PM) N ews | Quick Links|$)" % (mo, mo), t):
        mon = MONTHS.index(m.group(1)) + 1; day = int(m.group(2)); hh, mm = map(int, m.group(3).split(":"))
        if m.group(4) == "PM" and hh != 12: hh += 12
        if m.group(4) == "AM" and hh == 12: hh = 0
        try:
            loc = datetime(now.year, mon, day, hh, mm, tzinfo=ZoneInfo("America/New_York"))
            if loc < now - timedelta(days=60): loc = loc.replace(year=now.year + 1)   # the schedule lists upcoming dates; far past means next year
        except Exception: continue
        out.append({"title": m.group(5).strip(), "start": loc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "BEA", "time_assumed": False})
    return out

def parse_fomc(page, now):
    """FOMC meeting days from the Fed calendar page (year heading, month, 'd1-d2'). Statement is on the last day; the hour (14:00 ET) is NOT on the page, so time_assumed is true."""
    out = []
    for ym in re.finditer(r"(\d{4}) FOMC Meetings(.*?)(?=\d{4} FOMC Meetings|$)", page, re.S):
        year = int(ym.group(1)); body = ym.group(2)
        for m in re.finditer(r'fomc-meeting__month[^>]*><strong>([A-Za-z/]+)</strong>.*?fomc-meeting__date[^>]*>([\d\-/ A-Za-z]+?)\*?<', body, re.S):
            mon_name = m.group(1).split("/")[-1]; mon = next((i + 1 for i, n in enumerate(MONTHS) if n.startswith(mon_name[:3])), None)
            last = re.findall(r"\d+", m.group(2))
            if not mon or not last: continue
            try: loc = datetime(year, mon, int(last[-1]), 14, 0, tzinfo=ZoneInfo("America/New_York"))
            except Exception: continue
            out.append({"title": "FOMC statement day", "start": loc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "FOMC calendar", "time_assumed": True})
    return out

def atr_pct(k):
    tr = [max(k[i][2] - k[i][3], abs(k[i][2] - k[i - 1][4]), abs(k[i][3] - k[i - 1][4])) / k[i - 1][4] for i in range(1, len(k))]
    t = tr[-14:]; return sum(t) / len(t)

def stance(now, events, k1h):
    """Pure function (tested). Returns dict: wait (bool), next_event, leak_trap (bool), move_atr, details. now is a UTC datetime."""
    near = None; nxt = None
    for e in events:
        st = datetime.strptime(e["start"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if st - timedelta(hours=WAIT_BEFORE_H) <= now <= st + timedelta(hours=WAIT_AFTER_H): near = near or e
        if st > now and (nxt is None or e["start"] < nxt["start"]): nxt = e
    a = atr_pct(k1h); move = k1h[-1][4] / k1h[-3][4] - 1; mv = abs(move) / a if a else 0.0
    ahead = False
    if nxt:
        st = datetime.strptime(nxt["start"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc); ahead = st - now <= timedelta(hours=LEAK_AHEAD_H)
    leak = bool(ahead and mv >= LEAK_ATR)
    return {"wait": bool(near), "event_in_window": near, "next_event": nxt, "leak_trap": leak, "move_2h_pct": round(100 * move, 3), "atr_1h_pct": round(100 * a, 3), "move_in_atr": round(mv, 2)}

def build(feeds_res, events, klines, now):
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ"); cutoff = (now - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    heads = []
    for fid, name, kind, items in feeds_res:
        heads += [dict(x, feed=fid, feed_name=name, kind=kind) for x in items if x["published"] >= cutoff and x["published"] <= ts][:6]
    heads.sort(key=lambda x: x["published"], reverse=True)
    lo = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"); hi = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ev = sorted([e for e in events if lo <= e["start"] <= hi], key=lambda e: e["start"])
    recs = []
    for s in SYMS:
        k = klines["records"]; k1h = next(r["value"] for r in k if r["id"] == "kline.%susdt.1h" % s.lower())
        st = stance(now, ev, k1h)
        recs.append({"id": "news.%susdt" % s.lower(), "title_ar": "الأخبار والأحداث المجدولة %s" % s, "unit": "news",
                     "value": {"events": ev[:12], "headlines": heads[:14], "stance": st},
                     "stats": {"feeds": {f[0]: {"ok": True, "items": len(f[3])} for f in feeds_res}, "wait_before_h": WAIT_BEFORE_H, "wait_after_h": WAIT_AFTER_H, "leak_atr": LEAK_ATR, "leak_ahead_h": LEAK_AHEAD_H},
                     "source": {"name": "Al Jazeera RSS, Federal Reserve press RSS, ECB press RSS, Fed FOMC calendar, BEA release schedule", "url": "https://www.federalreserve.gov/feeds/press_all.xml"},
                     "fetched_at": ts, "label": "measured", "max_age_hours": 8, "checked_against": None})
    return {"meta": {"module": "news", "version": "1.0.0"}, "records": recs}

def main():
    d = os.environ["DATA_DIR"]; now = datetime.now(timezone.utc); status = {}; feeds_res = []; events = []
    for fid, name, url, kind in FEEDS:
        try:
            code, txt = get(url); items = parse_rss(txt); status[fid] = {"ok": bool(items), "http": code, "items": len(items)}
            if items: feeds_res.append((fid, name, kind, items))
        except Exception as e: status[fid] = {"ok": False, "error": type(e).__name__}
    for key, url, fn in (("fomc", FOMC_URL, parse_fomc), ("bea", BEA_URL, parse_bea)):
        try:
            code, txt = get(url); ev = fn(txt, now); events += ev; status[key] = {"ok": bool(ev), "http": code, "items": len(ev)}
        except Exception as e: status[key] = {"ok": False, "error": type(e).__name__}
    if not feeds_res and not events: raise SystemExit("no news feed and no calendar reachable: " + json.dumps(status))
    with open(os.path.join(d, "klines.json"), encoding="utf-8") as f: kl = json.load(f)
    doc = build(feeds_res, events, kl, now)
    for r in doc["records"]: r["stats"]["feeds"] = status
    with open(os.path.join(os.environ["OUT_DIR"], "news.json"), "w", encoding="utf-8") as f: json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()

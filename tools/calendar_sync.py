"""Self-refresh of modules/news/calendar.json from the BLS public iCal feed (free, no account).
Runs in the Refresh workflow. If BLS refuses or the file does not parse, nothing is changed and the reason is printed (exit 0),
so the committed file stays the fallback (Plan B) and the watchdog flags it when it is older than 40 days.
Only BLS-sourced events (jobs, CPI) are replaced; the BEA schedule (PCE and others) is read live by the news module.
The iCal layout is ASSUMED (VEVENT, SUMMARY, DTSTART); the first real run on the GitHub runner decides whether it works."""
import json, re, sys, urllib.request
from datetime import date, datetime, timedelta, timezone
URL = "https://www.bls.gov/schedule/news_release/bls.ics"
KINDS = [("Employment Situation", "US jobs report (NFP)", "https://www.bls.gov/schedule/news_release/empsit.htm"),
         ("Consumer Price Index", "US CPI inflation", "https://www.bls.gov/schedule/news_release/cpi.htm")]

def fetch(url=URL):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; gold-dashboard-calendar-sync; free public data)", "Accept": "text/calendar,*/*"})
    with urllib.request.urlopen(req, timeout=30) as r: return r.read().decode("utf-8", "replace")

def parse(ics, today):
    """Returns [{title,date,time_et,verified,source}] for future jobs/CPI events inside the next 120 days."""
    text = re.sub(r"\r?\n[ \t]", "", ics); out = []
    for blk in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
        s = re.search(r"^SUMMARY[^:]*:(.*)$", blk, re.M); d = re.search(r"^DTSTART[^:]*:(\d{8})", blk, re.M)
        if not s or not d: continue
        for key, title, src in KINDS:
            if key.lower() in s.group(1).lower():
                dt = datetime.strptime(d.group(1), "%Y%m%d").date()
                if today <= dt <= today + timedelta(days=120):
                    out.append({"title": title, "date": dt.isoformat(), "time_et": "08:30", "verified": True, "source": src})
    seen, uniq = set(), []
    for e in sorted(out, key=lambda e: (e["date"], e["title"])):
        k = (e["date"], e["title"])
        if k not in seen: seen.add(k); uniq.append(e)
    return uniq

def merge(cal, new, today):
    """Keep non-BLS events that are still in the future; replace BLS ones with the fresh list. Returns new calendar dict."""
    last = max((e["date"] for e in new), default=today.isoformat())   # the feed is authoritative up to its last date; later old BLS dates are kept
    keep = [e for e in cal["events"] if e["date"] >= today.isoformat() and ("bls.gov" not in e.get("source", "") or e["date"] > last)]
    cal = dict(cal); cal["events"] = sorted(keep + new, key=lambda e: (e["date"], e["title"])); cal["checked"] = today.isoformat()
    cal["note"] = "BLS events refreshed automatically from the BLS iCal feed by tools/calendar_sync.py on " + today.isoformat() + "; other events as committed. 08:30 America/New_York."
    return cal

def main(path="modules/news/calendar.json"):
    today = datetime.now(timezone.utc).date()
    try: new = parse(fetch(), today)
    except Exception as e: print("calendar_sync: BLS not reachable (%s); file unchanged" % type(e).__name__); return 0
    kinds = {e["title"] for e in new}
    if len(kinds) < 2: print("calendar_sync: feed parsed but jobs/CPI not both found (%d events); file unchanged" % len(new)); return 0
    cal = json.load(open(path, encoding="utf-8")); out = merge(cal, new, today)
    json.dump(out, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False); print("calendar_sync: updated, %d BLS events" % len(new)); return 0

if __name__ == "__main__": sys.exit(main(*sys.argv[1:]))

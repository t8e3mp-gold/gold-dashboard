"""Template module. Copy this folder, change manifest.json, edit compute()."""
import json, os
from datetime import datetime, timezone

def compute(now):
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"meta": {"module": "hello", "version": "1.0.0"},
            "records": [{"id": "hello.last_run", "value": ts, "unit": "utc-time",
                         "source": {"name": "Runner system clock (UTC)",
                                    "url": "https://github.com/t8e3mp-gold/gold-dashboard"},
                         "fetched_at": ts, "label": "measured", "max_age_hours": 48,
                         "checked_against": None}]}

if __name__ == "__main__":
    doc = compute(datetime.now(timezone.utc))
    with open(os.path.join(os.environ["OUT_DIR"], "hello.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

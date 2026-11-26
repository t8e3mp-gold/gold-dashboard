# news (R4)
Free public feeds only, no account, no key. Headlines are shown as they are with source and time; nothing is scored or summarised by AI.
Feeds (Plan A, then Plan B if one is down): Al Jazeera English RSS, Al Jazeera Arabic RSS; Federal Reserve press RSS, ECB press RSS.
Scheduled events: Fed FOMC calendar page (meeting dates) and BEA release schedule (GDP, personal income and outlays) with their ET times.
If BLS (CPI, jobs) is needed: bls.gov blocks our fetch (HTTP 403 checked Nov 26), so it is not used. Plan B is the BEA and Fed calendars above. The Egyptian central bank site rejects automated requests (checked Nov 26), not used.
Rules (computed, labelled hypothesis): stance "wait" from 2 h before to 1 h after a scheduled event. "Possible leak or trap" when an event is within the next 2 h and the last 2 closed 1h candles moved by 2 ATR or more. The official release is confirmation, not the first signal.
Per-feed status (HTTP result, item count) is published in stats so a blocked feed is visible, never hidden. The module fails if no feed and no calendar worked.

# Gaps list (current and future), each with Plan A / B / C

Status words: open, mitigated, closed. Updated Nov 25 2026 after B2.

| # | Gap | Status | Plan A | Plan B | Plan C | Switch trigger |
|---|---|---|---|---|---|---|
| G1 | The 0.5% source-difference flag has never fired on live data (tested with fake inputs and a simulated page only) | open | Keep unit tests plus the UI simulation; log every real cross-check diff in the data so the first real flag is visible | Add a weekly "flag drill" in CI that feeds a 1% mismatch through the real module code | Compare with a third source (Gate.io) when the flag fires, to see which side is wrong | First real flag, or 30 days without one |
| G2 | Page prices are only as fresh as the last refresh (up to 6 h without session refreshes) | mitigated | 12 session-time refreshes plus the 4/day keeper (docs/SMART_REFRESH.md) | Page shows the age and a stale badge on every price; stale after 8 h | Browser-side live prices (G3) | Age over 8 h |
| G3 | No live in-browser prices yet | closed Nov 25 (B1b, page v7) | Browser fetch from the Binance mirror, labelled live, every 10 s while the page is open (planned in B1b) | Same fetch from OKX | Show the last refresh value only, labelled with its age | Browser fetch blocked by CORS or error |
| G4 | GitHub's own scheduler did not fire on Nov 25 (0 scheduled runs) | open | Instinct wakes dispatch the refresh (proven) | GitHub cron 05:17 UTC (unproven until Nov 26) | Manual button in the footer | Data older than 2 h at a session event |
| G5 | Repo growth: each refresh rewrites the candle file (about 135 KB) | open | Watch repo size monthly; git delta-compresses most of it | Keep only 300 candles per series (already) and prune old data commits by squashing history yearly | Move data to GitHub Releases assets or an orphan data branch | Repo over 200 MB |
| G6 | Short history: XAUT daily has only 244 days (listing is new) | accepted | Use what exists; backtests must say the sample size | Use Gate.io or OKX older history to extend, labelled | Use gold spot (XAU) data as a proxy, labelled hypothesis | Backtest needs more than 244 days |
| G7 | OKX daily bars: default bar opens 16:00 UTC; found in testing, fixed by requesting UTC bars | closed | 1Dutc bars | none needed | none | n/a |
| G8 | Candle volume differs between exchanges (each is its own market) | open | Cross-check closes only, show volume as the primary source's | Compare volumes with a larger tolerance and show it | Do not use cross-exchange volume | A volume-based module (B3) starts |
| G9 | Real-device proof: user locked the phone 2 minutes, reopened, live prices updated (Nov 25 23:13 Cairo). Offline mode and phone-clock behaviour still not tested on a device | closed for background/resume; offline open | The user's 2-step phone test | Headless-browser tests in CI | n/a | User reports a failure |
| G10 | Public APIs can block runners (HTTP 451) or change shape | open | Mirror, OKX, Gate.io fallbacks with validation (done for B1, B2) | Binance public daily archive files | Last good data stays published, flagged stale | Source error in the module report |
| G11 | AI text without a free no-card model | open | Template text with computed numbers only | Placeholder-and-validator design when a free model exists | No AI text | B8 |
| G12 | Holiday and early-close calendar for the smart refresh is my own list | open | Review each January against exchange calendars | Extra refresh on a holiday is harmless; only the notice is skipped | Use a free calendar API | Any wrong notice |
| G13 | B3 aggTrades check skipped for ETH 1h (more than 15 pages of trades per hour); other 1h series and all 1d series are checked | open | Keep the cap, show "no independent check" on the card | Check a shorter slice (last 10 minutes) for ETH | Use Binance daily aggTrades archive files [R-20261125-04] | A check mismatch, or the cap hit for XAUT |
| G14 | Delta is taker side on Binance only; it is not trader intent and other exchanges can differ | accepted | Label on the card says so | Compare the sign of delta with OKX trades sample (500 recent) | Do not use delta alone for signals; B7 backtest decides if it has value | A strategy depends on delta |
| G15 | CVD is cumulative from the start of the 300-candle window, so its level moves when the window moves | accepted | Show it as "from window start" | Store a persistent running total in a history file | Use delta only | CVD used in a signal |
| G16 | intent module (large-trade share, size distribution, price/delta divergence) is hypothesis only: cut-offs (99th percentile; 0.3% price, 5% delta) are arbitrary; history has 3-9 events and every interval contains 50% | open | Show with sample size and 95% interval; no signal use | Hide the cards if aggTrades fails (last good data stays, flagged stale) | Remove the module; delta and profile remain | B7 out-of-sample test shows no edge |
| G17 | volume-profile (B4) is an approximation: 1m candle volume spread evenly over high-low; window is 1439 minutes. Order book is browser-only, live, never in a backtest | accepted | Labelled approximation | aggTrades-based profile for XAUT only | Hide the profile | A strategy depends on it |
| G18 | Two prices for one coin on one page (live card and saved snapshot) confused the auditor | closed Nov 25 (v12) | Snapshot cards titled "saved snapshot, not live" with an explanatory line | Merge into one card later | n/a | User still confused |
| G19 | Flow on closed hours can look bearish while the open hour rises | mitigated (v12 note) | Note on every flow card: open hour not counted | Show the open hour as a separate partial bar (needs a browser kline fetch) | n/a | User asks for it |
| G20 | Display wording: English fragments, UTC-only times, unlabelled order-book percent | closed Nov 25 (v12) | Arabic source names, Cairo time with UTC second, imbalance and spread wording, per-coin band warning; UI test fails on any Latin word in source lines | n/a | n/a | New text added without the test |

## Pre-mortem of the whole system (Nov 25 2026)

Likelihood / impact: L = low, M = medium, H = high. "Fixed now" says what is done today versus a plan only.

| # | Area | Cause of failure | How it shows up | L / I | Plan A | Plan B | Plan C | Fixed now? |
|---|---|---|---|---|---|---|---|---|
| P1 | Refresh | Nothing triggers refreshes: Instinct wakes stop (task expires, platform issue) and GitHub cron stays unproven (G4) | Data age grows, stale badge and banner after 8 h and 26 h | M / H | 12 session wakes plus 4/day keeper | GitHub cron 05:17 UTC (check Nov 26 morning) | Footer manual button for the user | Mitigated; cron unproven until Nov 26 |
| P2 | Refresh | Run takes longer than the module limit as aggTrades pages grow (full run is about 107 s; intent limit 240 s) | Module fails, last good data stays flagged stale | M / M | Page caps and per-module timeouts | Reduce the window or skip the check, labelled | Drop the module | Mitigated |
| P3 | Refresh | Two runs overlap (wake plus keeper, or push plus refresh) and one overwrites or fails to push data | Failed run in Actions, or lost update | M / L | Wakes skip dispatch if data is newer than 20 min | Refresh runs are serialized (concurrency group refresh); unpack and refresh use different groups, so a push race is possible but not seen yet | Rerun by hand | Mitigated for refresh vs refresh only |
| P4 | Repo and Pages | GitHub account locked, 2FA prompt, or the saved browser session expires (I push through the browser; no token allowed) | I cannot push; site keeps serving the last version | M / H | Saved login in the cloud browser; vault request to the user if sign-in needed | The user pushes the bundle by hand from the phone | Site keeps running on the last data | Open, plan only |
| P5 | Repo and Pages | Repo growth (G5), Pages soft bandwidth limit, Actions minutes | Slow clones, deploy errors | L / L | Public repo: standard runners are free; watch size monthly | Squash data history yearly | Move data to a release asset | Open, low |
| P6 | Repo and Pages | Old page cached on the phone (service worker) | User sees old code with new data | M / M | Version banner when data expects a newer page (done) | Cache-busted fetches (done) | Hard reload instruction | Mitigated |
| P7 | Data sources | Binance mirror blocks the runner (451), changes shape, or removes the XAUT pair | Module fails; fallbacks OKX and Gate.io for prices and candles | M / H | Fallbacks with validation | Binance daily archive files | Last good data, flagged stale | Mitigated for prices and candles; aggTrades has no fallback |
| P8 | Data sources | Browser live calls blocked (CORS change, rate limit, ad blocker, country block) | Live card shows a warning and falls back down the chain | M / M | Three sources in the browser (tested down one by one) | Show the snapshot with its age | Hide the live card | Mitigated and tested |
| P9 | Data sources | Free APIs rate-limit at our polling (10 s, 4 coins, order book plus prices) | 429 errors in the warning line | L / M | Polling only while the page is open and visible | Slow to 30 s on errors (not built) | Pause live views | Open, low |
| P10 | Data correctness | Sources disagree for real (the 0.5% flag has never fired, G1) or the check silently stops | No flag when there should be one | M / H | Unit tests plus UI simulation; real diffs logged | Weekly drill in CI | Show "no independent check" | Open |
| P11 | Data correctness | Timestamps and clocks: phone clock wrong, UTC vs Cairo confusion | Wrong ages or times | L / M | Server-time offset for ages; Cairo time first, UTC second (done v12) | n/a | n/a | Closed |
| P12 | Intent and signals | Hypotheses read as advice; small samples; thresholds tuned to history | False confidence | H / H | Labels, sample sizes, intervals, "not intent" notes | B7 out-of-sample backtest before any use | Remove the module | Mitigated; nothing meets 98% yet |
| P13 | Demo trading agent (not built yet) | Look-ahead bias, ignoring fees and slippage, overfitting, thin XAUT history (244 days) | Great backtest, bad live demo | H / H | Walk-forward test, fees in every result, sample size shown, demo money only | Paper-trade for weeks before any claim | No recommendation shown | Not built; rules recorded |
| P14 | Alerts | No alert channel besides main's WhatsApp; session notices depend on the wake | A missed notice or a wrong holiday notice | M / L | Notice sent at pre-event wakes | Keeper reports failures only | None | Open; holiday list is my own (G12) |
| P15 | Phone side | Safari pauses background tabs, offline, low data, old iOS | Live prices stop when the tab is hidden; stale badge shows | H / L | Page resumes on visibility; age shown | Offline mode shows last copy | n/a | Mitigated; no real-device proof (G9) |
| P16 | Phone side | RTL or font problems in Arabic text; long Latin strings overflow | Broken layout | M / L | UI test checks overflow at 390 px and Latin words | Screenshot check per release | n/a | Mitigated |
| P17 | Policy and cost | A free tier changes or a service asks for a card | Feature stops | L / M | Free tools only; no accounts beyond the repo | Swap the host (static files work on any host) | Run from the phone | Open, low |
| P18 | Agent side | My run time or context limit cuts a push half-way | Half-done work | M / M | Work in /downloads/gd2 with docs; bundle pushes are atomic; keeper unaffected | Continue from the docs and the wake prompt | n/a | Mitigated |
| P19 | Privacy | A secret, email or address lands in the public repo | Public leak | L / H | scan.py before every push; noreply author | Rotate and rewrite history | n/a | Mitigated |

## Levels and backtest (added Nov 26)
- G21 Levels are hypotheses: zones come from past data with small samples (3-9 touches). The backtest (docs/BACKTEST_R1.md) found no positive edge after fees. Status: mitigated by labels and by showing the samples; not solved.
- G22 "Bounce" in levels means price moved at least one ATR away within 6 candles. That is a description of the past, not a prediction. Status: mitigated (disclosed).
- G23 Backtest uses 1h candles only. Order-book walls and intent signals have no history, so they are untested. Status: open (needs the forward log R6).
- G24 Backtest tests 4 rules x up to 3 settings x 24 exits on the first 60% and reports the best on the last 40%. More rules tried means more chance of a lucky result. All were negative, so this did not flatter the result. Status: mitigated.
- G25 Backtest results are a committed file rebuilt by running modules/backtest/r1.py (needs network), not on every refresh. The page shows the run time. Status: mitigated.
- G26 News coverage: BLS (CPI, jobs) returns HTTP 403 to automated fetches and the Egyptian central bank rejects them (checked Nov 26), so the big US inflation and jobs dates are not in the calendar. Only FOMC and BEA dates are. Status: open. Plan B ideas: another free official calendar; the user can add dates by hand.
- G27 FOMC statement hour (14:00 New York) is not on the Fed page; it is assumed and marked as assumed. Status: mitigated.
- G28 Headlines are shown as published and are not scored. The leak/trap flag is a simple rule (event within 2 h and a 2-candle move of 2 ATR or more), untested on history. Status: hypothesis.
- G29 Feeds were reached from my machine; they must also work from the GitHub runner. The page names any feed that failed in the last refresh. Status: verify on first live refresh.
- G30 Recommendation: all 4 coins are "wait / no proven edge" because no backtested rule cleared the gate (100+ out-of-sample trades and positive net after fees). Reward to risk after fees is below 1 for every current buy plan. Status: honest, not solved. The page does not claim an edge it does not have.
- G31 News calendar file (calendar.json) is hand-committed from the calendar agent's checks (BLS blocks automated fetches). Dates need re-checking; the January 2027 PCE date is unverified and left out. Status: mitigated.
- G32 Forward log (R6): it logs the recommendation about hourly and scores each entry after 24 real closed 1h candles, net of 0.3% costs. The first scores appear about 24h after the first entry (logged 2026-11-26). Entries one hour apart overlap, so the page also shows independent days. A sample this small proves nothing; 98% over 1000+ trades needs months. Status: measuring, not solved.
- G33 Forward log only records when a Refresh runs (cron plus session wakes). A missed refresh means a missing hour, never an edited record (the runner rejects any change to old records). If the log file were deleted by hand, history would be lost; git history keeps it. Status: mitigated.
- G34 Forward scoring is conservative where one candle touches both invalidation and target (counted as invalidation) and cannot see inside a candle. Open positions at 24h are marked to the close. Status: disclosed.

## Standing project review (rule from the user, Nov 26 2026: review, then current gaps, future gaps, ways it could fail, and the fix for each)
Build status at review time: all planned modules built and live (price, klines, flow, volume profile, intent, cross-check log, levels, backtest R1, news R4, recommendation R5, forward log R6). Not complete: no trading rule has a proven edge; forward log has 0 scored entries; leak/trap flag never seen on real data.

Review of what exists (checked today): module tests pass for news, recommendation, backtest, levels, forward-log; UI test passes (one timing flake in the "timestamps do not wrap" check on one run, passed on rerun and in a direct all-tabs probe); scan clean; live Refresh at 10:05Z, all 12 modules ok.

### Current gaps (exist now)
- R1 No edge: 16 of 16 rule/coin combos negative after 0.3% costs out of sample. Fix: keep the gate; test new rule families (R1b) only with the same split; never lower the gate. The page says wait.
- R2 Backtest is run by hand, not by the Refresh (it needs network and is slow), so results.json can go stale. Fix: show its date on the page (done via the card time) and add a stale warning when older than 30 days (to build); re-run monthly.
- R3 News calendar is hand-committed from the calendar agent; BLS blocks fetches. Fix: re-check on the first of each month against the official pages; add an "age of calendar file" line on the news card (to build). Plan B: BEA and FOMC feeds already automatic.
- R4 Klines have one publishing source (data-api.binance.vision). Cross-check compares with OKX, but if Binance fails the module goes stale rather than switching. Plan B: build an OKX-backed klines fallback module (to build, free public API).
- R5 Forward log: tiny sample, overlapping hourly entries, intra-candle order unknown. Fix: disclosed on the page; judge only by independent days and after 1000+ entries.
- R6 The leak/trap rule is untested on real events. Fix: first real event (NFP Dec 4) is the test; record what it did in docs.

### Future gaps (will appear)
- F1 Data growth: forward-log adds about 4 records an hour, about 100 a day (roughly 60 KB a day, 20 MB a year) in one JSON file the page downloads. Fix before it hurts: when the file passes 1 MB, split by month (archive file per month, summary reads all), keep append-only checks per file.
- F2 GitHub disables scheduled workflows in a repo after 60 days without repo activity. Refresh data commits are expected to count as activity (not verified), but if commits stop the schedule can stop silently. Fix: the keeper wake already dispatches Refresh when meta is older than 5h and reports; keep it.
- F3 DST: US clocks change in March 2027 (Cairo/UTC offset to NY changes from 7h to 6h, and Egypt DST rules also apply). Calendar items are stored in UTC with ET source time; the "assumed time" markers and the session wakes (set in market timezones) follow local rules. Fix: check the first week after each DST change.
- F4 Free-tier limits: Actions minutes and Pages bandwidth are free for a public repo but can change. Plan B: run the same pipeline locally (runner.py works on any machine) and publish the data folder by hand.
- F5 Browser-only push path (no token) depends on the GitHub web editor layout. Fix: if the layout changes the bundle push fails loudly (no commit appears); Plan B is the file upload page.
- F6 Calendar dates expire: after Jan 13 2027 CPI and Jan 8 NFP the file has no US dates. Fix: refill monthly (see R3).

### Ways it could fail in the future, with the fix
- A feed or API changes format: module goes failed or stale, page shows it by name, other modules keep running (runner isolates modules). Fix: per-module tests plus the daily 08:30 health check.
- A bug makes a wrong number look fine: every number carries source and time, cross-checks run, AI text may cite only computed numbers. Residual: both sources wrong the same way. Fix: keep OKX/Gate cross-checks on.
- Overfitting by testing many rules: the best-of-24 setting is judged on the held-out 40%. Residual: repeated looks at the same held-out data. Fix: the forward log is the real out-of-sample test; trust it over R1.
- The user reads "wait" as a bug or reads a conditional plan as advice: labels say hypothesis and "not a recommendation". Fix: keep wording; the decision and the Sharia ruling stay his.
- Public repo leak of private data: scan.py runs on every push (clean today). Fix: keep it mandatory.

### Autonomy fixes (user's standing rule Nov 26: the project runs itself, manual steps near zero)
- A1 CORRECTION to R4 above: klines already had automatic fallback (Binance mirror, then OKX, then Gate.io, with cross-check). The "no fallback" claim was wrong. Nothing to build.
- A2 Refresh runs by itself every 3 hours (GitHub cron `17 */3 * * *`), no longer daily. Instinct session wakes remain as extra runs, not as the only trigger. Status: built; proof = scheduled runs seen.
- A3 Backtest re-runs by itself weekly (workflow Backtest, Sunday 03:41 UTC, Binance public data). Results are committed only if tools/backtest_check.py passes (4 coins, enough candles, out-of-sample present), then Refresh is dispatched so the recommendation uses them. Failure keeps the old results and turns the run red. Status: built; proof = first run.
- A4 Calendar self-refresh: tools/calendar_sync.py tries the free BLS iCal feed on every Refresh and rewrites only BLS jobs/CPI events. The iCal layout is an ASSUMPTION and BLS returned 403 from here, so it is unproven from the runner. If BLS refuses, the committed file stays (Plan B) and the watchdog flags it after 40 days. Plan C: calendar agent re-check monthly. Status: mitigated, not solved until a run shows "updated".
- A5 Self-heal and alert: the Watchdog (every 6h) now dispatches Refresh itself if data is older than 6h, and goes red (GitHub emails the owner) on: data older than 26h, a failed module, a site behind the repo, a failed scheduled refresh, calendar file older than 40 days, backtest older than 21 days. Status: built.
- A6 Forward-log monthly split: NOT built yet (file is small until it passes about 1 MB; trigger written in F1).
- A4 UPDATE (first live run, Nov 26 12:23 Cairo): calendar_sync WORKED from the GitHub runner. BLS iCal was reachable; it updated calendar.json (jobs Dec 4, CPI Dec 10, same as the calendar agent's checks). The feed did not list the Jan 8 and Jan 13 2027 dates, so the first version dropped them. Fixed: old BLS dates later than the feed's last date are kept. Status: automatic, proven once.

## Update 2026-11-26 (monthly split, A6 built)
| # | Gap / failure mode | Fix | Manual override |
|---|---|---|---|
| G35 | Forward log grows without limit and slows the phone page | tools/archive_logs.py moves records older than 45 days to data/archive/ monthly (workflow archive.yml); counters kept in data/forward-archive.json so all-time totals stay right; the page never downloads forward-log, forward-score or forward-archive (HEAVY skip in app.js) | Run "Archive forward log" from the Actions tab; the script is idempotent |
| G36 | Archive run stops half way | Archive file is written first, counters second, live trim last; re-run skips records already archived | Re-run the workflow |
| G37 | Patterns read as proof of an edge | docs/FORWARD_PATTERNS.md shows counts only, with "sample too small" under 100 per group | none needed |

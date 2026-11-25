# Gaps list (current and future), each with Plan A / B / C

Status words: open, mitigated, closed. Updated Nov 25 2026 after B2.

| # | Gap | Status | Plan A | Plan B | Plan C | Switch trigger |
|---|---|---|---|---|---|---|
| G1 | The 0.5% source-difference flag has never fired on live data (tested with fake inputs and a simulated page only) | open | Keep unit tests plus the UI simulation; log every real cross-check diff in the data so the first real flag is visible | Add a weekly "flag drill" in CI that feeds a 1% mismatch through the real module code | Compare with a third source (Gate.io) when the flag fires, to see which side is wrong | First real flag, or 30 days without one |
| G2 | Page prices are only as fresh as the last refresh (up to 6 h without session refreshes) | mitigated | 12 session-time refreshes plus the 4/day keeper (docs/SMART_REFRESH.md) | Page shows the age and a stale badge on every price; stale after 8 h | Browser-side live prices (G3) | Age over 8 h |
| G3 | No live in-browser prices yet | open | Browser fetch from the Binance mirror, labelled live, every 10 s while the page is open (planned in B1b) | Same fetch from OKX | Show the last refresh value only, labelled with its age | Browser fetch blocked by CORS or error |
| G4 | GitHub's own scheduler did not fire on Nov 25 (0 scheduled runs) | open | Instinct wakes dispatch the refresh (proven) | GitHub cron 05:17 UTC (unproven until Nov 26) | Manual button in the footer | Data older than 2 h at a session event |
| G5 | Repo growth: each refresh rewrites the candle file (about 135 KB) | open | Watch repo size monthly; git delta-compresses most of it | Keep only 300 candles per series (already) and prune old data commits by squashing history yearly | Move data to GitHub Releases assets or an orphan data branch | Repo over 200 MB |
| G6 | Short history: XAUT daily has only 244 days (listing is new) | accepted | Use what exists; backtests must say the sample size | Use Gate.io or OKX older history to extend, labelled | Use gold spot (XAU) data as a proxy, labelled hypothesis | Backtest needs more than 244 days |
| G7 | OKX daily bars: default bar opens 16:00 UTC; found in testing, fixed by requesting UTC bars | closed | 1Dutc bars | none needed | none | n/a |
| G8 | Candle volume differs between exchanges (each is its own market) | open | Cross-check closes only, show volume as the primary source's | Compare volumes with a larger tolerance and show it | Do not use cross-exchange volume | A volume-based module (B3) starts |
| G9 | No real-device proof for offline mode and phone-clock behaviour | open | The user's 2-step phone test | Headless-browser tests in CI | n/a | User reports a failure |
| G10 | Public APIs can block runners (HTTP 451) or change shape | open | Mirror, OKX, Gate.io fallbacks with validation (done for B1, B2) | Binance public daily archive files | Last good data stays published, flagged stale | Source error in the module report |
| G11 | AI text without a free no-card model | open | Template text with computed numbers only | Placeholder-and-validator design when a free model exists | No AI text | B8 |
| G12 | Holiday and early-close calendar for the smart refresh is my own list | open | Review each January against exchange calendars | Extra refresh on a holiday is harmless; only the notice is skipped | Use a free calendar API | Any wrong notice |

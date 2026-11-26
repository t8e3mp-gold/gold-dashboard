# Standby: daily-archive fallback for flow and intent (OFF)

Status: built and tested on an isolated copy only. It is not wired into the pipeline, not in `modules/registry.json`, not referenced by any workflow. Live behaviour is unchanged. Decided by the user: build it, do not apply it.

## What it covers
`flow` (buy/sell volume) and `intent` (trade sizes, divergence) have no live fallback. If Binance's API blocks the runner (HTTP 451), both fail, and the page keeps their last good data flagged stale.
`standby/archive-fallback/archive_fallback.py` rebuilds both from Binance's public daily archive files (data.binance.vision). Record shapes come from the live modules' own code.

## Honest limits
- Delayed: files are published once a day, so the newest data is up to about a day old. Records carry the time of their last candle, so the page shows the true age and the stale badge (8 h limit) appears by itself.
- Same company: a different host than the API, but still Binance. It does not help if Binance as a whole is unreachable.
- No second source: `checked_against` is empty (same as the backtest records).
- Not proven under a real 451 block. Checked against the live API instead: 2265 overlapping candles, 0 differences in volume, buy, sell and delta.

## Test evidence (26 Nov 2026, isolated copy)
- Output passes the repo's schema and envelope validation (0 errors); all 13 records flagged stale (about 20 h old), which is correct.
- `tests/test_archive_fallback.py` (4 checks: microsecond timestamps, forming candle dropped, 404 handled, taker side) runs in CI.

## How to switch it on (a human decision)
1. Run: `DATA_DIR=<dir containing klines.json> OUT_DIR=<output dir> python standby/archive-fallback/archive_fallback.py`
2. To use it automatically, a change to the runner or a new module entry is needed: on flow/intent failure, call this script and publish its output. That change is NOT made. Do it only after the user says so, and add a test first.
3. To switch it off again: remove that call. Nothing else depends on it.

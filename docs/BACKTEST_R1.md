# R1 backtest: support-bounce rule (SIMULATED, research only)

Run: 2026-11-26 11:13 Cairo. Code: modules/backtest/r1.py (tests: modules/backtest/tests/test_r1.py). Raw results: docs/backtest-r1-results.json.
Data: Binance spot 1h klines, closed candles only, https://data-api.binance.vision/api/v3/klines. XAUT from its listing (5,875 candles, about 8 months). ETH, SOL, BNB last 2 years (17,519 candles).

Rule: a candle wicks into a confirmed swing-low support zone (fractal 5, known only 5 candles later, no look-ahead) and closes back above it. Buy at next open. Exit at take-profit, stop or 48 candles. Long only, spot, one position at a time. Cost 0.15% per side (0.1% fee + 0.05% slippage), 0.3% round trip. If one candle touches both stop and target, the stop counts.
Method: 24 parameter sets (take-profit 0.5 to 2%, stop 1 to 4%, minimum touches 1 or 2) tried on the first 60% of time only. The best in-sample set (at least 20 trades) is reported on the last 40% (out-of-sample). Baseline: enter whenever flat with the same exits.

| Coin | Trades OOS | Win rate OOS (95% range) | Avg net per trade | Max drawdown | Baseline avg net |
|---|---|---|---|---|---|
| XAUT | 65 | 29.2% (19.6-41.2) | -0.47% | 29.0% | -0.52% |
| ETH | 145 | 44.1% (36.3-52.3) | -0.50% | 52.6% | -0.36% |
| SOL | 245 | 38.8% (32.9-45.0) | -0.33% | 57.4% | -0.36% |
| BNB | 377 | 39.8% (35.0-44.8) | -0.30% | 69.4% | -0.33% |

Reading: no coin is positive after fees, even in-sample (best in-sample average was already negative everywhere). Levels did slightly better than the baseline on XAUT, SOL and BNB and worse on ETH. The gaps are inside the noise. Target (98% over 1000+ trades, positive net, drawdown under 20%) is not met: win rates are 29-44%, and the largest sample is 377 trades.
Limits: one rule only; 1h candles only (no order-book walls in history); XAUT sample is small; the grid itself is a small multiple-testing risk; a different exit design (tranches, scaling) is not tested yet. Demo money, no real orders.

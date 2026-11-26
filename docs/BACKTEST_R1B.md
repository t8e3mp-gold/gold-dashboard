# R1b backtest: trend families (SIMULATED, research only)

Run: 2026-11-26 15:05 Cairo. Code: modules/backtest/r1b.py (same harness, costs 0.3% round trip with slippage, 60/40 split, exit grid as r1.py). Raw: docs/backtest-r1b-results.json.
Families: Donchian breakout (24 or 72 candles) and EMA cross-up (12/26 or 24/72). Same data as R1 (Binance public 1h klines).

| Coin | Rule | OOS trades | Avg net per trade | Baseline avg net | Win rate | Max drawdown |
|---|---|---|---|---|---|---|
| XAUT | Donchian | 14 | -0.89% | -0.64% | 28.6% | 13.1% |
| XAUT | EMA cross | 24 | -0.23% | -0.71% | 62.5% | 7.9% |
| ETH | Donchian | 61 | -0.59% | -0.41% | 68.9% | 33.6% |
| ETH | EMA cross | 107 | -0.21% | -0.34% | 58.9% | 23.8% |
| SOL | Donchian | 141 | -0.21% | -0.35% | 36.2% | 31.0% |
| SOL | EMA cross | 50 | -0.34% | -0.36% | 42.0% | 18.2% |
| BNB | Donchian | 60 | -0.05% | -0.42% | 65.0% | 14.1% |
| BNB | EMA cross | 114 | -0.26% | -0.33% | 36.0% | 26.9% |

Result: 8 of 8 negative after costs. With R1's 16, that is 24 of 24 rule/coin combinations with no positive net out of sample. The gate (98% over 1000+ trades, positive net, drawdown under 20%, out of sample) is not met by any. The page keeps saying wait. The gate is unchanged.
Limits: 1h candles only; small samples for XAUT; more families tried raises the chance of a lucky result, and none passed anyway; this is not advice.

# R1c backtest: squeeze breakout and volume spike (SIMULATED, research only)

Run: 2026-11-26 ~17:15 Cairo. Code: modules/backtest/r1c.py (same harness, costs 0.3% round trip with slippage, 60/40 in-sample/out-of-sample split, exit grid as r1.py; parameter chosen in-sample only). Raw: docs/backtest-r1c-results.json. Data: Binance public 1h klines (XAUT full history, others 2 years).
Families: Bollinger squeeze breakout (bandwidth in the lowest 20% of the last 120 candles, then close above the upper band, n=20) and volume spike (volume over 3x or 5x the 24h mean on a green candle).

| Coin | Rule | OOS trades | Avg net per trade | Baseline avg net | Win rate | Max drawdown |
|---|---|---|---|---|---|---|
| XAUT | bb_squeeze | 12 | -0.8561% | -0.513% | 58.3% | 10.28% |
| XAUT | vol_spike | 18 | -0.5266% | -0.4533% | 27.8% | 9.26% |
| ETH | bb_squeeze | 86 | -0.306% | -0.33% | 87.2% | 24.42% |
| ETH | vol_spike | 30 | -0.5627% | -0.4361% | 56.7% | 23.22% |
| SOL | bb_squeeze | 92 | -0.2626% | -0.3235% | 89.1% | 24.46% |
| SOL | vol_spike | 19 | -0.4989% | -0.376% | 63.2% | 13.3% |
| BNB | bb_squeeze | 66 | -0.2992% | -0.3225% | 54.5% | 19.78% |
| BNB | vol_spike | 19 | -0.2951% | -0.3266% | 63.2% | 8.89% |

Result: 8 of 8 negative after costs. Total so far: 32 of 32 rule/coin combinations with no positive net out of sample. Squeeze breakout has a high win rate (up to 89%) but average net is still negative: small wins, larger losses. Three of 8 rows beat their own baseline (ETH, SOL, BNB squeeze, by 0.02 to 0.06 points) but all stay negative, so this is not an edge. Trade counts are far below 1000 for every row. The gate (98% over 1000+ trades, positive net, drawdown under 20%, out of sample) is not met by any. The page keeps saying wait. The gate is unchanged.
Limits: 1h candles only; small samples; trying more families raises the chance of a lucky result, and none passed anyway; not advice. Gap #6 stays OPEN.

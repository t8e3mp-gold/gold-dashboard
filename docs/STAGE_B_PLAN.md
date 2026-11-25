# Stage B plan: real market data, one module at a time

Approved by the user Nov 25 20:50 Cairo. Rules: free, no card, no new accounts, no keys, public data only, spot only, research not advice. Every module: unit tests on hand-computed data, schema check, cross-check against a second source, UI test, live check after deploy, an audit round, then a short report. The next module starts only after the previous audit passes. Plan A/B/C for each module, with the switch trigger. References are in `docs/references/` (cited as [R-id]).

## Gate test first (B0)
Can GitHub Actions runners reach https://data-api.binance.vision? Claude's answer says 451 blocks were seen (reported, not verified) [R-20261125-01, R-20261125-04]. Run one small read-only request from a runner and record the result. If blocked, Plan B sources become Plan A for the file data.

## Modules
| id | module | Plan A | Plan B | Plan C | switch trigger |
|---|---|---|---|---|---|
| B1 | `price-spot`: XAUT, BNB, ETH, SOL last price and 24h stats; the page also fetches live prices directly in the browser (label live) | Binance mirror from the runner [R-20261125-04] | OKX public ticker [R-20261125-06] | Gate.io ticker, Kraken XAUTUSD as a USD cross-check [R-20261125-06]; browser-side fetch if the runner is blocked [R-20261125-01] | A fails or returns 451/empty, or A and B differ by more than 0.5% (flag, never blend) |
| B2 | `klines`: 5m, 1h, 1d candles, last 1000 bars each, closed candles only (no look-ahead) | Binance mirror klines | OKX candles | Binance public archive (daily files) [R-20261125-04] | A fails twice |
| B3 | `trades-flow`: aggTrades for buyer/seller volume (delta) and volume flow | Binance aggTrades via mirror (isBuyerMaker field) [R-20261125-04] | kline taker-buy volume (coarser, same source) | OKX trades | A rate limited or blocked |
| B4 | `volume-profile`: POC, value area, high/low volume nodes | Own numpy code from B2/B3, cross-checked against py-market-profile on the same data [R-20261125-05] | srl-python-indicators idea set (Apache-2.0) | Fixed-range profile from daily bars | cross-check differs by more than a set tolerance |
| B5 | `order-book`: depth view and imbalance, live in the browser only, no history stored (history cannot be backtested) [R-20261125-01] | Binance depth from the browser | OKX books | Gate.io order book | A fails or CORS blocks |
| B6 | `zones`: entry/exit zones from B4/B5, label hypothesis | computed from B4 | computed from B2 swing levels | none shown ("no zone") | inputs stale |
| B7 | `backtest`: fees, slippage, 1000+ trades, 20% drawdown filter, walk-forward out-of-sample; every strategy tried is logged; feeds the 98% card [R-20261125-01] | own engine, no GPL code copied | second implementation of the same rule for a cross-check | none (no result shown) | cross-check mismatch |
| B8 | `ai-text`: summaries that only use computed numbers via {{id}} placeholders and a validator [R-20261125-01] | template text (no model) | free model if one is found that needs no card (none verified; GitHub Models retired, Workers AI newer models need payment) [R-20261125-01] | none | validator rejects twice |

## Cadence
File data refreshes through Plan A/B/C of gap 9 (cron, Instinct keeper 4 times a day, manual) and on demand. Live prices and the order book are fetched by the page in the browser, labeled live with their own timestamp. Closed-candle data is fine at 6-hour freshness. A faster cadence needs the user's agreement because it means more browser logins.

## Not used (and why)
Cloudflare Workers/proxy: no new accounts and card status unverified [R-20261125-07]. ollama, langflow, n8n, Grafana and other self-hosted tools: need a server [R-20261125-02, R-20261125-03]. Scrapling: we use public APIs, not scraping.

## Audit per module
1) tests with hand-computed values; 2) schema and secret scan; 3) cross-check against the Plan B source on live data; 4) UI test and a screenshot at 390px; 5) live page check after deploy; 6) failure drill for that module; 7) written audit round, repeat until a pass finds nothing material.

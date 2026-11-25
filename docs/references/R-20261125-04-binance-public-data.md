# R-20261125-04: Binance public market data
- Found by us Nov 25 (research report 16:10 Cairo).
- Sources: https://data-api.binance.vision (public spot market data mirror, no keys), https://github.com/binance/binance-public-data (daily/monthly archives), terms https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md
- Key facts: **verified** Nov 25 20:55 Cairo: https://data-api.binance.vision/api/v3/ticker/price?symbol=XAUTUSDT returned a price. **Verified earlier** (Nov 25 16:10): aggTrades and klines (with taker buy volume) work from the mirror. **Not verified**: whether GitHub Actions runners are blocked (Claude's answer says 451 errors were seen, reported only). This test is the first Stage B step.
- Verdict: use. Plan A for all four assets.
- Used by: B1, B3, B4, B5.

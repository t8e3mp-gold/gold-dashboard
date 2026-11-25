# [افتح لوحة الذهب والعملات: https://t8e3mp-gold.github.io/gold-dashboard/](https://t8e3mp-gold.github.io/gold-dashboard/)

**Open the dashboard:** https://t8e3mp-gold.github.io/gold-dashboard/

Public research dashboard (Arabic UI, phone first) for Binance spot XAUT/USDT, BNB, ETH and SOL. Spot only, public market data, no keys, no trading, no real accounts. Research readings, not financial advice.

- `site/` : the page (HTML, CSS, JS).
- `modules/` : one folder per data module (prices, candles, flow, volume profile, intent proxies, cross-check log), each with its own tests.
- `pipeline/` : the runner that executes modules and validates their output.
- `data/` : the published data files (refreshed by the `Refresh data` workflow).
- `docs/` : architecture, stage plan, gaps list, root fixes, references.

Everything here is publicly readable. No passwords, keys, tokens, emails or addresses belong in this repo.

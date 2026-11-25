# gold-dashboard

Public research dashboard (Arabic UI) for Binance spot XAUT/USDT, BNB, ETH, SOL. Spot only, public market data, no keys, no trading, no real accounts.

- `src/` : the dashboard source. `src/data/*.json` are data files (price history, strategy lab results, research notes, demo trade log).
- `tools/` : scripts that rebuild the data (`daily.sh` runs `refresh.py`, `ext.py`, `ext2.py`).
- `file.json` : allowed data origins.

Everything here is publicly readable: research notes, backtests and demo (virtual money) trades. No passwords, keys, tokens, emails or addresses belong in this repo. Research readings, not financial advice.

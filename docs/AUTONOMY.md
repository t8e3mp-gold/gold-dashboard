# Design rule: automatic by default, manual override always available
Standing rule from the user (Nov 26 2026): the project runs itself, heals itself and evolves, but manual control is never removed. It stays as the emergency path. The project must not get sick or die.

Every automatic mechanism needs: (1) automatic default, (2) a written Plan B, (3) a manual override that works without the automatic part, (4) a failure that is loud (red run, watchdog message), never silent.

| Mechanism | Automatic default | Manual override (emergency) |
|---|---|---|
| Data refresh | Refresh workflow every 3h, plus market-session runs from the assistant, plus watchdog heal if data older than 6h | Actions > Refresh data > Run workflow. Or run `python pipeline/runner.py` locally and commit data/ |
| Backtest | Backtest workflow weekly, commit only if the sanity gate passes | Actions > Backtest > Run workflow. Or run `R1_OUT=modules/backtest/results.json python modules/backtest/r1.py` locally |
| Economic calendar | tools/calendar_sync.py on every Refresh (BLS iCal), BEA and FOMC read live | Edit modules/news/calendar.json by hand (dates, source, checked date) |
| Klines source | Binance mirror, then OKX, then Gate.io, switched per series with a cross-check | Edit the source order in modules/klines/run.py |
| Health | Watchdog every 6h: heals stale data, goes red on problems (GitHub emails the owner) | Actions > Watchdog > Run workflow for an immediate check |
| Bad change | Tests and scan run before data or code is accepted; invalid module output is never published | Revert the commit on GitHub (History > Revert), then run Refresh |
| Pause everything | none | Actions > select the workflow > "..." > Disable workflow (re-enable the same way) |

The recommendation gate (100+ out-of-sample trades, positive net after fees) is never changed automatically. Only the user can change it.

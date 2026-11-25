# Architecture

Static site on GitHub Pages. Data and code are separate. The site only reads JSON files in `data/`.
Every JSON file is written by a module, validated, then committed by a GitHub Action.

## Folders
- `site/` static UI (HTML, JS, CSS). Arabic, RTL, black and gold. Built from `data/meta.json`; no per-module UI edits for standard cards.
- `modules/<id>/` one folder per module: `manifest.json`, `run.py`, `schema/`, `tests/`, `README.md`.
- `modules/registry.json` list of enabled module ids.
- `schemas/` envelope and manifest schemas.
- `pipeline/` `runner.py` (order, run, validate, publish) and `validate.py` (gate).
- `data/` published output. `meta.json` holds per-module status, source, label, last good run.
- `tests/` unit tests. `.github/workflows/` CI, daily refresh, Pages deploy.

## Rules
1. Every record has: id, value, unit, source (name, url), fetched_at (UTC), label (measured, simulated, live, hypothesis, ai), max_age_hours, checked_against.
2. A module with output that fails schema or envelope checks is rejected. Its last good output stays and the site shows a warning.
3. One failing module never stops the others.
4. Stale data (older than max_age_hours) is flagged on the page automatically.
5. No secrets in the repo. Public, key-free data sources only.
6. Research readings only, not financial advice. Spot only, no real trading.

## Flow
refresh.yml (daily, or manual) -> tests -> runner -> validate -> commit data -> pages.yml deploys.

## Isolation, health and pushing (added in stage A hardening)
- Modules run in a throwaway copy with only their declared inputs, no secrets, resource limits, and no network unless the manifest says `"permissions": {"network": true}`. If network isolation is not available on the machine, a no-network module is refused (fails closed).
- Time on the page comes from the server (HTTP Date + Age), not the phone clock. The page caches its shell and last data (service worker) and says when it is offline.
- `Watchdog` workflow (every 6h) fails if data is older than 26h, a module failed, the live site is behind the repo, or the last scheduled refresh failed or is missing.
- `Refresh data` can be started with `drill=true` to prove the failure path.
- Many files in one push: commit `incoming/bundle.b64` (base64 of a tar.gz). The `Apply bundle` workflow extracts only allowlisted folders, runs tests and the scan, commits as the bot, and deletes the bundle. Workflow files themselves are never extracted from a bundle.

## Refresh paths: Plan A, B, C (switch-over triggers)
- **A. GitHub cron** (`Refresh data`, 05:17 UTC daily). GitHub's scheduler is best effort. On Nov 25 it fired nothing in 27 minutes on two separate schedules, so A is not trusted alone.
- **B. Instinct keeper.** Four wakes a day (01:20, 07:20, 13:20, 19:20 Cairo) read `data/meta.json` through the GitHub API. If the data is older than 5 hours, or a scheduled run is missing, it starts `Refresh data` from the signed-in browser (drill unticked) and checks the result. No token, no account, free. Switch trigger: data older than 5h. Proven Nov 25 20:32 Cairo (run #11).
- **C. Manual.** Open the Actions page "Refresh data", press Run workflow (leave drill unticked), or ask the assistant to do it. Switch trigger: A and B both failed, or the keeper reports a failure. A refresh link is in the page footer.
- The `Watchdog` fails visibly if all three fail and the data passes 26 hours.

## Second source per module (Plan B for data)
Each module that reads an outside source must name a fallback source in its manifest notes. The fallback result is shown with its own source and label and is never merged silently. The first price modules (stage B) will use data-api.binance.vision as A and a second independent source as B. That source is not chosen yet.

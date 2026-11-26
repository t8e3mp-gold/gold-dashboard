# Recommendation rules (R5). Computed, display only, no AI text, no orders.

Inputs: levels (zones, ATR), news (wait window, leak/trap flag, next event), backtest (out-of-sample results per rule). Spot only, own the asset, buy dips and sell rallies in tranches. No leverage or shorting.

1. Edge gate. A rule has a proven edge only with at least 100 out-of-sample trades and a positive average net after fees. Until a rule clears it the stance is "wait" and the page says "no proven edge". The best rule is still shown with its numbers.
2. Wait overrides. A scheduled-event window (2 h before to 1 h after) or a possible leak/trap flag forces "wait". The official release is confirmation, not the first signal.
3. Only with a proven edge and quiet news: "buy watch" if price is within 1 ATR above the nearest support and a bounce is forming; "sell watch" if price is within 1 ATR below the nearest resistance. Otherwise "wait".
4. Conditional plans (always shown, never a call): buy zone = strongest support within 5% (else nearest); confirmation = a 1h close above the zone; invalidation = zone low minus 1 ATR; first target = nearest resistance; risk and reward in %, reward to risk after 0.3% round-trip cost. Sell plan = tranches at the nearest and strongest resistance zones; hold the rest above the top zone plus 1 ATR.
5. Plan A: wait for the touch and a 1h close above the zone. Plan B: a 1h close under invalidation cancels the idea. Plan C: near a scheduled event or a leak/trap flag, do nothing until an hour after the official release.
Tests: modules/recommendation/tests. Backtest evidence: docs/BACKTEST_R1.md.

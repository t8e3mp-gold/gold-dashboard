# Smart refresh tied to market sessions

Requested by the user Nov 25 21:04 Cairo. Refresh 1 hour before and at each open and close of Tokyo, London and New York (12 per day on trading days). Times use each market's own timezone and daylight saving, not fixed Cairo times. Each "1 hour before" refresh also sends the user a notice with the market name and event.

## Schedule (local exchange time; Cairo shown for winter time, UTC+2)
| Market | Event | Refresh at (local) | Cairo (winter) |
|---|---|---|---|
| Tokyo (Asia/Tokyo) | open 09:00 | 08:00 notice+refresh, 09:00 refresh | 01:00, 02:00 |
| Tokyo | close 15:30 | 14:30 notice+refresh, 15:30 refresh | 07:30, 08:30 |
| London (Europe/London) | open 08:00 | 07:00, 08:00 | 09:00, 10:00 |
| London | close 16:30 | 15:30, 16:30 | 17:30, 18:30 |
| New York (America/New_York) | open 09:30 | 08:30, 09:30 | 15:30, 16:30 |
| New York | close 16:00 | 15:00, 16:00 | 22:00, 23:00 |

Tokyo closes at 15:30 JST since 5 Nov 2024 [JPX notice: https://www.jpx.co.jp/english/corporate/news/news-releases/1030/20230920-01.html]. Cairo times move when London or New York change clocks; the schedule follows the markets, not Cairo. Weekends are skipped (Mon-Fri in the market's own timezone).

## Holidays and early closes (my list, hypothesis until checked against exchange calendars)
Skip the notice and refresh on: NY Nov 26 2026 (Thanksgiving), Dec 25, Jan 1; London Dec 25, Dec 28 (substitute), Jan 1; Tokyo Dec 31, Jan 1-3. Early closes: NY Nov 27 (13:00 ET), Dec 24 (13:00 ET); London Dec 24 and 31 (12:30). On an early-close day the 16:00/16:30 event is wrong; the extra refresh is harmless and the notice is skipped. Review this list in January.

## Plan A / B / C
- Plan A: 12 Instinct wake schedules, one per event, each in the market's own timezone (DST-correct). Each dispatches the Refresh workflow once and verifies the data moved. Proven mechanism (keeper dispatch worked Nov 25).
- Plan B: the existing keeper (4 wakes a day, dispatches if data is older than 5 h) and the GitHub daily cron 05:17 UTC. Switch trigger: a Plan A wake is missed or the data is older than 2 h at a session event.
- Plan C: manual "Run workflow" button (link in the page footer).
Total refreshes: at most 12 + 4 keeper + 1 cron per day, well under hourly. Live prices and the order book are fetched by the page in the browser and do not depend on this.

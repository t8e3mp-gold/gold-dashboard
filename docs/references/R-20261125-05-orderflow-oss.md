# R-20261125-05: open-source volume profile / flow / order book projects
- Found by us Nov 25 (report 16:10 Cairo); stars and licences read from GitHub then.
- Projects: py-market-profile (BSD, 413 stars); srl-python-indicators (Apache-2.0); tayor/orderflowkit (MIT, new); Tworasos/tape-and-book (MIT, new); OrderflowChart (Apache-2.0); freqtrade orderflow docs (GPL-3, ideas only); TradingView lightweight-charts (Apache-2.0, https://github.com/tradingview/lightweight-charts); microstructure-lab (MIT).
- Decision already approved by the user: write our own tested implementations and cross-check the volume profile against py-market-profile.
- Verdict: use-with-limits (code reused only where licence allows; GPL code is not copied).
- Used by: B4 volume profile, B5 delta/volume flow, B6 order book, charts (stage C).

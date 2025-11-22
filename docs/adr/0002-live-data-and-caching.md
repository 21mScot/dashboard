# 0002 – Live data fetching and caching
Date: 2025-11-22  
Status: Accepted

## Context
- App fetches BTC network data from public APIs (price, difficulty, block height, FX).
- Needs resilience, clear modes (live vs. static), and predictable caching.

## Decision
- Live mode uses public APIs; static mode uses defaults from `settings.py`.
- Streamlit `st.cache_data` used for network data with TTL from `LIVE_DATA_CACHE_TTL_S`.
- Graceful fallback to static assumptions when live fetch fails (warn the user).
- User-agent and timeouts defined in `settings.py`; no API keys are embedded.

## Consequences
- Callers must handle the live/static flag and surface which mode is active.
- Changes to live data sources or cache TTL should be made in `settings.py`.
- Avoid duplicating fetch logic; centralize in `src/core/live_data.py`.

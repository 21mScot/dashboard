# 0001 – Chart styling conventions
Date: 2025-11-22  
Status: Accepted

## Context
- Multiple charts (BTC and fiat monthly forecasts) needed consistent look/feel.
- Dual axes, padded domains, and formatted month labels were applied ad hoc.

## Decision
- Apply shared settings for padding and colors from `src/config/settings.py`:
  - `HISTOGRAM_COLOR`, `HISTOGRAM_Y_PAD_PCT` for bar charts.
  - `LINE_Y_PAD_PCT` for line charts.
- Line style semantics:
  - Actual/observed series use `LINE_STYLE_SOLID`.
  - Forecast/projection series use `LINE_STYLE_FORECAST` (dashed/broken).
- Use dual y-axes (left/right) with matching domains to avoid inverted scales.
- Format x-axis month labels as `%b '%y` with a slight angle for readability.
- Keep BTC charts as bars (monthly mined) and fiat as lines (revenue), both with left/right axes.

## Consequences
- Chart code should read padding/color/label formats from settings; avoid hard-coded scales.
- New charts should follow the same axis formatting and padding conventions unless there’s a justified exception.

# src/ui/style.py

from __future__ import annotations

"""
UI / visual style constants for the dashboard.

Keep anything purely presentational in here (colours, line widths, spacing),
and keep domain / modelling constants in src/config/settings.py.
"""

# ---------------------------------------------------------------------------
# Chart line widths
# ---------------------------------------------------------------------------

LINE_WIDTH_PRIMARY = 1.25  # default for main time-series lines


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
# These are hex colours chosen to look modern and readable on light backgrounds.
# They roughly align with the palette used in the Future Bitcoin Calculator.

COLOR_REVENUE = "#1f77b4"  # soft blue
COLOR_OPEX = "#d62728"  # modern red
COLOR_PROFIT = "#2ca02c"  # green (money)
COLOR_BTC = "#bfbfbf"  # neutral grey for BTC bars

AXIS_LABEL_COLOR = "0.5"  # light grey (matplotlib greyscale)
TICK_LABEL_COLOR = "0.5"
GRID_ALPHA = 0.25
BAR_ALPHA = 0.3

# 0007 – Chart color semantics (Bitcoin vs. Fiat)
Date: 2025-11-22  
Status: Accepted

## Context
- We need consistent, semantic colors for different quantitative series across charts.
- Bitcoin series already use a brand color (Bitcoin Orange). Fiat/revenue series should use a neutral, professional color.

## Decision
- Use Bitcoin Orange (`BITCOIN_ORANGE_HEX`, defined in settings) for Bitcoin-specific series and markers (e.g., halving lines).
- Use a neutral blue for fiat/price/revenue series:
  - `FIAT_NEUTRAL_BLUE_HEX = "#1f77b4"` (standard neutral quantitative blue).
- Apply these constants in chart layers instead of hardcoded colors.

## Consequences
- Chart code should reference `BITCOIN_ORANGE_HEX` for BTC series/markers and `FIAT_NEUTRAL_BLUE_HEX` for fiat/neutral series.
- Avoid arbitrary colors for new series; extend the palette in settings if more semantic roles are needed.

## Reporting-standard cues (line/marker semantics)
To align with common financial reporting conventions for charts:

| Element             | Actual / Historical Data                                         | Forecast / Projected / Budget / Plan Data                                     |
|---------------------|------------------------------------------------------------------|--------------------------------------------------------------------------------|
| Line style          | Solid line                                                       | Dashed or dotted line (dashed is most common)                                  |
| Line thickness      | Usually same or slightly thicker                                 | Often same thickness; sometimes slightly thinner                               |
| Color               | Strong, saturated color (e.g., dark blue, black, dark green)     | Same color but lighter/faded; or gray; or same hue but dashed                  |
| Marker              | Optional small dot/circle on data points                         | Usually no markers on the forecast portion                                     |
| Vertical separator  | Thin vertical line (often light gray/black) at the “today”/last actual point | Separates actual from forecast                                        |
| Shading             | None or very light fill under actual line                        | Light shaded band/area under forecast to emphasize “future”                    |
| Label               | “Actual”, “Historical”, “YTD”                                    | “Forecast”, “Projection”, “Budget”, “Plan”, “Outlook”, “Guidance”              |

Use these cues when adding or adjusting forecast vs. actual series, in addition to the palette guidance above.

## Palette grammar (for clarity and future use)
| Signal                 | Colour                  | Meaning/Usage                                   |
|------------------------|-------------------------|-------------------------------------------------|
| BTC-specific metric    | Bitcoin Orange          | Bitcoin-native values (price, halving markers)  |
| Energy/mining output   | Neutral Grey            | Physical production metrics (e.g., BTC mined)   |
| Money (fiat)           | Neutral Blue            | Numeric revenue/fiat values                     |
| Profits/gains/losses   | Green/Red (optional)    | Only if P&L/NPV/IRR are added; avoid elsewhere  |

This keeps the palette lean, avoids overloading green, and makes color meaning consistent across charts.

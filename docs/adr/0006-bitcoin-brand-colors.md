# 0006 – Bitcoin brand color palette
Date: 2025-11-22  
Status: Accepted

## Context
- Charts and UI elements occasionally need Bitcoin brand colors for clarity/branding.
- We want a single source of truth for the palette.

## Decision
- Define Bitcoin Orange as the primary brand color:
  - HEX: `#F7931A`
  - RGB: `247, 147, 26`
  - HSL: `35°, 94%, 54%`
- Store the color in `settings.py` as `BITCOIN_ORANGE_HEX`.
- Use the constant for any Bitcoin-specific accents; avoid hardcoding the hex elsewhere.

## Consequences
- UI and chart code should import/use `BITCOIN_ORANGE_HEX` for Bitcoin accents.
- Additional palette entries can be added alongside this constant to keep branding consistent.

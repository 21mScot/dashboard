# 0005 – Locale-aware date formatting
Date: 2025-11-22  
Status: Accepted

## Context
- Forecast tables display months/dates and should respect the user’s locale when possible.
- We want a single fallback format when locale resolution isn’t available or fails.

## Decision
- Use `locale.setlocale(locale.LC_TIME, "")` at UI startup to honor the host/user locale for date formatting.
- Apply a shared helper (`_format_month`) to format table Month columns, using locale-aware `strftime("%x")` with a fallback to `settings.DATE_DISPLAY_FMT` (currently `%d-%b-%Y`).
- Keep chart axes using explicit `%b '%y` formatting for readability/consistency across locales.

## Consequences
- Dates in tables reflect user locale when available; otherwise they fall back to a consistent, human-readable format.
- Any new date displays should reuse the helper or `DATE_DISPLAY_FMT` to stay consistent.
- Locale initialization is best-effort; failures fall back to the configured format without breaking rendering.

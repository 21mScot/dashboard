# Changelog

All notable changes will be documented in this file.

## [Unreleased]

## [v0.30.2-alpha] - 2025-11-25
### Added
- Sidebar tooltips for BTC price, network hashrate, and realised hashprice; clarified FX label and help text.
### Changed
- PDF footer styling refined to align with the rest of the layout and reduce whitespace.

## [v0.30.1-alpha] - 2025-11-25
### Changed
- Sidebar static-mode messaging now explicitly names the USD/GBP exchange rate alongside BTC price and hashprice.

## [v0.30.0] - 2025-11-25
### Added
- Estimated hashprice now computed from blockchain.info hashrate, BTC price, and block subsidy with a static fallback value.
### Changed
- Sidebar consolidates BTC price and hashprice in one expander; static-mode messaging references hashprice, and difficulty/subsidy/height were removed from the network panel.

## [v0.21.6] - 2025-11-26
### Fixed
- PDF export controls now render via a Streamlit component so the “View PDF” action works reliably; removed the non-functioning print button.

## [v0.21.5] - 2025-11-25
### Added
- Introduced a “Learn about Bitcoin” tab with curated, UX-friendly expanders covering energy use, mining mechanics, and recommended reading paths.

## [v0.21.4] - 2025-11-24
### Changed
- Synced production miner catalogue to the latest supplier spreadsheet and retained the previous set in `PREVIOUS_MINERS` for manual comparison.

## [v0.21.3] - 2025-11-24
### Changed
- Live network data cache TTL now respects environment: 24h in dev for stability, 10 minutes in prod for fresher data.

## [v0.21.2] - 2025-11-24
### Added
- Split miner catalogues by environment: dev shows three TestMake variants for efficiency/breakeven/payback testing; prod keeps the supplier-approved set with immediate-access markers.
- Reintroduced a miner dropdown inside “Miner detailed analysis...” so users can experiment with alternative miners; selection respects the active catalogue (APP_ENV).

## [v0.21.1] - 2025-11-24
### Fixed
- Wired project CapEx into Section 3 scenario payback/ROI so the financial forecasts reflect the current miner plan instead of assuming zero capital.
- Hardened revenue-share selection to respect explicit 0–100% inputs and avoid falsy fallback behaviour.
- Made fiat forecast fallback rebuilds safe for dataclass contexts when BTC forecasts are regenerated.

## [v0.21.0] - 2025-11-23
### Added
- Investment metrics pipeline: compute total net cash and monthly/annual IRR from monthly net cashflows and CapEx; new Streamlit investment summary panel with tooltips.
- Cumulative cashflow & payback chart now returns payback info and uses a lighter zero line; added Plotly unified BTC/fiat chart with optional BTC price path and halving markers.
- Fiat/BTC Plotly enhancements: power cost and net cashflow overlays, refined line styling, and explanatory text across forecast expanders.
- Added `numpy-financial` dependency for IRR calculations; new `investment_metrics` core helper and UI wiring.
### Changed
- Version bumped to v0.21.0 to capture investment metrics and unified Plotly chart updates.

## [v0.20.0] - 2025-11-23
### Added
- Rebuilt BTC and fiat forecasts in Plotly with dual axes, halving labels, and semantic BTC orange/fiat blue styling; BTC forecast now shows monthly and cumulative series with dashed forecast conventions.
- Added fiat Plotly chart with gross revenue, power cost, net cashflow, and BTC price path on the secondary axis, plus tooltips and refined line weights/dashes.
- Introduced cumulative cashflow & payback Plotly view (zero-line, payback marker/annotation) using CapEx-derived starting cashflow.
- New helper chart functions under `src/ui/charts.py` to centralize Plotly usage; ADR updated with financial reporting line/marker conventions.
### Changed
- Version bump to v0.20.0 to reflect Plotly chart domain and BTC/fiat visualization overhaul.

## [v0.19.0] - 2025-11-22
### Added
- Unified forecast helpers (halving dates, y-domain prep, unified table) and typed contexts for BTC/fiat forecasts.
- New constants: BTC bar grey (`BTC_BAR_GREY_HEX`) and forecast line styles; BTC forecast table columns renamed to Block reward/subsidy/Tx fees.
- Additional tests for forecast utilities and data-prep edge cases.
### Fixed
- Hardened fiat forecast prep when columns are missing or Month is NaT; added halving marker caption to BTC forecast chart.

## [v0.18.0] - 2025-11-21
### Added
- Streamlined miner details with supplier/model/price summary, three-column specs, and an inline miner picker embedded in the overview “Miner details...” expander.
- Scenario comparison table now uses consistent metric sizing (configurable via `settings.py`) and centered headers; moved revenue-share slider into the scenario details expander for clarity.
- Updated site performance copy to reflect live network data and current hardware; added constants for Streamlit metric styling.
### Changed
- Default miner selection now persists in session state; dropdown selection triggers immediate recalculation.
- Allow cost of generation to be zero to support free/credit scenarios.
### Verification
- `python3 -m compileall src`

## [v0.17.0] - 2025-11-19
### Added
- Created initial PDF export pipeline with download/view/print controls so stakeholders can grab WIP reports without leaving the app; appended the Assumptions & Methodology appendix for shared context.
- Introduced in-app Terms & Conditions / Privacy Policy links and versioned footer, plus lightweight legal docs under `docs/`.
- Added changelog tracking to capture release content before tagging.

### Verification
- `pytest`
- `black` / `ruff` pre-commit hooks
- Manual Streamlit run, PDF download/view/print smoke test

## [v0.16.0] - 2025-11-19
### Added
- Split scenario responsibilities into distinct model, calculation, and finance helper modules.
- Introduced new regression coverage for the scenario engine plus reusable payback/ROI and revenue-weighted margin helpers.
- Moved `MinerOption` into `src/core/miner_models.py` so core code no longer imports UI modules.

### Verification
- `pytest`
- `black` / `ruff` pre-commit hooks
- Manual Streamlit UI smoke test (scenarios + miner selection)

[Unreleased]: https://github.com/21mScot/dashboard/compare/v0.30.2-alpha...HEAD
[v0.30.2-alpha]: https://github.com/21mScot/dashboard/releases/tag/v0.30.2-alpha
[v0.30.1-alpha]: https://github.com/21mScot/dashboard/releases/tag/v0.30.1-alpha
[v0.30.0]: https://github.com/21mScot/dashboard/releases/tag/v0.30.0
[v0.21.6]: https://github.com/21mScot/dashboard/releases/tag/v0.21.6
[v0.21.5]: https://github.com/21mScot/dashboard/releases/tag/v0.21.5
[v0.21.4]: https://github.com/21mScot/dashboard/releases/tag/v0.21.4
[v0.21.3]: https://github.com/21mScot/dashboard/releases/tag/v0.21.3
[v0.21.2]: https://github.com/21mScot/dashboard/releases/tag/v0.21.2
[v0.21.1]: https://github.com/21mScot/dashboard/releases/tag/v0.21.1
[v0.21.0]: https://github.com/21mScot/dashboard/releases/tag/v0.21.0
[v0.20.0]: https://github.com/21mScot/dashboard/releases/tag/v0.20.0
[v0.19.0]: https://github.com/21mScot/dashboard/releases/tag/v0.19.0
[v0.18.0]: https://github.com/21mScot/dashboard/releases/tag/v0.18.0
[v0.17.0]: https://github.com/21mScot/dashboard/releases/tag/v0.17.0
[v0.16.0]: https://github.com/21mScot/dashboard/releases/tag/v0.16.0

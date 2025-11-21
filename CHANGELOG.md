# Changelog

All notable changes will be documented in this file.

## [Unreleased]
- TBC

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

[Unreleased]: https://github.com/21mScot/dashboard/compare/v0.18.0...HEAD
[v0.18.0]: https://github.com/21mScot/dashboard/releases/tag/v0.18.0
[v0.17.0]: https://github.com/21mScot/dashboard/releases/tag/v0.17.0
[v0.16.0]: https://github.com/21mScot/dashboard/releases/tag/v0.16.0

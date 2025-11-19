# Changelog

All notable changes will be documented in this file.

## [Unreleased]
- TBC

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

[Unreleased]: https://github.com/21mScot/dashboard/compare/v0.17.0...HEAD
[v0.17.0]: https://github.com/21mScot/dashboard/releases/tag/v0.17.0
[v0.16.0]: https://github.com/21mScot/dashboard/releases/tag/v0.16.0

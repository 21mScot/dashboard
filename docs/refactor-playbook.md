# Refactor Playbook

This document is the shared, version-controlled reference for how we plan and execute refactors in the `dashboard` repo. Update it whenever we learn something new so future work stays consistent.

## Purpose and Principles
- **Keep `main` deployable.** All significant work happens on focused branches (e.g., `codex-refactor/<feature>`), merged only after review and verification.
- **Separate concerns.** UI code lives under `src/ui`, business logic under `src/core`, configuration under `src/config`. Data objects encapsulate related values so downstream code manipulates meaningful structures rather than primitive tuples.
- **Tests protect behavior.** Calculation engines and adapters must have unit or integration coverage before structural changes land.
- **Small, observable steps.** Prefer iterative commits that each pass tests. If the refactor goal can’t be explained in two sentences, split it.

## When to Refactor
Refactor when one or more of these signals appear (not just when a file is “long”):
1. **High change coupling.** Updating one feature requires touching several unrelated modules or duplicating logic.
2. **Hidden intent.** Deep nesting, unclear naming, or large functions that mix responsibilities (e.g., calculation, validation, and I/O together).
3. **Duplicated logic or data flow.** Copy/pasted validation, repeated data-shaping, or inconsistent domain concepts (e.g., “portfolio” vs “position” objects).
4. **Hard-to-test modules.** Lack of seams/interfaces prevents targeted testing, causing fragile integration tests.
5. **Performance/resource red flags.** Profiling shows hotspots tied to poor abstractions.
6. **Upcoming features blocked.** Planned capability can’t be added cleanly because the current structure lacks extension points.

## Preparation Checklist
- [ ] Identify the pain point and desired outcome (e.g., “Make scenario engine independently testable”).
- [ ] Confirm you are on a feature branch (`git checkout -b codex-refactor/<topic>` if needed).
- [ ] Capture current behavior: locate existing tests, or add a lightweight safety net if coverage is missing.
- [ ] Note dependencies: config files, env vars, scripts, or data fixtures that must stay compatible.
- [ ] Decide success metrics (simpler API, fewer side effects, faster runtime, etc.).

## Refactor Workflow
1. **Align on scope.** Write 2–3 sentences summarizing the change and update this file’s log (see below).
2. **Inventory tests.** List commands to run (e.g., `pytest tests/core/test_scenarios.py`). Add missing tests that lock critical behavior before restructuring.
3. **Design the steps.** Break the work into small phases (extract object, move logic, rename module). Each phase should build and pass tests independently.
4. **Implement incrementally.** After each phase:
   - run the agreed commands,
   - review the diff for unintended changes,
   - commit with a descriptive message (`git commit -m "Refactor: extract ScenarioNormalizer"`).
5. **Verify holistically.** When the refactor goal is met, run the broader suite (or as much as feasible offline) and describe the verification in the PR/commit message.
6. **Document outcomes.** Update README/docs if APIs moved, note migrations/data implications, and log the refactor below.

## Module-Specific Guidance
- **Calculation engines (`src/core`)**
  - Keep pure functions or side-effect-light classes that accept data objects and return new immutable structures.
  - Favor dependency injection so tests can swap adapters.
  - Enforce invariants via dataclasses/pydantic models; add regression tests before major rewrites.
- **UI (`src/ui`)**
  - UI components should consume prepared view models from core modules; avoid embedding calculations or persistence logic.
  - When refactoring, ensure component props/events remain backward compatible or document breaking changes.
- **Data shapes**
  - Define shared schemas (dataclasses/TypedDicts) under `src/core/models` (or similar) and import them rather than duplicating dictionaries.
  - Changes to schema definitions require coordinated updates to serializers, storage, and tests.

## Working With Codex
When asking Codex to assist with a refactor:
1. Specify the branch, target module(s), and the pain point.
2. Provide any architectural constraints or domain rules.
3. Share the test command(s) Codex should run and whether network access is available.
4. Expect Codex to:
   - draft a plan,
   - make only scoped edits,
   - run/describe tests,
   - summarize diffs for review.
5. Apply or cherry-pick the resulting changes only after you verify locally.

## Refactor Log
Use this table to record ongoing work (newest first):

| Date | Area | Branch | Driver | Goal & Notes |
| --- | --- | --- | --- | --- |
| 2025-11-19 | ui/pdf export | `codex-download` | Mark/Codex | Added versioned footer with Terms/Privacy links, placeholder legal docs, and a first-pass PDF export feature (download/view/print). Smoke-tested via Streamlit; PDF layout verified manually. |
| 2025-11-19 | core/scenario_engine & miner models | `codex-refactor-first` | Mark/Codex | Added regression coverage (`tests/test_scenario_engine.py`), synced miner output tests with `NetworkData`, split scenario models/calculations/finance helpers into dedicated modules (including weighted margin + payback helpers), and moved `MinerOption` into `src/core/miner_models.py` so core logic no longer imports UI modules. `pytest` all green post-refactor. |

| _YYYY-MM-DD_ | _e.g., core/scenarios_ | `codex-refactor/<topic>` | _Mark/Codex_ | _What problem we’re solving, key tests run, follow-ups_ |


Add a new row for each effort so we can track progress and revisit decisions later.

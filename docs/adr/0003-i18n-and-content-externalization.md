# 0003 – i18n and content externalization (planned)
Date: 2025-11-22  
Status: Accepted (backlog)

## Context
- Text appears in multiple places (UI, assumptions tab, PDF). We want a single source of truth.
- Future need for non-developers to edit copy and potentially support multiple languages.

## Decision
- Move toward externalized content files (e.g., JSON/YAML/Markdown under `docs/content`).
- Load content once and reuse across UI and PDF instead of duplicating strings in code.
- Plan for language keys (en, fr, etc.) to enable future i18n via a selector/config.

## Consequences
- Short-term: existing copy remains in code; refactor later to read from content files.
- Future work: add a content loader helper and update UI/PDF renderers to pull from the external source.
- Enables non-dev editing and clean i18n without code changes once implemented.

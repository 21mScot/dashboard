# 0004 – FOSS-first policy
Date: 2025-11-22  
Status: Accepted

## Context
- We prefer free and open-source software (FOSS) for dependencies, tooling, and data sources wherever practical.
- Proprietary choices should be justified and tracked.

## Decision
- Default to FOSS libraries/services with permissive licenses (MIT/Apache-2.0/BSD) and maintainable communities.
- Require explicit rationale for proprietary components when FOSS does not meet security, reliability, or feature needs.
- Track exceptions and revisit periodically; prefer replacing proprietary parts with FOSS when viable.
- Contribute back upstream where possible (bug reports/fixes) to sustain dependencies.

## Consequences
- Dependency selection and architecture reviews should check FOSS options first.
- Proprietary additions must document justification and any exit/replacement plan.
- Licensing compliance and security reviews remain mandatory for all dependencies.

# ADR-001: Transition to Domain-Driven Modular Architecture

- **Status**: accepted
- **Date**: 2026-06-04

## Context
The ConfigStream repository contained several monolithic "god objects," specifically `src/configstream/output_logic.py` (77KB) and `frontend/assets/js/lab.js` (75KB). These files had multiple responsibilities, making them difficult to maintain, test, and audit for security. The monolithic frontend structure also necessitated broad 'unsafe-inline' Content Security Policy (CSP) directives.

## Decision
We decided to decompose these monoliths into domain-driven packages and ES modules.

1.  **Backend Decomposition**: Created `src/configstream/output/` to house specialized modules:
    *   `metadata.py`: Handles analytics and health telemetry.
    *   `public_lists.py`: Generates protocol and country-specific URI lists.
    *   `native_configs.py`: Builds profiles for Sing-box, Clash, and third-party adapters.
    *   `subscriptions.py`: Manages Base64/plaintext formatting and packaging.
    *   `output_logic.py` was refactored into a thin orchestrator that delegates to these modules.

2.  **Frontend Modularization**: Created `frontend/assets/js/lab/` to house a modern ES6 package:
    *   `state.js`: Centralized state management.
    *   `ui.js`: Programmatic DOM construction (replacing `innerHTML`).
    *   `parser.js`: Proxy URI and subscription parsing logic.
    *   `builder.js`: Chain configuration generation.
    *   `exporters.js`: Export format builders (Clash, Xray, etc.).
    *   `index.js`: Main entry point and event wiring.

3.  **Security Mandate**: As part of this transition, we strictly enforced the removal of `innerHTML` in favor of programmatic DOM manipulation to mitigate XSS risks.

## Alternatives considered
*   **Incremental Refactoring**: Rejected because the technical debt was too large and blocked critical security hardening (CSP fixes).
*   **Complete Rewrite**: Rejected as the existing logic was functional and well-tested; surgical extraction was safer.

## Consequences
### Positive
*   **Improved Maintainability**: Clear separation of concerns makes it easier to add new output formats or lab features.
*   **Enhanced Security**: Significantly reduced XSS attack surface by eliminating `innerHTML`.
*   **Better Testability**: Modules can now be unit-tested in isolation without mocking the entire pipeline.
*   **Faster Frontend Build**: i18n and modular JS allow for better code-splitting and smaller initial payloads.

### Negative
*   **Increased File Count**: Navigating the codebase now requires understanding the package structure.
*   **Breaking Change for Legacy Imports**: Any scripts importing directly from `output_logic.py` internals required updates (mitigated by re-exports in the orchestrator).

### Neutral
*   **Modern Tooling Requirement**: Development now requires a build step (Vite) for the frontend, which was already partially in place.

## Links
*   [GEMINI.md](../../GEMINI.md)
*   [SECURITY.md](../../SECURITY.md)

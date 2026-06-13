# ConfigStream Gemini CLI Mandates

This file establishes foundational mandates for AI agents contributing to the ConfigStream repository. These instructions take absolute precedence over general defaults.

## 1. Modular Architecture Mandate
The repository has transitioned from monolithic "god objects" to a domain-driven modular structure.
*   **Backend**: All output generation logic MUST reside in the `src/configstream/output/` package. `output_logic.py` is reserved exclusively for orchestration and backward compatibility.
*   **Frontend**: All complex UI logic MUST be modularized into ES6 packages under `frontend/assets/js/`. The "Laboratory" logic MUST reside in `frontend/assets/js/lab/`.

## 2. Security (XSS) Mandate
ConfigStream operates in a high-risk environment. Dynamic rendering of untrusted data (proxies, metadata, user input) MUST NOT use `innerHTML`.
*   **Standard**: Use `document.createElement`, `textContent`, and `appendChild` or `replaceChildren`.
*   **Exception**: `innerHTML` is only permitted for constant, trusted internal strings in UI helpers (e.g., `showResultHTML`) and MUST be explicitly audited.

## 3. Data Integrity & Schema Compliance
*   **Proxy Model**: The `uuid` field in the root `Proxy` model MUST be a valid UUIDv4.
*   **Credentials**: Non-UUID credentials (usernames, passwords, hashes) MUST be stored in `proxy.details`. Parsers MUST enforce this separation to prevent downstream schema validation failures.

## 4. Source of Truth
*   **Canonical Source**: `consolidated_sources.txt` is the single canonical source of truth for proxy subscription URLs.
*   **Deprecated**: Never use or recreate `sources/backup_dynamic/`.

## 5. Legacy Pipeline Retirement
The repository has completed the migration from legacy monolithic pipeline orchestrators (`pipeline.py`, `fetcher.py`, `producer.py`, `consumer.py`) to a domain-driven `StandardPipeline` within the `src/configstream/pipeline/` package.
*   **Mandate**: All new pipeline development MUST utilize `StandardPipeline`, `StreamingProducer`, and `WorkerConsumer` within the `src/configstream/pipeline/` package.
*   **Deletion**: Legacy files `pipeline.py`, `fetcher.py`, `producer.py`, `consumer.py` have been removed. Do not reintroduce them.


## 7. Truth Hierarchy
When status surfaces disagree, use this hierarchy:
1.  `STATUS.md` (Current operational posture)
2.  Machine-readable contracts (`docs/*.json`, `docs/DEBT_MATRIX.md`)
3.  `AGENTS.md` (Contributor constraints)
4.  `CHANGELOG.md` (Implementation history)
5.  Removed historical source-of-truth ledgers (git-history provenance only; durable value is absorbed into the active master/status chain)

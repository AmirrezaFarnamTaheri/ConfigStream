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
*   **Canonical Source**: `sources/batch_*.txt` are the authored operational source lists. Do not create a duplicate root mirror.
*   **Deprecated**: Never use or recreate `sources/backup_dynamic/`.

## 5. Canonical Pipeline and Compatibility Shims
The canonical pipeline implementation lives in `src/configstream/pipeline/`. All new pipeline development MUST use `StandardPipeline`, `StreamingProducer`, `WorkerConsumer`, and `src/configstream/pipeline/fetcher.py`.
*   Root `src/configstream/producer.py` and `src/configstream/consumer.py` remain thin compatibility shims.
*   Root `pipeline.py` and `fetcher.py` are absent; do not recreate them.
*   Optional network, GeoIP, and native-tester integrations must remain lazy so dry-run and orchestration imports do not require unused extras.

## 6. Verification and Release Truth
*   `docs/readiness.json` and generated `STATUS.md` remain `CONDITIONAL` until exact-head CI, sealed artifacts, and live Pages checks pass for the same commit.
*   `docs/readiness.json` is the canonical release checkpoint; `STATUS.md` is its generated human-readable projection.
*   Run `python scripts/verify_repository.py --profile full` before any release-readiness claim. Report unavailable checks separately.

## 7. Truth Hierarchy
When status surfaces disagree, use this hierarchy:
1.  Canonical machine-readable contracts (`docs/readiness.json` for release posture and the other maintained `docs/*.json` contracts for their domains)
2.  Generated `STATUS.md` (human-readable projection of release posture)
3.  `AGENTS.md` (Contributor constraints)
4.  `CHANGELOG.md` (Implementation history)
5.  Historical point-in-time audit reports (provenance only; never current operational truth)

# Architectural Bridge Nodes & Coupling Audit

This document contains an audit of bridge nodes with high betweenness centrality within the ConfigStream codebase.

## Architectural Bridge Nodes Betweenness Centrality Table

| Bridge Node / Function | File / Module | Betweenness Centrality | Primary Role |
|---|---|---|---|
| `GoBatchTester.test_custom_configs` | `src/configstream/testers/go_tester/manager.py` | 0.0124 | Bridges proxy configuration models with the external daemon IPC pipeline. |
| `test_chain_config` | `src/configstream/testers/lab_chain_tester.py` | 0.0055 | Bridges singbox testing context with the laboratory API execution flow. |
| `validate_pages_artifact` | `scripts/validate_pages_artifact.py` | 0.0048 | Bridges deployment artifact checks with domain schema validation and cryptographic verification. |

## Module Ownership & Import Boundary Audit

### 1. `GoBatchTester.test_custom_configs`
- **Ownership:** Belongs to the core proxy testing subsystem (`configstream.testers`).
- **Import Boundaries:** Integrates models, network logic, and asynchronous processing, orchestrating configuration batching through standard input to the Go daemon. It properly encapsulates the complexity of IPC communication. 
- **Observations:** No immediate cyclic dependencies, but tight coupling with evasion enrichment logic and proxy models.

### 2. `test_chain_config` (in `lab_chain_tester.py`)
- **Ownership:** Belongs to the API laboratory testing module.
- **Import Boundaries:** Depends on `singbox2proxy` and `aiohttp` for proxy verification, establishing a bridge between REST inputs and asynchronous sub-process invocation.
- **Observations:** Contains conditional import boundaries and `SecureConfigContext` coupling which prevents direct circular issues but couples the testing capability directly to singbox environments.

### 3. `validate_pages_artifact` (in `scripts/validate_pages_artifact.py`)
- **Ownership:** CI/CD and deployment pipeline module.
- **Import Boundaries:** Heavily couples internal schema rules, native client process testing (e.g. `sing-box check`), and cryptographic signature handling all in one giant procedural script.
- **Observations:** While it resides in `scripts/`, its responsibilities leak across many domains (schema validation, security secret scanning, cryptography).

## Circular Dependency & Tight Coupling Findings

- **GoBatchTester:** Highly centralized, tightly coupling JSON serialization, daemon management, and model enrichment (e.g. `enrich_outbound_with_evasion`). This makes it a significant structural bottleneck.
- **Lab Chain Tester:** The dependency on dynamic `singbox2proxy` availability is relatively isolated, minimizing circular imports, but tightly pairs the tester logic to the API framework context.
- **Pages Artifact Validator:** Monolithic structure where all validation (cryptographic, schema, file presence, secrets) is combined. High coupling but restricted to the CI boundary.

## Refactoring Boundary Recommendations

1. **Decouple IPC from Tester Logic (`GoBatchTester`)**:
   - Extract the low-level JSON IPC and subprocess daemon orchestration into a dedicated `DaemonManager` or `IPCPipeline` class. 
   - Decouple `enrich_outbound_with_evasion` from the tester batching to ensure proxy conversion and evasion logic is applied upstream.

2. **Abstract Chain Testing Interfaces (`lab_chain_tester.py`)**:
   - Isolate the `singbox2proxy` specific execution into an interface (e.g., `ChainExecutionEngine`), allowing easier mocking and expansion to other core engines without modifying the API boundary.

3. **Modularize the CI Validation Script (`validate_pages_artifact.py`)**:
   - Break down the monolithic script into discrete modules: `schema_validator`, `crypto_verifier`, and `secret_scanner`.
   - Maintain the main script strictly as a runner/orchestrator of these decoupled validators.

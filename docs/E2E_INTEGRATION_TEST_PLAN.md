# E2E & Integration Test Plan

## 1. Current Test Suite Architecture Assessment
The ConfigStream test suite is currently partitioned into Unit and E2E boundaries, though the boundaries are sometimes blurred by excessive mocking in integration contexts.

*   **Unit Tests (`tests/unit/`)**: Exhibits comprehensive coverage for internal application logic. Tests rely heavily on `unittest.mock` (e.g., `test_pipeline_extended.py` mocks `SingBoxTester`, `ProxyWasher`, `EventStream`). 
    *   **WASM Sandbox**: Tested statically (`test_wasm_browser_semantics.py`) using regex/AST inspections on `wasm_main.go` and docs to ensure "browser-limited" constraints are communicated.
    *   **Artifact Contracts**: High coverage. `test_validate_output_matrix.py` properly guards `docs/output_matrix.json` ensuring no schema drift, file presence, or zip packing discrepancies occur.
*   **E2E Tests (`tests/e2e/`)**: Contains Python Playwright tests for the frontend (`test_frontend.py`) and a basic smoke test for the pipeline (`test_pipeline_real.py`). 
    *   *Gap*: `test_pipeline_real.py` executes with `dry_run=True`, bypassing real network connectivity and Go tester execution.
    *   *Gap*: Playwright tests use inline locators and complex route interceptions without a Page Object Model (POM), making them brittle to UI refactors.

## 2. E2E & Integration Test Coverage Matrix

| Component | Unit Coverage | Integration/E2E Coverage | Identified Gaps |
| :--- | :--- | :--- | :--- |
| **`StandardPipeline`** | High (Logic mocked) | Low (`dry_run` mode only) | True end-to-end processing with a local dummy testing server handling real traffic. |
| **WASM Browser Sandbox** | Medium (Textual asserts) | None | Real execution of the `.wasm` module in a browser engine communicating with a mock WebSocket proxy. |
| **Artifact Contracts** | High (Schema & Script valid) | N/A | Verification of actual generated artifacts within an E2E pipeline execution. |
| **Laboratory UI (`/lab`)** | Low | Low (Basic loads checked) | Deep user flow testing, WASM connectivity simulation, Exporter UI tests, and POM abstraction. |

## 3. Playwright POM & Test Suite Specifications for Laboratory UI
To stabilize testing for `frontend/assets/js/lab/*`, a Page Object Model (POM) strategy must be adopted.

### POM Architecture
*   **`LabPage`**: The root page object controlling `/lab.html`. Handles page navigation, frame initialization, and global loading states (`ui.js`).
*   **`BuilderComponent`**: Maps to `builder.js`. Handles UI inputs for constructing/editing proxy configurations and parsing share links (`parser.js`).
*   **`CleanIpsComponent`**: Maps to `clean-ips.js`. Controls IP selection, region filtering, and dispatching washing tasks.
*   **`ExporterComponent`**: Maps to `exporters.js`. Handles UI selection of export formats (Clash, Sing-Box, JSON) and verifying the clipboard or downloaded blobs.

### Playwright Test Specs (Examples)
1.  **Config Import Flow**: 
    *   *Action*: `LabPage.Builder.pasteConfig('vless://...')` -> `LabPage.Builder.clickParse()`
    *   *Assertion*: Expect internal state (`state.js`) to reflect correct protocol parsing, and UI fields to populate accurately.
2.  **Export Flow Validation**: 
    *   *Action*: Add mock proxies to state -> `LabPage.Exporter.selectFormat('Clash')` -> `LabPage.Exporter.download()`
    *   *Assertion*: Intercept download event, read stream, and validate YAML structure against expected Clash schema.

## 4. WASM Sandbox Integration Test Patterns
Since testing WASM statically is insufficient, we will introduce a dynamic integration pattern:

1.  **Mock Target Server**: Spin up a local Python asyncio WebSocket server that mimics a proxy backend (accepting standard handshake, returning mock payload).
2.  **Test Harness Page**: Serve a minimal HTML page that instantiates `wasm_main.go` (compiled to `.wasm`).
3.  **Playwright Evaluation**: 
    *   Use `page.evaluate()` to trigger the WASM exported testing functions directly.
    *   Provide the local Mock WebSocket Server URL.
    *   Assert that the WASM function returns the correct payload (e.g., success status, latency > 0ms).
4.  **Network Disconnect Tests**: Programmatically kill the mock WebSocket server mid-flight and assert that the WASM module handles the drop gracefully without crashing the browser tab.

## 5. CI/CD Test Pipeline Execution Strategy
To support robust execution of these E2E patterns, the GitHub Actions (or equivalent CI) pipeline must be enhanced.

*   **Test Segmentation**:
    *   `pytest -m unit`: Runs on all commits. Extremely fast.
    *   `pytest -m e2e`: Runs on PRs to `main` or explicitly triggered. Utilizes the Playwright docker image (`mcr.microsoft.com/playwright:v1.xx.x-jammy`).
*   **Flaky Test Mitigation**:
    *   Strictly forbid arbitrary `time.sleep()`. Force the use of Playwright's auto-waiting locators (`expect(locator).to_be_visible()`).
    *   Configure Pytest to automatically retry failing E2E tests up to 2 times (`--reruns 2`).
*   **Artifact Collection**:
    *   Configure `pytest-playwright` to capture traces and screenshots on failure (`--tracing=retain-on-failure --screenshot=only-on-failure`).
    *   Upload the `test-results/` directory as a CI artifact for debugging pipeline crashes.

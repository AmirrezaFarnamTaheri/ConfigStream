# `validate_pages_artifact.py` Audit Report

## Artifact Validation Pipeline Flowchart

```text
+---------------------+
|  CI / CLI Trigger   |
| (Artifact Root Dir) |
+---------+-----------+
          |
          v
+-----------------------------+
| Directory & Path Resolution |  <-- Uses `_safe_join` to prevent traversal
+---------+-------------------+
          |
          v
+-----------------------------+
| File Existence & Size Check |  <-- Verifies against `REQUIRED_EXISTS` & `REQUIRED_NONEMPTY`
+---------+-------------------+
          |
          v
+-----------------------------+
|    Schema & JSON/YAML       |  <-- In-memory custom validation (`_validate_schema_rule`)
|    Syntax Validation        |      for JSON and Clash YAML structures
+---------+-------------------+
          |
          v
+-----------------------------+
| Bundle & Core Checks        |  <-- Validates Sing-box/Clash internal references
| (ZIP integrity, Data leaks) |  <-- Scans ZIP members for deployed secrets
+---------+-------------------+
          |
          v
+-----------------------------+
| Native Binary Verification  |  <-- Optional local `sing-box check` & `mihomo -t -f`
+---------+-------------------+
          |
          v
+-----------------------------+
| Exit & Return Code (0 / 1)  |  <-- Aggregates all errors, returns 1 if any failure
+-----------------------------+
```

## Schema & Output Matrix Verification Table

| Artifact Category | Output Matrix Spec (`docs/output_matrix.json`) | Implementation in Script | Compliance / Gap Analysis |
|-------------------|----------------------------------------------|--------------------------|---------------------------|
| **Control** | `metadata.json`, `health.json`, `artifact_manifest.json` | Validated via custom subset of JSON Schema parser against local `.schema.json` files | **Compliant**. Also includes signature verification (Ed25519) for manifests. |
| **Subscription (Base64/Text)** | `base64*.txt`, `proxies*.txt` | Checked for existence (`REQUIRED_EXISTS`), not required to be non-empty (`nonempty: false`). | **Compliant**. Accurately matches the matrix allowance for degraded/empty sets. |
| **Sing-box Configs** | `singbox*.json`, `chains*.json` | Custom structural validation (`_validate_singbox_config` checks tags, detours, DNS, rules). | **Compliant**. Deep semantic validation catches dead/duplicate references. |
| **Clash Configs** | `clash*.yaml` | Structural validation (`_validate_clash_config`) requiring `PyYAML` to catch proxy-group and rule errors. | **Compliant**. |
| **Bundles (ZIPs)** | `side_products*.zip` | Enforces safe member paths, presence of `proxies.txt`, and scans for 10+ secret markers up to 1MB. | **Compliant**. Good defense against accidental CI token injection. |

## Cross-Platform File Read & Path Safety Audit

- **Path Traversal Protection**: The `_safe_join` function resolves absolute paths and enforces that the target resides inside the resolved `root` directory (`root_resolved not in target.parents`). This prevents zip slips or traversal attacks.
- **File Encoding Consistency**: Hardcoded `encoding="utf-8"` across all read operations (`_load_json`, `_load_yaml`, pipeline event reading). This ensures safe cross-platform reads without relying on the OS default encoding (which varies on Windows).
- **Memory/Performance Profile**:
  - Hashing (`_sha256`) uses buffered streaming (1MB chunks) via `iter(lambda: handle.read(1024 * 1024), b"")`, preventing OOM issues on large artifacts.
  - Zip secret scanning is strictly bounded to `ZIP_SECRET_SCAN_MAX_BYTES` (1MB).
  - **Minor Risk**: `pipeline_events.jsonl` is parsed using `.read_text().splitlines()`. For enormous telemetry files, this could spike memory, but given GitHub Pages size limits, it's realistically acceptable.
  - **Minor Risk**: JSON and YAML structures are parsed directly into memory. Acceptable given artifact constraints.

## CI Exit Code & Blocker Detection Assessment

- **Exit Codes**: The script relies on an aggregated error list (`errors: list[str]`). If the list is populated, it outputs the aggregated errors to stdout and `return 1` cleanly from `main()`. If empty, returns `0`.
- **Error Truncation**: For lists with excessive proxy issues, limits error logging via `MAX_PROXY_VALIDATION_ERRORS = 500`. This prevents pipeline log pollution and out-of-storage CI failures.
- **Subprocess Safety**: Native core validations utilize `subprocess.run` with `capture_output=True` and a strict `timeout=30`, preventing hanging jobs. Non-zero exits from native binaries are captured and seamlessly injected into the error stream. Output is cleanly truncated at 500 chars to avoid overwhelming CI runners.

## Refactoring & Hardening Roadmap

1. **Replace Custom Schema Validator**: The custom `_validate_schema_rule` logic replicates standard `jsonschema` library behavior. Long-term, adding `jsonschema` to the dependencies would remove hundreds of lines of complex recursion and edge cases.
2. **Streaming for Large JSONL**: Refactor `_validate_pipeline_events` to read `pipeline_events.jsonl` lazily via file object iteration rather than `read_text().splitlines()`, protecting against memory exhaustion for exceptionally large telemetry bursts.
3. **Formal Exception Handling in Main**: While returning 1 on structural validation errors is solid, wrapping `main` execution in a try/except block to catch unhandled `OSError` or `json.JSONDecodeError` and transforming them into managed error prints before exiting with code `1` or `2` would ensure clean CI signals rather than generic Python tracebacks.
4. **Extend Manifest Coverage**: Extend `ZIP_SECRET_SCAN_MAX_BYTES` logic across all generated plain-text configurations (like `proxies.txt` or JSONs) to guarantee no secrets leak into *any* published file, not just the ZIP bundles.

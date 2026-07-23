# Architecture Blast Radius Deep-Dive

This document maps the complete blast radius of the top 3 hub nodes in the ConfigStream repository.

## Hub 1: `to_singbox_outbound`
- **Location**: `src/configstream/converters/singbox.py`
- **Degree**: 218

### Source Summary
Converts a `Proxy` model object into a Sing-box outbound JSON dictionary. It is highly complex, containing strict structural requirements and protocol-specific transformations (VMess, VLESS, WireGuard, Shadowsocks, Trojan, etc.). The function enforces strict data validation, sanitization of inputs (e.g., removing unsupported flows or methods), and drops proxies that are structurally unsound.

### Call Graph Table
| Hop Level | Caller Module | Caller Function / Context |
|-----------|---------------|---------------------------|
| 1-Hop     | `src/configstream/testers/go_tester/manager.py` | `GoBatchTester.test_batch` |
| 1-Hop     | `src/configstream/generators/singbox.py` | Sing-box template generation |
| 1-Hop     | `src/configstream/intelligence/washer/core.py` | Proxy washing routines |
| 1-Hop     | `src/configstream/converters/chains.py` | Chain evaluation |
| 2-Hop     | `src/configstream/testers/manager.py` | Tester multiplexer |
| 2-Hop     | `src/configstream/pipeline/consumer.py` | Testing pipeline workers |

### Test Coverage
- `tests/unit/converters/test_singbox_bool_fix.py`
- `tests/unit/converters/test_singbox_converters.py`
- `tests/unit/converters/test_singbox_fix.py`
- `tests/unit/coverage_boost/test_converters_coverage.py`
- `tests/unit/generators/test_singbox_comprehensive.py`
- `tests/unit/test_converters.py`
- `tests/unit/test_protocol_output_golden.py`

### Output Artifacts Dependency
- `singbox_config.json` and associated client formats.
- Indirectly all output artifacts, since the `GoBatchTester` relies on this conversion to test proxies correctly. A failure here marks the proxy as invalid across the pipeline.

### Safe Refactoring Boundary
- **Refactoring Risk**: Critical
- **Boundary**: Extract protocol-specific logic into isolated functions (e.g., `_convert_vmess`, `_convert_wireguard`). The outer boundary (signature: `(proxy: Proxy) -> Optional[Dict]`) must not change, as its None-return behavior is load-bearing in the pipeline to filter out bad proxies.

---

## Hub 2: `GoBatchTester.test_batch`
- **Location**: `src/configstream/testers/go_tester/manager.py`
- **Degree**: 209

### Source Summary
Handles asynchronous batch IPC with the Go-based tester binary via `stdin`/`stdout`. It converts proxies into Sing-box outbounds, adds evasion features, serializes them, and streams them to the daemon. It manages timeouts, process crashes, deduplication of concurrent futures, and assigns the response attributes (latency, working status, errors) back to the Python `Proxy` models.

### Call Graph Table
| Hop Level | Caller Module | Caller Function / Context |
|-----------|---------------|---------------------------|
| 1-Hop     | `src/configstream/testers/manager.py` | `TesterManager.test_batch` |
| 1-Hop     | `src/configstream/pipeline/consumer.py` | `consumer_worker` loop |
| 1-Hop     | `src/configstream/testers/go_tester/interfaces.py` | Go tester interfaces |
| 2-Hop     | `src/configstream/pipeline/core.py` | Main pipeline orchestration |

### Test Coverage
- `tests/test_manager.py`
- `tests/unit/test_consumer.py`
- `tests/unit/test_cross_engine_parity.py`
- `tests/unit/test_go_tester_streaming.py`
- `tests/unit/test_pipeline_stages.py`

### Output Artifacts Dependency
- Defines which proxies survive into the final `data/` and `assets/` distributions.
- Impacts latencies listed in `metadata.json`.

### Safe Refactoring Boundary
- **Refactoring Risk**: High
- **Boundary**: Do not decouple the `Proxy` object mutation from the IPC event loop directly unless you return a state differential. The safest refactoring is to abstract the `_ensure_process` and low-level `stdin.write` into an isolated Daemon client class, leaving `test_batch` strictly for payload framing and state application.

---

## Hub 3: `save_metadata`
- **Location**: `src/configstream/output/metadata.py`
- **Degree**: 162

### Source Summary
Aggregates metrics for the entire run (e.g., country stats, protocol distribution, latency buckets, testing drop reasons) from the collection of proxies and the pipeline stats object. It writes this analytical data out as a public contract JSON (`metadata.json`).

### Call Graph Table
| Hop Level | Caller Module | Caller Function / Context |
|-----------|---------------|---------------------------|
| 1-Hop     | `src/configstream/output_handler.py` | `handle_outputs` |
| 1-Hop     | `src/configstream/output_logic.py` | Orchestration wrappers |
| 2-Hop     | `CLI / __main__.py` | Application teardown / completion |

### Test Coverage
- `tests/unit/test_analytics_output.py`
- `tests/unit/test_metadata_completeness.py`
- `tests/unit/test_output.py`
- `tests/unit/test_output_full.py`
- `tests/unit/test_pipeline_extended.py`

### Output Artifacts Dependency
- `metadata.json`
- `health.json`
- `artifact_manifest.json`

### Safe Refactoring Boundary
- **Refactoring Risk**: Medium
- **Boundary**: Extract the metric aggregation (the massive loops collecting ASNs, countries, latencies) into a pure `build_metadata_model(stats, proxies)` function that returns a dataclass. Keep `save_metadata` strictly for writing the dataclass to the filesystem.

---

## Cross-Hub Dependency Matrix
| Origin Hub | Depends on | Context |
|------------|------------|---------|
| `GoBatchTester.test_batch` | `to_singbox_outbound` | The Go tester relies on `to_singbox_outbound` to serialize the `Proxy` object into a config it can test. A failure in Hub 1 means the proxy is immediately failed without reaching IPC. |
| `save_metadata` | `GoBatchTester.test_batch` | Metadata aggregates latencies and specific drop reasons (e.g., `DIRTY_IP`, `TIMEOUT`) injected into proxy models by the Go Tester. |

## Refactoring Risk Rating
- **`to_singbox_outbound`**: **Critical**
- **`GoBatchTester.test_batch`**: **High**
- **`save_metadata`**: **Medium**

## ASCII Dependency Flow Diagram
```text
[Raw Proxy Model]
       |
       v
(1) to_singbox_outbound  <------- [Config Generators & Intelligence Washers]
       |
       v
[JSON Config Object]
       |
       v
(2) GoBatchTester.test_batch  <-- [Pipeline Consumer & Multiplexer]
       |
       v
[Mutated Proxy Model w/ Latency & State]
       |
       v
(3) save_metadata  <------------- [Output Handler & App Completion]
       |
       v
[metadata.json & health.json]
```

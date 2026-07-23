# Monolithic Functions & High-Cyclomatic De-Slop Audit

This document outlines the refactoring strategy ("de-slopping") for four major monolithic components identified within the ConfigStream repository. The goal is to enforce Single-Responsibility Principle (SRP), reduce cyclomatic complexity, and maintain 100% backward compatibility for downstream consumers and tests.

## 1. Complexity & Line Count Audit

| Component / Function | File Path | Scope (Lines) | Est. Cyclomatic Complexity | Assessment |
|----------------------|-----------|---------------|----------------------------|------------|
| `DNSScannerTUI` | `src/configstream/tools/dns_scanner/python/dnsscanner_tui.py` | 525 - 2007 (~1483 lines) | ~125 | Severe God-Class. UI logic, state management, and async I/O tightly coupled. |
| `ProxyWasher` | `src/configstream/intelligence/washer/core.py` | 52 - 983 (~932 lines) | ~85 | Domain logic intertwined with parallel execution, retries, and data parsing. |
| `GoBatchTester` | `src/configstream/testers/go_tester/manager.py` | 35 - 883 (~849 lines) | ~72 | Excessively handles subprocess lifecycle, stream parsing, and metrics aggregation. |
| `to_singbox_outbound`| `src/configstream/converters/singbox.py` | 198 - 754 (~557 lines) | ~95 | Massive `if/elif` chain for protocol switching, config mutation, and validation. |

---

## 2. Structural Refactoring Plans

### A. `DNSScannerTUI` (1,483 lines)
**Issue:** `DNSScannerTUI` handles rendering (curses/Textual), async DNS resolution polling, configuration state, and event callbacks all in a single class.

**Decomposition Plan:**
1. **Model-View-Presenter (MVP) Split:** Extract view rendering into `DNSScannerView`.
2. **State Manager:** Extract scan state into an observable `ScanStateManager`.
3. **Async Poller:** Isolate background task management into `DNSAsyncPoller`.

**Flowchart (ASCII):**
```text
[ Legacy: DNSScannerTUI ]
          |
     (Decomposed into)
          |
  +-------+-------+
  |               |
[View]       [Presenter] ----> [ScanStateManager]
(Renders)    (Binds I/O)       (Tracks progress)
                  |
            [DNSAsyncPoller]
            (Runs queries)
```

### B. `ProxyWasher` (932 lines)
**Issue:** `ProxyWasher` mixes the generic proxy filtering algorithm with network I/O, error retry logic, and rule parsing.

**Decomposition Plan:**
1. **Rule Engine:** Extract filtering rules into `WasherRuleEngine`.
2. **I/O Coordinator:** Extract retry and batching logic into `WasherWorkerPool`.
3. **Core Validator:** Keep `ProxyWasher` strictly as the high-level API orchestrator (Façade).

**Flowchart (ASCII):**
```text
[ Legacy: ProxyWasher ]
          |
    (Delegates to)
          |
  +-------+-------+
  |               |
[RuleEngine]   [WorkerPool]
(Filters)      (I/O, Retries)
```

### C. `GoBatchTester` (849 lines)
**Issue:** Responsible for Go binary lifecycle management, IPC (Inter-Process Communication), JSON stream parsing, and telemetry.

**Decomposition Plan:**
1. **Subprocess Manager:** Extract `GoSubprocessLifecycle` to handle spawn/kill/signals.
2. **Stream Parser:** Extract `TesterStreamParser` for reading JSON/stdout asynchronously.
3. **Result Aggregator:** Extract `MetricsAggregator` for storing ping/latency results.

**Flowchart (ASCII):**
```text
[ Legacy: GoBatchTester ]
          |
     (Refactored as)
          |
[GoBatchTester (Façade)]
  |---> [GoSubprocessLifecycle]
  |---> [TesterStreamParser]
  +---> [MetricsAggregator]
```

### D. `to_singbox_outbound` (557 lines)
**Issue:** A single monolithic function containing dozens of `if node_type == 'vmess': ... elif node_type == 'vless': ...` blocks, deeply nested validation, and dict mutations.

**Decomposition Plan:**
1. **Protocol Handlers Registry:** Create a strategy pattern registry `SingboxProtocolHandler`.
2. **Handler Classes:** Break down logic into `build_vmess_outbound()`, `build_vless_outbound()`, `build_trojan_outbound()`, etc.
3. **Common Mutators:** Extract TLS/Transport builders into shared utility functions.

**Flowchart (ASCII):**
```text
[ Legacy: to_singbox_outbound(node) ]
          |
     (Routes via)
          |
[SingboxOutboundRegistry]
  |-- vmess -> build_vmess()
  |-- vless -> build_vless()
  |-- trojan -> build_trojan()
```

---

## 3. Backward-Compatible Refactoring Interfaces

To maintain 100% test compatibility, the original class/function signatures will be preserved as "Façades" or thin wrappers over the new internal components.

### Example: Preserving `to_singbox_outbound`
```python
# src/configstream/converters/singbox.py

def to_singbox_outbound(proxy: dict) -> dict:
    """
    Legacy wrapper maintaining 100% API compatibility.
    Internally delegates to the new Registry pattern.
    """
    from .singbox_handlers import outbound_registry
    
    protocol = proxy.get("type")
    handler = outbound_registry.get_handler(protocol)
    if not handler:
        raise ValueError(f"Unsupported protocol: {protocol}")
        
    return handler.build(proxy)
```

### Example: Preserving `ProxyWasher`
```python
# src/configstream/intelligence/washer/core.py

class ProxyWasher:
    """
    Backward-compatible Façade. 
    State and execution have been delegated to specialized classes.
    """
    def __init__(self, config=None):
        self._engine = WasherRuleEngine(config)
        self._pool = WasherWorkerPool()
        
    async def wash(self, proxies: list) -> list:
        # Thin delegation
        valid_proxies = self._engine.filter_initial(proxies)
        return await self._pool.execute_tests(valid_proxies)
```

This structural shift ensures that existing integration tests and consuming modules will not break while significantly lowering the cognitive load and cyclomatic complexity for maintainers.

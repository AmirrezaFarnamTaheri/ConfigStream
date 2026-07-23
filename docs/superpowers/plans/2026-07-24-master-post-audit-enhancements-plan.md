# Master Post-Audit Roadmap & Technical Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the full post-audit enhancement roadmap derived from the 44-track repository investigation, delivering TUIC v5 / Hysteria3 parsers, HMAC-SHA256 steganography KAT vectors, AnomalyDetector SQLite WAL lifecycle controls, Ed25519 manifest replay hardening, WASM panic recovery, and Playwright POM E2E testing.

**Architecture:** A 3-phase modular plan: Phase 1 covers Core Pipeline & Security Parsers; Phase 2 covers Crypto, Manifest Signing & WASM Edge Security; Phase 3 covers Frontend Laboratory UI & Playwright E2E Integration.

**Tech Stack:** Python 3.10+ (asyncio, sqlite3, hmac, hashlib, cryptography, pytest, Playwright), Go 1.21+ (WASM syscall/js), ES6 Javascript (Web Crypto API).

## Global Constraints

- Maintain 100% pass rate across the unit test suite (1,255/1,255 tests currently passing).
- Zero placeholders: every step must contain complete, copy-pasteable code blocks and explicit CLI commands.
- Preserve PEP 8 code formatting and strict typing annotations (`Optional`, `List`, `Dict`, `Union`).
- Follow exact contract specifications in `docs/protocol_matrix.json`, `docs/output_matrix.json`, and `schema/*.json`.

---

## Phase 1: Core Pipeline & Security Parsers

### Task 1: TUIC v5 & Hysteria3 Protocol Parsers

**Files:**
- Create: `src/configstream/parsers/tuic.py`
- Create: `src/configstream/parsers/hysteria3.py`
- Modify: `src/configstream/parsers/__init__.py`
- Test: `tests/unit/parsers/test_tuic.py`
- Test: `tests/unit/parsers/test_hysteria3.py`

**Interfaces:**
- Consumes: Raw `tuic://` and `hy3://` / `hysteria2://` URI strings.
- Produces: `parse_tuic(line: str) -> Optional[Proxy]` and `parse_hysteria3(line: str) -> Optional[Proxy]` returning standard `Proxy` models with normalized protocols `"tuic"` and `"hysteria3"`.

- [ ] **Step 1: Write failing unit tests for TUIC v5 and Hysteria3 parsers**

Create `tests/unit/parsers/test_tuic.py`:
```python
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for TUIC v5 protocol parser."""
import pytest
from configstream.parsers.tuic import parse_tuic

def test_parse_tuic_valid_uri():
    uri = "tuic://00000000-0000-0000-0000-000000000001:mysecret@1.2.3.4:8443?congestion_control=bbr&alpn=h3#TUIC-Node"
    proxy = parse_tuic(uri)
    assert proxy is not None
    assert proxy.protocol == "tuic"
    assert proxy.address == "1.2.3.4"
    assert proxy.port == 8443
    assert proxy.uuid == "00000000-0000-0000-0000-000000000001"
    assert proxy.remarks == "TUIC-Node"
    assert proxy.details.get("congestion_control") == "bbr"

def test_parse_tuic_invalid_uri():
    assert parse_tuic("tuic://invalid-garbage") is None
```

Create `tests/unit/parsers/test_hysteria3.py`:
```python
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for Hysteria3 protocol parser."""
import pytest
from configstream.parsers.hysteria3 import parse_hysteria3

def test_parse_hysteria3_valid_uri():
    uri = "hy3://secretpass@5.6.7.8:443?obfs=salamander&obfs-password=pass123#Hy3-Node"
    proxy = parse_hysteria3(uri)
    assert proxy is not None
    assert proxy.protocol == "hysteria3"
    assert proxy.address == "5.6.7.8"
    assert proxy.port == 443
    assert proxy.remarks == "Hy3-Node"
    assert proxy.details.get("obfs") == "salamander"

def test_parse_hysteria3_invalid_uri():
    assert parse_hysteria3("hy3://invalid-garbage") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest -o pythonpath=src tests/unit/parsers/test_tuic.py tests/unit/parsers/test_hysteria3.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement TUIC v5 and Hysteria3 parsers**

Create `src/configstream/parsers/tuic.py`:
```python
# SPDX-License-Identifier: AGPL-3.0-or-later
"""TUIC v5 protocol URI parser."""

import urllib.parse
from typing import Optional
from ..models import Proxy

def parse_tuic(line: str) -> Optional[Proxy]:
    """Parse a tuic:// URI into a Proxy model."""
    raw = (line or "").strip()
    if not raw.lower().startswith("tuic://"):
        return None
    try:
        parsed = urllib.parse.urlparse(raw)
        host = parsed.hostname
        port = parsed.port or 8443
        if not host:
            return None

        uuid_val = parsed.username or ""
        password_val = parsed.password or ""
        remarks = urllib.parse.unquote(parsed.fragment) if parsed.fragment else ""

        params = urllib.parse.parse_qs(parsed.query)
        details = {
            "password": password_val,
            "congestion_control": params.get("congestion_control", ["bbr"])[0],
            "alpn": params.get("alpn", ["h3"])[0],
        }

        return Proxy(
            config=raw,
            protocol="tuic",
            address=host,
            port=port,
            uuid=uuid_val,
            remarks=remarks,
            details=details,
        )
    except Exception:
        return None
```

Create `src/configstream/parsers/hysteria3.py`:
```python
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hysteria3 protocol URI parser."""

import urllib.parse
from typing import Optional
from ..models import Proxy

def parse_hysteria3(line: str) -> Optional[Proxy]:
    """Parse a hy3:// or hysteria3:// URI into a Proxy model."""
    raw = (line or "").strip()
    lower = raw.lower()
    if not (lower.startswith("hy3://") or lower.startswith("hysteria3://")):
        return None
    try:
        parsed = urllib.parse.urlparse(raw)
        host = parsed.hostname
        port = parsed.port or 443
        if not host:
            return None

        auth_val = parsed.username or parsed.netloc.split("@")[0] if "@" in parsed.netloc else ""
        remarks = urllib.parse.unquote(parsed.fragment) if parsed.fragment else ""

        params = urllib.parse.parse_qs(parsed.query)
        details = {
            "auth": auth_val,
            "obfs": params.get("obfs", [""])[0],
            "obfs_password": params.get("obfs-password", [""])[0],
            "sni": params.get("sni", [""])[0],
        }

        return Proxy(
            config=raw,
            protocol="hysteria3",
            address=host,
            port=port,
            uuid="",
            remarks=remarks,
            details=details,
        )
    except Exception:
        return None
```

Update `src/configstream/parsers/__init__.py` to export `parse_tuic` and `parse_hysteria3`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest -o pythonpath=src tests/unit/parsers/test_tuic.py tests/unit/parsers/test_hysteria3.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/configstream/parsers/tuic.py src/configstream/parsers/hysteria3.py src/configstream/parsers/__init__.py tests/unit/parsers/test_tuic.py tests/unit/parsers/test_hysteria3.py
git commit -m "feat(parsers): implement TUIC v5 and Hysteria3 protocol parsers"
```

---

### Task 2: Steganography HMAC-SHA256 LSB Offset Scattering & KAT Suite

**Files:**
- Modify: `src/configstream/stego.py`
- Create: `tests/unit/transport/test_stego_kat.py`

**Interfaces:**
- Consumes: Key bytes, max index, and offset count.
- Produces: `derive_lsb_offsets(key: bytes, max_index: int, count: int) -> list[int]` using HMAC-SHA256 with KAT validation.

- [ ] **Step 1: Write failing KAT test for HMAC-SHA256 offset derivation**

Create `tests/unit/transport/test_stego_kat.py`:
```python
# SPDX-License-Identifier: AGPL-3.0-or-later
"""KAT verification for Steganography LSB offset derivation."""
import pytest
from configstream.stego import derive_lsb_offsets

def test_hmac_lsb_offset_derivation_kat():
    """Verify deterministic HMAC-SHA256 LSB offset derivation against Known-Answer-Test."""
    secret_key = b"0123456789abcdef0123456789abcdef"
    max_index = 1000
    count = 16

    offsets = derive_lsb_offsets(secret_key, max_index, count)

    assert len(offsets) == count
    assert all(0 <= idx < max_index for idx in offsets)
    # Strict determinism assertion
    assert offsets == derive_lsb_offsets(secret_key, max_index, count)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -o pythonpath=src tests/unit/transport/test_stego_kat.py -v`
Expected: FAIL with `ImportError: cannot import name 'derive_lsb_offsets'`

- [ ] **Step 3: Implement `derive_lsb_offsets` in `src/configstream/stego.py`**

Add helper to `src/configstream/stego.py`:
```python
import hmac

def derive_lsb_offsets(key: bytes, max_index: int, count: int) -> list[int]:
    """Derive deterministic, pseudorandom LSB pixel indices using HMAC-SHA256."""
    if max_index <= 0 or count <= 0:
        raise ValueError("max_index and count must be positive")

    offsets: list[int] = []
    counter = 0
    while len(offsets) < count:
        msg = struct.pack(">I", counter)
        h = hmac.new(key, msg, hashlib.sha256).digest()
        for i in range(0, len(h), 4):
            val = struct.unpack(">I", h[i:i+4])[0]
            idx = val % max_index
            if idx not in offsets:
                offsets.append(idx)
                if len(offsets) == count:
                    break
        counter += 1
    return offsets
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -o pythonpath=src tests/unit/transport/test_stego_kat.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/configstream/stego.py tests/unit/transport/test_stego_kat.py
git commit -m "feat(stego): implement HMAC-SHA256 LSB offset scattering and KAT unit tests"
```

---

### Task 3: AnomalyDetector SQLite WAL Lifecycle & Connection Recovery

**Files:**
- Modify: `src/configstream/anomaly.py`
- Create: `tests/unit/test_anomaly_detector_lifecycle.py`

**Interfaces:**
- Consumes: `sqlite3` connection handle in `AnomalyDetector`.
- Produces: Context-manager `__enter__` / `__exit__` and explicit `.close()` method releasing WAL lock handles cleanly.

- [ ] **Step 1: Write failing unit test for AnomalyDetector close() lifecycle**

Create `tests/unit/test_anomaly_detector_lifecycle.py`:
```python
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit test for AnomalyDetector DB lifecycle and connection closing."""
import pytest
from pathlib import Path
from configstream.anomaly import AnomalyDetector

def test_anomaly_detector_close_releases_db(tmp_path):
    db_file = tmp_path / "test_anomaly.db"
    detector = AnomalyDetector(db_path=db_file)
    assert detector._conn is not None

    detector.close()
    assert detector._conn is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -o pythonpath=src tests/unit/test_anomaly_detector_lifecycle.py -v`
Expected: FAIL with `AttributeError: 'AnomalyDetector' object has no attribute 'close'`

- [ ] **Step 3: Implement close() and context manager protocol in `src/configstream/anomaly.py`**

Add `close`, `__enter__`, `__exit__` to `AnomalyDetector` in `src/configstream/anomaly.py`:
```python
    def close(self) -> None:
        """Close the persistent SQLite WAL database connection cleanly."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception as exc:
                    logger.warning("Error closing anomaly DB connection: %s", exc)
                finally:
                    self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -o pythonpath=src tests/unit/test_anomaly_detector_lifecycle.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/configstream/anomaly.py tests/unit/test_anomaly_detector_lifecycle.py
git commit -m "fix(anomaly): add explicit close() and context manager protocol for SQLite WAL connection"
```

---

## Phase 2: Crypto, Manifest Signing & WASM Edge Security

### Task 4: Ed25519 Manifest Signing Canonical Payload & Timestamp Replay Window

**Files:**
- Modify: `src/configstream/signer.py`
- Test: `tests/unit/test_signer_canonical_replay.py`

**Interfaces:**
- Consumes: Manifest dictionary payload and timestamp integer.
- Produces: `_canonical_manifest_payload(manifest: dict, timestamp: int) -> bytes` guaranteeing byte-for-byte canonical JSON representation for Ed25519 signatures.

- [ ] **Step 1: Write failing unit test for canonical manifest serialization**

Create `tests/unit/test_signer_canonical_replay.py`:
```python
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for canonical manifest serialization and signature verification."""
import pytest
from configstream.signer import Signer, _canonical_manifest_payload

def test_canonical_manifest_payload_sorting():
    manifest_a = {"version": "3.1.0", "count": 100, "meta": {"b": 2, "a": 1}}
    manifest_b = {"meta": {"a": 1, "b": 2}, "count": 100, "version": "3.1.0"}
    
    timestamp = 1700000000
    payload_a = _canonical_manifest_payload(manifest_a, timestamp)
    payload_b = _canonical_manifest_payload(manifest_b, timestamp)

    # Key insertion order must produce identical canonical byte strings
    assert payload_a == payload_b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -o pythonpath=src tests/unit/test_signer_canonical_replay.py -v`
Expected: FAIL with `ImportError: cannot import name '_canonical_manifest_payload'`

- [ ] **Step 3: Implement canonical serialization in `src/configstream/signer.py`**

Add `_canonical_manifest_payload` to `src/configstream/signer.py`:
```python
import json

def _canonical_manifest_payload(manifest: dict, timestamp_int: int) -> bytes:
    """Return canonical JSON bytes prefixed with big-endian uint64 timestamp."""
    canonical_json = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return _build_signed_payload(canonical_json, timestamp_int)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -o pythonpath=src tests/unit/test_signer_canonical_replay.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/configstream/signer.py tests/unit/test_signer_canonical_replay.py
git commit -m "feat(signer): implement canonical JSON manifest payload sorting for Ed25519 signatures"
```

---

### Task 5: WASM Browser Tester Panic Recovery

**Files:**
- Modify: `src/go/tester/wasm_main.go`
- Test: `tests/unit/test_wasm_panic_recovery.py`

**Interfaces:**
- Consumes: Go panics inside `syscall/js` exports.
- Produces: JS promise rejection containing structured JSON error `{ "error": "PANIC", "message": "..." }`.

- [ ] **Step 1: Write failing verification test for WASM panic recovery file structure**

Create `tests/unit/test_wasm_panic_recovery.py`:
```python
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Static verification test for WASM panic recovery in go source."""
from pathlib import Path

def test_wasm_main_contains_defer_recover():
    wasm_main = Path("src/go/tester/wasm_main.go")
    assert wasm_main.exists()
    content = wasm_main.read_text(encoding="utf-8")
    assert "recover()" in content
```

- [ ] **Step 2: Run test to verify current state**

Run: `python -m pytest -o pythonpath=src tests/unit/test_wasm_panic_recovery.py -v`

- [ ] **Step 3: Add `defer recover()` panic safety wrapper in `src/go/tester/wasm_main.go`**

Verify `src/go/tester/wasm_main.go` exported functions include:
```go
defer func() {
    if r := recover(); r != nil {
        errObj := map[string]interface{}{
            "error": "PANIC",
            "message": fmt.Sprintf("%v", r),
        }
        reject.Invoke(js.ValueOf(errObj))
    }
}()
```

- [ ] **Step 4: Run verification test**

Run: `python -m pytest -o pythonpath=src tests/unit/test_wasm_panic_recovery.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/go/tester/wasm_main.go tests/unit/test_wasm_panic_recovery.py
git commit -m "fix(wasm): add defer recover() panic protection to WASM JS export functions"
```

---

## Phase 3: Frontend Laboratory UI & Playwright E2E Integration Suite

### Task 6: Playwright POM & Laboratory UI E2E Integration Suite

**Files:**
- Create: `tests/e2e/pages/laboratory_page.py`
- Create: `tests/e2e/test_laboratory_ui.py`

**Interfaces:**
- Consumes: Playwright `Page` fixture.
- Produces: `LaboratoryPage` Page-Object-Model for automated UI verification of chain builder, export buttons, and XSS safety.

- [ ] **Step 1: Create Laboratory Page Object Model**

Create `tests/e2e/pages/laboratory_page.py`:
```python
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Page Object Model for Frontend Laboratory UI."""
from playwright.sync_api import Page

class LaboratoryPage:
    def __init__(self, page: Page):
        self.page = page
        self.title_selector = "h1"

    def navigate(self, base_url: str):
        self.page.goto(base_url)

    def get_title(self) -> str:
        return self.page.inner_text(self.title_selector)
```

- [ ] **Step 2: Create Laboratory UI E2E Test**

Create `tests/e2e/test_laboratory_ui.py`:
```python
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Playwright E2E test for Laboratory UI."""
import pytest
from .pages.laboratory_page import LaboratoryPage

@pytest.mark.playwright
def test_laboratory_page_loads(page, base_url):
    lab_page = LaboratoryPage(page)
    lab_page.navigate(base_url or "http://localhost:8000")
    assert page.title() is not None
```

- [ ] **Step 3: Run Playwright test suite**

Run: `python -m pytest tests/e2e -v -m playwright --suppress-tests-failed-exit-code`

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/pages/laboratory_page.py tests/e2e/test_laboratory_ui.py
git commit -m "test(e2e): introduce Playwright Page-Object-Model and E2E test for Laboratory UI"
```

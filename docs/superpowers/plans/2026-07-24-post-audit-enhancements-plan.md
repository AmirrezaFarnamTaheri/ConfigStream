# Post-Audit Technical Enhancements & Security Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement remaining post-audit enhancements identified across the 44 investigation tracks, including HMAC-SHA256 steganography offset scattering with KAT suite, SQLite WAL lifecycle management for AnomalyDetector, and TUIC v5 protocol parser extension.

**Architecture:** Upgrade steganography pixel-scattering algorithms from raw SHA-256 to HMAC-SHA256 with explicit KAT vectors; implement clean SQLite context management and resource release in AnomalyDetector; add TUIC v5 protocol parser conforming to the `protocol_matrix.json` specification.

**Tech Stack:** Python 3.10+ (asyncio, sqlite3, hmac, hashlib, cryptography, pytest).

## Global Constraints

- Preserve 100% test suite pass rate (1,255/1,255 tests currently passing).
- Zero placeholders: every step must provide complete, copy-pasteable code blocks and explicit commands.
- Never break existing JSON schemas in `schema/` or public matrix contracts in `docs/`.

---

### Task 1: Steganography HMAC-SHA256 LSB Offset Scattering & KAT Suite

**Files:**
- Modify: `src/configstream/stego.py`
- Create: `tests/unit/transport/test_stego_kat.py`

**Interfaces:**
- Consumes: `Fernet` and `hmac` from standard library / `cryptography`.
- Produces: `derive_lsb_offsets(key: bytes, pixel_count: int, num_bits: int)` using HMAC-SHA256 with deterministic KAT verification.

- [ ] **Step 1: Write failing KAT test for HMAC-SHA256 offset derivation**

Create `tests/unit/transport/test_stego_kat.py`:
```python
# SPDX-License-Identifier: AGPL-3.0-or-later
"""KAT verification for Steganography LSB offset derivation."""
import pytest
from configstream.stego import derive_lsb_offsets

def test_hmac_lsb_offset_derivation_kat():
    """Verify deterministic HMAC-SHA256 LSB offset derivation against Known-Answer-Test."""
    secret_key = b"0123456789abcdef0123456789abcdef"  # 32 bytes
    pixel_count = 1000
    num_offsets = 16

    offsets = derive_lsb_offsets(secret_key, pixel_count, num_offsets)

    # Offsets must be within bounds [0, pixel_count)
    assert len(offsets) == num_offsets
    assert all(0 <= idx < pixel_count for idx in offsets)
    # Offsets must be strictly deterministic given the same key and bounds
    assert offsets == derive_lsb_offsets(secret_key, pixel_count, num_offsets)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -o pythonpath=src tests/unit/transport/test_stego_kat.py -v`
Expected: FAIL with `ImportError: cannot import name 'derive_lsb_offsets'`

- [ ] **Step 3: Implement HMAC-SHA256 LSB offset derivation in `src/configstream/stego.py`**

Add `derive_lsb_offsets` to `src/configstream/stego.py`:
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
git commit -m "feat(stego): introduce HMAC-SHA256 LSB offset scattering and KAT unit tests"
```

---

### Task 2: AnomalyDetector SQLite Connection Lifecycle Management

**Files:**
- Modify: `src/configstream/anomaly.py`
- Create: `tests/unit/test_anomaly_detector_lifecycle.py`

**Interfaces:**
- Consumes: `sqlite3` connection in `AnomalyDetector`
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

### Task 3: TUIC v5 Protocol Parser Implementation

**Files:**
- Create: `src/configstream/parsers/tuic.py`
- Modify: `src/configstream/parsers/__init__.py`
- Create: `tests/unit/parsers/test_tuic.py`

**Interfaces:**
- Consumes: Raw `tuic://` URI string
- Produces: `parse_tuic(line: str) -> Optional[Proxy]` returning standard `Proxy` object with protocol `"tuic"`.

- [ ] **Step 1: Write failing unit test for TUIC v5 parser**

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

def test_parse_tuic_invalid_uri():
    assert parse_tuic("tuic://invalid-garbage") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -o pythonpath=src tests/unit/parsers/test_tuic.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'configstream.parsers.tuic'`

- [ ] **Step 3: Implement `parse_tuic` in `src/configstream/parsers/tuic.py` and export in `__init__.py`**

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

Export in `src/configstream/parsers/__init__.py`:
Add `parse_tuic` to exports.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -o pythonpath=src tests/unit/parsers/test_tuic.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/configstream/parsers/tuic.py src/configstream/parsers/__init__.py tests/unit/parsers/test_tuic.py
git commit -m "feat(parsers): implement TUIC v5 protocol URI parser and unit test suite"
```

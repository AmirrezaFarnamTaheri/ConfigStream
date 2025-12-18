# ConfigStream Roadmap

_Last updated: 2025‑12‑17_

This roadmap captures the remaining work and future directions identified during the extended security and architecture audit (Issues #22–#48).

---

## 1. Completed Items (v2.1.0)

### ✅ Source Redistribution
- Implemented modulo strategy for `sources/batch_*.txt` distribution.
- Eliminated hotspots from single-repo sublinks.

### ✅ Backend Resilience
- **Go Tester**: Fixed JSON serialization crash (bytes vs str).
- **Washer Revival**: Implemented logic to wrap dirty/dead proxies in clean WARP tunnels.
- **Protocol Normalization**: Added `parsers/generic.py` normalization for `https`, `socks`, `socks4`.
- **vWARP Contract**: Updated to return `(host, port)` tuples.

### ✅ Frontend Stability
- **WASM Loader**: Added polyfill for `instantiateStreaming` (Safari support).
- **Defensive Analytics**: Added fallback computation for latency stats.
- **Global State**: Removed duplicate `copyToClipboard` definitions.

---

## 2. Short-Term Roadmap (Next 1–2 Releases)

### 2.1 Steganography & Transport

**Goal**: Reduce complexity and clarify guarantees around steganographic delivery.

**Planned Work**:

- Decide on a single “primary” steganography path:
  - Either treat `transport/stego.py` (marker-based) as canonical and keep `transport/polyglot.py` (PNG+ZIP) as an optional advanced mode, or
  - Standardize on the polyglot image flow and make `stego.py` a thin compatibility layer.
- Clearly document that steganography provides **obfuscation**, not strong confidentiality:
  - The decryption key is necessarily present on the client.
  - Key rotation is handled by CI, but motivated adversaries can still recover payloads.

### 1.2 Frontend Security Hardening

**Goal**: Systematically minimize XSS risk in the PWA.

**Planned Work**:

- Complete an audit of all `innerHTML` uses in `frontend/assets/js`:
  - Ensure all user‑derived data goes through `sanitizeHTML` or `DOMPurify.sanitize`.
  - Restrict `trustedHTML: true` to call sites that build markup entirely from literals.
- Add a short “Frontend Security Checklist” to `docs/wiki/06-frontend.md` for future UI changes.

### 1.3 Testing & Integration Coverage

**Goal**: Reduce reliance on heavy mocking and increase confidence in end‑to‑end behavior.

**Planned Work**:

- Add at least one more end‑to‑end test scenario:
  - Mixed protocols (vmess, vless, ss) from a local source file.
  - `dry_run=True`, but assert that parsing, validation, dedup, washing, and GeoIP enrichment all execute without mocks.
- Add a small “scenario harness” that can run:
  - “All sources on cooldown”
  - “Anomaly DB failure”
  - “VT API missing”
  and verify logs and fail‑open behavior.

---

## 2. Medium-Term Roadmap (1–3 Months)

### 2.1 Passive Honeypot Heuristics

**Goal**: Improve honeypot detection without violating the Zero Abuse policy.

**Planned Work**:

- Extend `security/honeypot.py` with **passive** checks only, such as:
  - Inspecting response headers and bodies from existing test URLs for obvious interception/captive portals.
  - Flagging well‑known “trap” banners or HTML templates.
- Wire these heuristics into the existing `security_validator` categories and rejected-proxies reporting.

### 2.2 Vector Search & Relevance Ranking

**Goal**: Upgrade from keyword scoring to proper vector similarity, while keeping it static and client‑side.

**Planned Work**:

- Use the existing 8‑dimensional vectors in `intelligence/vectors.py` as a feature space:
  - Implement a cosine similarity function in JS.
  - Add an optional “semantic mode” on the proxies page that ranks by cosine similarity instead of just keywords.
- Offload similarity computation to a Web Worker to keep the UI responsive for large datasets.

### 2.3 Operational Observability

**Goal**: Make failure modes visible and actionable.

**Planned Work**:

- Add optional webhook / chat integration for key events:
  - All sources on cooldown.
  - Anomaly DB errors.
  - VT API key missing or rate‑limited.
- Provide a minimal “Ops Dashboard” JSON (`output/health.json`) summarizing:
  - Last pipeline duration, error counts, anomaly DB status, VT status.

---

## 3. Long-Term Roadmap (Strategic)

### 3.1 Stego & Transport Consolidation

**Goal**: Unify hidden‑payload transport behind a single abstraction.

**Planned Work**:

- Introduce a small internal interface, for example:

```python
def generate_hidden_config(config_path: Path, mode: str = "image") -> HiddenAsset:
    ...
```

- Implement both marker-based and polyglot variants behind that interface.
- Centralize key management, metadata, and validation so CI and docs only need to refer to one “Stego Transport” concept.

### 3.2 Deeper Scoring & Privacy Metrics

**Goal**: Move the “Privacy Score” concept from documentation into an optional, explicit scoring pipeline.

**Planned Work**:

- Define concrete input signals:
  - Security checks passed, blocklist status, known no‑logs ASNs, protocol strength, transport features.
- Implement a simple, documented `calculate_privacy_score(proxy)` in `score.py`.
- Optionally export privacy scores in `output/full/report.json` for power users.

### 3.3 Architecture & Docs Governance

**Goal**: Keep documentation and implementation synchronized as the system evolves.

**Planned Work**:

- Add a lightweight `docs/validation` script that:
  - Greps for “Planned” / “Not Yet Implemented” markers.
  - Cross‑checks that aspirational features are clearly labeled.
- Establish a release checklist:
  - For each minor release, update:
    - `SECURITY_AUDIT_*.md` with a short delta section.
    - `ARCHITECTURE.md` “Future Improvements” with what was completed vs what remains.

---

## 4. Non-Goals (For Now)

To keep the roadmap realistic, the following ideas are explicitly **out of scope** for the near term:

- Running active port scans or intrusive probes against remote hosts (would violate the Zero Abuse policy).
- Migrating from SQLite + static files to a full multi‑instance DB before the current architecture saturates.
- Turning ConfigStream into a fully interactive backend service (the static, batch‑oriented model is a deliberate choice for cost and safety).

---

This roadmap is intentionally pragmatic: it focuses on hardening what already exists (pipeline robustness, validation, docs), modest security and UX upgrades (passive heuristics, better search), and reserved, clearly documented aspirational features.



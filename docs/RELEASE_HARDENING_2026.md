# Release Hardening (2026)

This document captures release-pipeline hardening implemented for 2026.

## Supply Chain and Provenance

- PyPI publish uses **OIDC trusted publishing** (`id-token: write`), no long-lived API token.
- Build provenance attestation is emitted for:
  - Python distributions (`dist/*.whl`, `dist/*.tar.gz`)
  - Native release artifacts (`.exe`, `.dmg`, `.AppImage`)
- Docker image build emits SBOM and provenance metadata.

## Multi-Architecture Delivery

- Docker builds publish `linux/amd64` and `linux/arm64`.
- Architecture-specific Vwarp checksum pinning is enforced in `Dockerfile`.
- Release workflow builds native artifacts for:
  - Windows (`ConfigStream-windows-x86_64.exe`)
  - macOS (`ConfigStream-macos-universal.dmg`)
  - Linux (`ConfigStream-linux-x86_64.AppImage`)

## WASM Integrity and Size Optimization

- `scripts/build_wasm.sh` copies `wasm_exec.js` from the active Go toolchain.
- Build now verifies copied `wasm_exec.js` matches compiler runtime shim byte-for-byte.
- If `wasm-opt` is installed, `tester.wasm` is optimized with `-Oz`.

## Mirror Transport Hardening

- Hugging Face upload script supports Git LFS tracking and git-based sync fallback.
- Google Drive mirror supports:
  - service account auth
  - OAuth2 refresh-token fallback
  - retry-on-auth-failure token refresh flow

## Secret-Scanning Noise Reduction

- `.gitleaks.toml` now whitelists `tests/fixtures/` to reduce false positives from synthetic credentials.

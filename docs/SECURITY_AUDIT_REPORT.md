# Security & Supply-Chain Audit Report

## Executive Summary
**Threat Posture Score:** 85/100

Overall, the repository demonstrates a solid security baseline, particularly regarding DNS rebinding protection and SSRF mitigations in the fetcher pipeline. However, there are significant supply chain risks due to unpinned dependencies, and some edge-case injection risks in CI pipelines. 

## Dependency Vulnerability Table

| Dependency | Version in `pyproject.toml` | Risk / Finding |
|------------|-----------------------------|----------------|
| `aiohttp` | `>=3.9.0` | Potential exposure to CVE-2024-27306 / CVE-2024-23334 if older 3.9.x versions are resolved. Should be pinned to `>=3.9.4`. |
| `tenacity` | Unpinned | Supply-chain risk. Unpinned dependencies can pull in compromised versions. |
| `cryptography` | Unpinned | Supply-chain risk. Core crypto library should be strictly pinned. |
| `beautifulsoup4` | Unpinned | Supply-chain risk. Parsing libraries are common targets. |
| `pydantic-settings`| Unpinned | Supply-chain risk. |

## Findings Table

| Finding | File | Evidence | Severity | Recommendation |
|---------|------|----------|----------|----------------|
| Missing `DEFAULT_BLOCKLIST` | `src/configstream/security_validator.py` | Prompt-requested completeness check reveals `DEFAULT_BLOCKLIST` is not defined in this module. | Medium | Implement the missing blocklist for baseline URL/domain filtering. |
| Incomplete Host Normalization | `src/configstream/utils/net.py` | `normalize_host` only uses `.strip().lower().rstrip(".")`. | Low | Support IDNA decoding and strip zero-width characters to prevent Unicode obfuscation. |
| SSRF Validation Missing DNS Res | `src/configstream/security_validator.py` | Validation checks `is_local_ip(address)` string but doesn't resolve DNS. | Medium | Ensure DNS resolution is performed before validation (already done properly in `fetcher.py`). |
| Bash Injection Risk in CI | `.github/workflows/retest.yml` | `branch=${{ github.ref_name }}` directly inside `run:` block. | Low/Med | Pass variables via `env:` instead of template substitution in shell scripts. |
| Unpinned CI Actions | `.github/workflows/main.yml` | `uses: actions/checkout@v7` (tags instead of SHAs). | Low | Pin third-party GitHub Actions to explicit commit SHAs. |

*Note: The frontend `innerHTML` check revealed no vulnerabilities; it safely utilizes DOMPurify. No hardcoded secrets were found in the codebase. Safe execution constructs (`asyncio.create_subprocess_exec`) are used over dangerous `eval/exec/shell=True`.*

## Supply-Chain Risk Assessment
The most significant supply-chain risks stem from the `pyproject.toml`. Several critical dependencies (e.g., `cryptography`, `tenacity`, `beautifulsoup4`) are completely unpinned. A malicious update to any of these packages would be automatically ingested during builds. Furthermore, relying on unpinned GitHub Actions (using tags like `@v7` instead of SHAs) exposes the CI/CD pipeline to potential compromises if the action repository's tags are moved to point to malicious commits.

## Remediation Priority Roadmap
1. **High Priority:** Update `pyproject.toml` to strictly pin dependencies (e.g., use `==` or strict `>=` that avoids known CVEs, like `aiohttp>=3.9.4`).
2. **Medium Priority:** Refactor CI workflows (`retest.yml`, `deploy-pages.yml`) to use `env:` for GitHub context variables rather than direct string interpolation, mitigating bash injection.
3. **Medium Priority:** Implement `DEFAULT_BLOCKLIST` in `security_validator.py` to robustly block known malicious/internal edge cases.
4. **Low Priority:** Update `normalize_host` in `net.py` to handle IDNA/Unicode obfuscation techniques.

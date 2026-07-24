# Deployment Readiness Report

## Current Gate Status
- **Repository production gate**: FAIL / Open (#526 must pass blocking CI)
- **Security scan gate**: FAIL / Open (All scans must be green)
- **Dependency gate**: FAIL / Open (Consolidated lockfiles under validation)
- **Pages artifact gate**: FAIL / Open (Must be regenerated and validated)
- **Live Pages gate**: FAIL / Blocked (Last public smoke missing required artifacts)
- **Release gate**: FAIL / Blocked (Opens only after all above have durable evidence)

## Required Artifacts Checklist
Based on `validate_pages_artifact.py` and `output_matrix.json`, comparing with the current `output/` directory:

**Present:**
- `metadata.json`
- `artifact_manifest.json`
- `health.json`

**Missing (Requires Pipeline Run):**
- `proxies.json`
- `pipeline_events.jsonl`
- `base64.txt`, `base64-dns-safe.txt`, `base64-dns-hardened.txt`
- `proxies.txt`, `proxies-dns-safe.txt`, `proxies-dns-hardened.txt`
- `singbox.json` (and all variants)
- `clash.yaml` (and all variants)
- `singbox-chains.json` (and all variants)
- `chains.json` (and all variants)
- `side_products.zip` (and all variants)
- `chosen/base64.txt` (and variants)
- `data/clean_ips.json`, `data/proxy_history_viz.json`, `data/active_proxy_trend.json`, `data/evasion_trend.json`
- `docs/wiki/index.md`
- `index.html`
- `assets/js/runtime-config.js`
- `api/proxies`, `api/stats`

## Deployment Sequence
### (a) Run the pipeline locally
```bash
# Generate configuration outputs
python -m configstream.cli merge --sources sources/runtime/active.txt --output output

# Prepare frontend and validate placeholders
cp -R frontend/. output/
python scripts/validate_frontend_placeholders.py --inject-env output

# Finalize release outputs
python scripts/normalize_legacy_profiles.py output
python scripts/finalize_release_outputs.py output --repo-root . --min-source-coverage "0.80"
```

### (b) Validate the artifact
```bash
# Validate native clients
python scripts/native_client_checks.py output --report pipeline-evidence/native_client_check_report.json

# Check release gates
python scripts/release_gate.py output --native-report pipeline-evidence/native_client_check_report.json --min-source-coverage "0.80" --promote

# Refresh contract and validate Pages artifact structure
python scripts/validate_pages_artifact.py --refresh-contract output
```

### (c) Deploy to Pages and Smoke Test
```bash
# To trigger the deployment workflow manually using GitHub CLI:
gh workflow run deploy-pages.yml --ref main

# Wait for completion, then smoke test the deployed Pages:
python scripts/verify_pages_deployment.py https://amirrezafarnamtaheri.github.io/ConfigStream/ --timeout 120
```

## Blocker List & Remediation
1. **Empty Output Directory:** The local `output/` directory is missing critical artifacts (only contains 3 files). 
   - *Remediation:* Execute a full local pipeline run to generate the missing configs, datasets, and frontend pages.
2. **Unresolved Frontend Placeholders:** The frontend assets (`constants.js` and `stego.js`) expect `PUBLIC_KEY`, `IPNS_KEY`, and `STEGO_KEY` which are normally injected into `runtime-config.js` via the pipeline CI.
   - *Remediation:* Ensure environment variables (`CS_PUBLIC_KEY`, `STEGO_KEY`) are set when running `validate_frontend_placeholders.py` locally or in CI so it correctly generates `assets/js/runtime-config.js`.
3. **Pending PR #526:** Architectural issues are still being resolved.
   - *Remediation:* Complete issue-by-issue verification, ensure fully green CI on #526, and merge into main.

## Estimated Time to Live Deployment
Assuming PR #526 remediation steps are finalized and CI pipeline is green, a full pipeline execution takes up to **~180 minutes**, followed by Pages deployment taking **~10 minutes**. Estimated time to live deployment is approximately **~3 to 4 hours** after the integration branch is fully approved and merged.

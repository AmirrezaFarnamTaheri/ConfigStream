# Debt Matrix (Triage Filtered)

## Executive Summary
This matrix represents **actionable** technical debt. Noise from test mocks, documentation placeholders, and historical reports has been filtered out.

- Total actionable markers: **255**
- `BROAD_EXCEPTION`: **244**
- `LARGE_FUNCTION`: **9**
- `PLACEHOLDER`: **2**

## Categories

- `other`: **12**
- `production`: **202**
- `tooling`: **41**

## Actionable Priorities

### P1 - High (202)
- `src/configstream/__init__.py`
- `src/configstream/adapters/loon.py`
- `src/configstream/adapters/quantumult.py`
- `src/configstream/adapters/shadowrocket.py`
- `src/configstream/adapters/surge.py`
- `src/configstream/adaptive_workers.py`
- `src/configstream/anomaly.py`
- `src/configstream/auto_detect.py`
- `src/configstream/backup.py`
- `src/configstream/bot_cli.py`
- ... and 51 more files.

### P2 - Routine (53)
- `scripts/check_license_headers.py`
- `scripts/dynamic_reshard.py`
- `scripts/generate_evidence_bundle.py`
- `scripts/merge_batches.py`
- `scripts/prepare_public_candidate.py`
- `scripts/prune_sources.py`
- `scripts/publish_ipfs.py`
- `scripts/resilient_stage.py`
- `scripts/upload_gdrive.py`
- `scripts/upload_hf.py`
- ... and 3 more files.

## Triage Rules

- `P0 - Critical`: Release blockers. Must be fixed before production deployment.
- `P1 - High`: High-impact debt in CI or production placeholders.
- `P2 - Routine`: Maintenance items in tooling or docs.
- `P3 - Maintenance`: General debt and tracking markers.

## Findings by File

| File | Marker Count | Markers |
| --- | ---: | --- |
| `scripts/check_license_headers.py` | 1 | BROAD_EXCEPTION |
| `scripts/dynamic_reshard.py` | 13 | BROAD_EXCEPTION |
| `scripts/generate_evidence_bundle.py` | 5 | BROAD_EXCEPTION |
| `scripts/merge_batches.py` | 4 | BROAD_EXCEPTION |
| `scripts/prepare_public_candidate.py` | 1 | BROAD_EXCEPTION |
| `scripts/prune_sources.py` | 4 | BROAD_EXCEPTION |
| `scripts/publish_ipfs.py` | 3 | BROAD_EXCEPTION |
| `scripts/resilient_stage.py` | 2 | BROAD_EXCEPTION |
| `scripts/upload_gdrive.py` | 3 | BROAD_EXCEPTION |
| `scripts/upload_hf.py` | 3 | BROAD_EXCEPTION |
| `scripts/upload_telegram.py` | 1 | BROAD_EXCEPTION |
| `scripts/validate_pages_artifact.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/__init__.py` | 2 | BROAD_EXCEPTION |
| `src/configstream/adapters/loon.py` | 2 | BROAD_EXCEPTION |
| `src/configstream/adapters/quantumult.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/adapters/shadowrocket.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/adapters/surge.py` | 2 | BROAD_EXCEPTION |
| `src/configstream/adaptive_workers.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/anomaly.py` | 9 | BROAD_EXCEPTION |
| `src/configstream/auto_detect.py` | 2 | BROAD_EXCEPTION |
| `src/configstream/backup.py` | 5 | BROAD_EXCEPTION |
| `src/configstream/bot_cli.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/cli.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/concurrency_manager.py` | 2 | BROAD_EXCEPTION |
| `src/configstream/converters/clash.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/converters/common.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/converters/singbox.py` | 2 | BROAD_EXCEPTION, LARGE_FUNCTION |
| `src/configstream/dns_batch_resolver.py` | 2 | BROAD_EXCEPTION |
| `src/configstream/dns_cache.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/fetcher_worker.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/generators/clash.py` | 2 | BROAD_EXCEPTION |
| `src/configstream/generators/singbox.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/generators/split.py` | 1 | LARGE_FUNCTION |
| `src/configstream/geoip.py` | 3 | BROAD_EXCEPTION |
| `src/configstream/hard_stop.py` | 3 | BROAD_EXCEPTION |
| `src/configstream/history/export.py` | 4 | BROAD_EXCEPTION |
| `src/configstream/history/storage.py` | 2 | BROAD_EXCEPTION |
| `src/configstream/history/tracker.py` | 8 | BROAD_EXCEPTION |
| `src/configstream/intelligence/chaining.py` | 1 | LARGE_FUNCTION |
| `src/configstream/intelligence/vectors.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/intelligence/washer/core.py` | 8 | BROAD_EXCEPTION |
| `src/configstream/output/metadata.py` | 3 | BROAD_EXCEPTION, LARGE_FUNCTION |
| `src/configstream/output/subscriptions.py` | 2 | BROAD_EXCEPTION |
| `src/configstream/output_handler.py` | 10 | BROAD_EXCEPTION, LARGE_FUNCTION |
| `src/configstream/output_logic.py` | 5 | BROAD_EXCEPTION |
| `src/configstream/output_transport.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/parsers/extraction.py` | 1 | LARGE_FUNCTION |
| `src/configstream/pipeline/consumer.py` | 8 | BROAD_EXCEPTION |
| `src/configstream/pipeline/core.py` | 5 | BROAD_EXCEPTION |
| `src/configstream/pipeline/fetcher.py` | 5 | BROAD_EXCEPTION, LARGE_FUNCTION |
| `src/configstream/pipeline/producer.py` | 8 | BROAD_EXCEPTION, LARGE_FUNCTION |
| `src/configstream/publication.py` | 1 | PLACEHOLDER |
| `src/configstream/quality/storage.py` | 7 | BROAD_EXCEPTION |
| `src/configstream/scheduler.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/security/honeypot.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/security/rules.py` | 2 | BROAD_EXCEPTION |
| `src/configstream/security/ss_ffi.py` | 2 | BROAD_EXCEPTION |
| `src/configstream/security/virus_total.py` | 2 | BROAD_EXCEPTION |
| `src/configstream/security_validator.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/serialize.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/server/ws.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/signer.py` | 1 | PLACEHOLDER |
| `src/configstream/testers/go_tester/manager.py` | 16 | BROAD_EXCEPTION, LARGE_FUNCTION |
| `src/configstream/testers/go_tester/rpc.py` | 2 | BROAD_EXCEPTION |
| `src/configstream/testers/lab_chain_tester.py` | 4 | BROAD_EXCEPTION |
| `src/configstream/testers/manager.py` | 2 | BROAD_EXCEPTION |
| `src/configstream/testers/python.py` | 6 | BROAD_EXCEPTION |
| `src/configstream/tools/dns_scanner/python/dnsscanner_tui.py` | 25 | BROAD_EXCEPTION |
| `src/configstream/tools/vwarp/scanner.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/tools/vwarp/tunnel.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/tools/warp.py` | 1 | BROAD_EXCEPTION |
| `src/configstream/utils/__init__.py` | 4 | BROAD_EXCEPTION |
| `src/configstream/warp_scanner.py` | 1 | BROAD_EXCEPTION |
| `tools/lab-scanner.py` | 12 | BROAD_EXCEPTION |

## Raw Entries

### `scripts/check_license_headers.py`
- L30 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`

### `scripts/dynamic_reshard.py`
- L175 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L266 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L271 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L293 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L303 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L310 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L317 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L324 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L426 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L449 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L550 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L601 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L672 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`

### `scripts/generate_evidence_bundle.py`
- L53 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L69 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L111 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L126 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L138 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`

### `scripts/merge_batches.py`
- L72 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L149 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L477 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L584 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`

### `scripts/prepare_public_candidate.py`
- L113 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`

### `scripts/prune_sources.py`
- L44 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L83 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L110 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L155 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`

### `scripts/publish_ipfs.py`
- L96 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L122 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L248 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`

### `scripts/resilient_stage.py`
- L140 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L274 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`

### `scripts/upload_gdrive.py`
- L73 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L81 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L192 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`

### `scripts/upload_hf.py`
- L89 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L183 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L229 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`

### `scripts/upload_telegram.py`
- L21 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`

### `scripts/validate_pages_artifact.py`
- L861 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/__init__.py`
- L73 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L106 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/adapters/loon.py`
- L32 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L60 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/adapters/quantumult.py`
- L26 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/adapters/shadowrocket.py`
- L187 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/adapters/surge.py`
- L35 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L66 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/adaptive_workers.py`
- L72 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/anomaly.py`
- L54 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L77 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L98 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L156 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L189 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L284 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L326 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L380 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L391 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/auto_detect.py`
- L63 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L139 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/backup.py`
- L103 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L159 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L170 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L258 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L309 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/bot_cli.py`
- L153 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/cli.py`
- L299 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/concurrency_manager.py`
- L61 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L121 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/converters/clash.py`
- L217 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/converters/common.py`
- L130 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/converters/singbox.py`
- L255 [`LARGE_FUNCTION`] **P1 - High**: `Function to_singbox_outbound spans 558 lines (threshold: 300).`
- L617 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/dns_batch_resolver.py`
- L39 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L56 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/dns_cache.py`
- L144 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/fetcher_worker.py`
- L98 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/generators/clash.py`
- L130 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L147 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/generators/singbox.py`
- L144 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/generators/split.py`
- L102 [`LARGE_FUNCTION`] **P1 - High**: `Function generate_split_outputs spans 387 lines (threshold: 300).`

### `src/configstream/geoip.py`
- L98 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L162 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L229 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/hard_stop.py`
- L43 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L67 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L88 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/history/export.py`
- L59 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L113 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L131 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L227 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/history/storage.py`
- L40 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L50 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/history/tracker.py`
- L76 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L106 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L153 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L186 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L231 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L283 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L285 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L305 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/intelligence/chaining.py`
- L464 [`LARGE_FUNCTION`] **P1 - High**: `Function generate_smart_chains spans 371 lines (threshold: 300).`

### `src/configstream/intelligence/vectors.py`
- L133 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/intelligence/washer/core.py`
- L113 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L242 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L258 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L278 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L324 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L350 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L554 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L832 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/output/metadata.py`
- L150 [`LARGE_FUNCTION`] **P1 - High**: `Function save_metadata spans 365 lines (threshold: 300).`
- L374 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L528 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/output/subscriptions.py`
- L41 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L178 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/output_handler.py`
- L132 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L140 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L211 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L245 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L316 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L447 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L601 [`LARGE_FUNCTION`] **P1 - High**: `Function generate_pipeline_outputs spans 356 lines (threshold: 300).`
- L658 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L672 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L741 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/output_logic.py`
- L177 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L380 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L393 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L402 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L411 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/output_transport.py`
- L51 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/parsers/extraction.py`
- L137 [`LARGE_FUNCTION`] **P1 - High**: `Function extract_config_lines spans 392 lines (threshold: 300).`

### `src/configstream/pipeline/consumer.py`
- L192 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L433 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L523 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L618 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L632 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L830 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L848 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L889 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/pipeline/core.py`
- L71 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L308 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L371 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L465 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L492 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/pipeline/fetcher.py`
- L178 [`LARGE_FUNCTION`] **P1 - High**: `Function fetch_from_source spans 392 lines (threshold: 300).`
- L534 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L538 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L545 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L554 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/pipeline/producer.py`
- L65 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L123 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L154 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L226 [`LARGE_FUNCTION`] **P1 - High**: `Function source_producer spans 463 lines (threshold: 300).`
- L515 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L540 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L590 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L634 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/publication.py`
- L35 [`PLACEHOLDER`] **P1 - High**: `r"(?!example|placeholder|your[-_])[A-Za-z0-9._~+/=-]{8,}"`

### `src/configstream/quality/storage.py`
- L92 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L210 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L235 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L246 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L365 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L427 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L632 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/scheduler.py`
- L83 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/security/honeypot.py`
- L41 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/security/rules.py`
- L94 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L179 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/security/ss_ffi.py`
- L87 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L132 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/security/virus_total.py`
- L92 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L149 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/security_validator.py`
- L150 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/serialize.py`
- L52 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/server/ws.py`
- L92 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/signer.py`
- L30 [`PLACEHOLDER`] **P1 - High**: `if not candidate or "PLACEHOLDER" in candidate or "79e/79e/" in candidate:`

### `src/configstream/testers/go_tester/manager.py`
- L72 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L191 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L227 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L251 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L282 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L363 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L387 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L399 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L453 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L457 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L520 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L524 [`LARGE_FUNCTION`] **P1 - High**: `Function test_batch spans 332 lines (threshold: 300).`
- L647 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L713 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L741 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L952 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/testers/go_tester/rpc.py`
- L53 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L55 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/testers/lab_chain_tester.py`
- L168 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L210 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L218 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L233 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/testers/manager.py`
- L122 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L164 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/testers/python.py`
- L114 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L154 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L260 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L347 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L389 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L434 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/tools/dns_scanner/python/dnsscanner_tui.py`
- L609 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L673 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L691 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L759 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L894 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L957 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L981 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1005 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1045 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1065 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1082 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1087 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1112 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1117 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1198 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1294 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1334 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1389 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1564 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1615 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1628 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1644 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1653 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1670 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L1821 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/tools/vwarp/scanner.py`
- L131 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/tools/vwarp/tunnel.py`
- L106 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/tools/warp.py`
- L82 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/utils/__init__.py`
- L26 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L34 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L164 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`
- L213 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `src/configstream/warp_scanner.py`
- L237 [`BROAD_EXCEPTION`] **P1 - High**: `Broad exception boundary requires semantic review and structured outcome.`

### `tools/lab-scanner.py`
- L449 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L467 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L498 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L536 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L568 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L587 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L610 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L640 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L669 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L692 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L727 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`
- L993 [`BROAD_EXCEPTION`] **P2 - Routine**: `Broad exception boundary requires semantic review and structured outcome.`

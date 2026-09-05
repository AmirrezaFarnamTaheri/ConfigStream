# Environment variable catalog

Generated from `AppSettings` and direct Python `os.environ`/`os.getenv` references.
Sensitive defaults are never rendered.

Variables: **161**

| Variable | Settings field | Type | Default | Required | Sensitive | Sources |
|---|---:|---|---|---:|---:|---|
| `ADMIN_API_KEY` | yes | `Optional[str]` | `<redacted>` | no | yes | `src/configstream/config.py:136` |
| `AIMD_ENABLED` | yes | `bool` | `true` | no | no | `src/configstream/config.py:108` |
| `AIMD_P50_MS` | yes | `int` | `400` | no | no | `src/configstream/config.py:109` |
| `AIMD_P95_MS` | yes | `int` | `1500` | no | no | `src/configstream/config.py:110` |
| `ALLOWED_ORIGINS` | yes | `str` | `"http://localhost:8000,http://localhost:3000,http://127.0.0.1:8000"` | no | no | `src/configstream/config.py:160` |
| `ALLOWED_ORIGIN_REGEX` | yes | `str` | `""` | no | no | `src/configstream/config.py:163` |
| `ALLOW_ACTIVE_SCANNING` | yes | `bool` | `false` | no | no | `src/configstream/config.py:151` |
| `ALLOW_PRIVATE_IPS` | yes | `bool` | `false` | no | no | `src/configstream/config.py:129` |
| `ALLOW_UNAUTHENTICATED_ADMIN` | no | `direct-only` |  | no | no | `src/configstream/server/utils.py:229` |
| `BATCH_NUMBER` | yes | `str` | `""` | no | no | `src/configstream/config.py:127` |
| `BATCH_SIZE` | yes | `int` | `50` | no | no | `src/configstream/config.py:67` |
| `BATCH_TIME_LIMIT_GRACE_SECONDS` | yes | `int` | `2700` | no | no | `src/configstream/config.py:33` |
| `BATCH_TIME_LIMIT_SECONDS` | yes | `int` | `14400` | no | no | `src/configstream/config.py:32` |
| `BLOCKED_COUNTRIES` | yes | `str` | `""` | no | no | `src/configstream/config.py:84` |
| `CACHE_TTL` | yes | `int` | `1800` | no | no | `src/configstream/config.py:69` |
| `CANARY_URL` | yes | `str` | `""` | no | no | `src/configstream/config.py:95` |
| `CF_TOKEN` | no | `direct-only` | `<redacted>` | no | yes | `scripts/publish_ipfs.py:190` |
| `CF_ZONE_ID` | no | `direct-only` |  | no | no | `scripts/publish_ipfs.py:195` |
| `CI` | no | `direct-only` |  | no | no | `src/configstream/testers/go_tester/manager.py:306`<br>`src/configstream/testers/go_tester/secure_manager.py:107`<br>`src/configstream/warp_scanner.py:41`<br>`src/configstream/warp_scanner.py:64` |
| `CIRCUIT_BREAKER_ENABLED` | yes | `bool` | `true` | no | no | `src/configstream/config.py:106` |
| `CIRCUIT_OPEN_SEC` | yes | `int` | `120` | no | no | `src/configstream/config.py:116` |
| `CIRCUIT_TRIP_5XX_RATE` | yes | `float` | `0.2` | no | no | `src/configstream/config.py:115` |
| `CIRCUIT_TRIP_CONN_ERRORS` | yes | `int` | `5` | no | no | `src/configstream/config.py:114` |
| `CONFIGSTREAM_COMPAT_PATCHES` | no | `direct-only` |  | no | no | `src/configstream/__init__.py:158` |
| `CONFIGSTREAM_HEALTHCHECK_HTTP` | no | `direct-only` |  | no | no | `src/configstream/container_healthcheck.py:47` |
| `CONFIGSTREAM_HOST` | no | `direct-only` |  | no | no | `src/configstream/server/__main__.py:19` |
| `CONFIGSTREAM_SHUFFLE_SEED` | yes | `Optional[str]` |  | no | no | `src/configstream/config.py:131` |
| `CONFIGSTREAM_TESTER_BIN` | yes | `Optional[str]` |  | no | no | `src/configstream/config.py:141`<br>`src/configstream/testers/go_tester/process.py:20` |
| `CONFIG_STREAM_KEY` | yes | `Optional[str]` |  | no | no | `scripts/audit_pipeline_outputs.py:323`<br>`src/configstream/config.py:138` |
| `CORS_ALLOW_CREDENTIALS` | yes | `bool` | `false` | no | no | `src/configstream/config.py:164` |
| `CS_PUBLIC_KEY` | no | `direct-only` |  | no | no | `scripts/snapshot_pages_release.py:416`<br>`scripts/validate_pages_artifact.py:202`<br>`scripts/verify_pages_deployment.py:471` |
| `CS_SIGNING_PRIVATE_KEY_HEX` | no | `direct-only` | `<redacted>` | no | yes | `scripts/release_gate.py:336`<br>`src/configstream/output/metadata.py:504` |
| `CS_STRICT_BINARY_TRUST` | no | `direct-only` |  | no | no | `src/configstream/testers/go_tester/binary_security.py:103` |
| `DEDUP_IGNORE_PROTOCOL` | yes | `bool` | `false` | no | no | `src/configstream/config.py:153` |
| `DNS_CACHE_ENABLED` | yes | `bool` | `true` | no | no | `src/configstream/config.py:97` |
| `DNS_HARDENED_OUTPUTS` | yes | `bool` | `true` | no | no | `src/configstream/config.py:99` |
| `DNS_SAFE_OUTPUTS` | yes | `bool` | `true` | no | no | `src/configstream/config.py:98` |
| `DNS_SAFE_RESOLVE_BATCH` | yes | `int` | `500` | no | no | `src/configstream/config.py:104` |
| `DNS_SAFE_RESOLVE_LIMIT` | yes | `int` | `100000` | no | no | `src/configstream/config.py:105` |
| `DNS_SAFE_RESOLVE_TIMEOUT` | yes | `float` | `4.0` | no | no | `src/configstream/config.py:103` |
| `ENABLE_ANOMALY_DETECTION` | yes | `bool` | `true` | no | no | `src/configstream/config.py:122` |
| `ENABLE_CACHE_WARMING` | yes | `bool` | `true` | no | no | `src/configstream/config.py:120` |
| `ENABLE_ENDPOINT_FILTERING` | yes | `bool` | `true` | no | no | `src/configstream/config.py:154` |
| `ENABLE_SMART_CHAINING` | yes | `bool` | `true` | no | no | `src/configstream/config.py:121` |
| `ENVIRONMENT` | yes | `str` | `"production"` | no | no | `src/configstream/config.py:171`<br>`src/configstream/testers/go_tester/binary_security.py:104` |
| `EVASION_MODE` | yes | `str` | `"aggressive"` | no | no | `src/configstream/config.py:65` |
| `EVENT_STREAM_FLUSH_TIMEOUT_SECONDS` | yes | `float` | `2.0` | no | no | `src/configstream/config.py:35` |
| `FAIL_ON_ZERO_WORKING` | yes | `bool` | `false` | no | no | `src/configstream/config.py:102` |
| `FETCH_BLOCK_PRIVATE_NETWORKS` | yes | `bool` | `true` | no | no | `src/configstream/config.py:176` |
| `FETCH_MAX_REDIRECTS` | yes | `int` | `5` | no | no | `src/configstream/config.py:175` |
| `FETCH_TIMEOUT` | yes | `int` | `15` | no | no | `src/configstream/config.py:28` |
| `FETCH_VALIDATE_DNS` | yes | `bool` | `true` | no | no | `src/configstream/config.py:177` |
| `FORCE_SCANNER` | yes | `bool` | `false` | no | no | `src/configstream/config.py:150` |
| `FORWARDED_ALLOW_IPS` | no | `direct-only` |  | no | no | `src/configstream/server/__main__.py:28` |
| `FRONTEND_DIR` | yes | `Optional[str]` |  | no | no | `src/configstream/config.py:159` |
| `GDRIVE_CLIENT_ID` | no | `direct-only` |  | no | no | `scripts/upload_gdrive.py:44` |
| `GDRIVE_CLIENT_SECRET` | no | `direct-only` | `<redacted>` | no | yes | `scripts/upload_gdrive.py:196`<br>`scripts/upload_gdrive.py:45` |
| `GDRIVE_REFRESH_TOKEN` | no | `direct-only` | `<redacted>` | no | yes | `scripts/upload_gdrive.py:195`<br>`scripts/upload_gdrive.py:43` |
| `GDRIVE_SA_JSON` | no | `direct-only` |  | no | no | `scripts/upload_gdrive.py:197`<br>`scripts/upload_gdrive.py:33` |
| `GEOIP_ASN_DB_PATH` | yes | `str` | `"data/GeoLite2-ASN.mmdb"` | no | no | `src/configstream/config.py:37` |
| `GEOIP_CITY_DB_PATH` | yes | `str` | `"data/GeoLite2-City.mmdb"` | no | no | `src/configstream/config.py:36` |
| `GEOIP_TIMEOUT` | yes | `int` | `5` | no | no | `src/configstream/config.py:31` |
| `GITHUB_EVENT_NAME` | no | `direct-only` |  | no | no | `scripts/generate_evidence_bundle.py:22` |
| `GITHUB_REF` | no | `direct-only` |  | no | no | `scripts/resilient_stage.py:471` |
| `GITHUB_REPOSITORY` | no | `direct-only` |  | no | no | `scripts/generate_evidence_bundle.py:24`<br>`scripts/resilient_stage.py:466` |
| `GITHUB_RUN_ATTEMPT` | no | `direct-only` |  | no | no | `scripts/finalize_release_outputs.py:589`<br>`scripts/finalize_release_outputs.py:632`<br>`scripts/generate_evidence_bundle.py:20`<br>`scripts/native_client_checks.py:232`<br>`scripts/release_gate.py:181`<br>`scripts/release_gate.py:390`<br>`scripts/resilient_stage.py:469`<br>`scripts/validate_pages_artifact.py:1203`<br>`scripts/validate_pages_artifact.py:1236`<br>`src/configstream/output/metadata.py:545`<br>`src/configstream/output/metadata.py:578` |
| `GITHUB_RUN_ID` | no | `direct-only` |  | no | no | `scripts/finalize_release_outputs.py:588`<br>`scripts/finalize_release_outputs.py:631`<br>`scripts/generate_evidence_bundle.py:19`<br>`scripts/native_client_checks.py:231`<br>`scripts/release_gate.py:180`<br>`scripts/release_gate.py:387`<br>`scripts/resilient_stage.py:468`<br>`scripts/validate_pages_artifact.py:1202`<br>`scripts/validate_pages_artifact.py:1235`<br>`src/configstream/output/metadata.py:544`<br>`src/configstream/output/metadata.py:577` |
| `GITHUB_SHA` | no | `direct-only` |  | no | no | `scripts/finalize_release_outputs.py:587`<br>`scripts/finalize_release_outputs.py:630`<br>`scripts/generate_evidence_bundle.py:21`<br>`scripts/native_client_checks.py:230`<br>`scripts/release_gate.py:179`<br>`scripts/release_gate.py:384`<br>`scripts/resilient_stage.py:470`<br>`scripts/validate_pages_artifact.py:1201`<br>`scripts/validate_pages_artifact.py:1234`<br>`src/configstream/output/metadata.py:543`<br>`src/configstream/output/metadata.py:576` |
| `GITHUB_WORKFLOW` | no | `direct-only` |  | no | no | `scripts/resilient_stage.py:467` |
| `GO_TESTER_BATCH_SIZE` | yes | `int` | `500` | no | no | `src/configstream/config.py:57` |
| `HEDGE_AFTER_MS` | yes | `int` | `800` | no | no | `src/configstream/config.py:112` |
| `HEDGE_MAX_EXTRA` | yes | `int` | `1` | no | no | `src/configstream/config.py:113` |
| `HEDGING_ENABLED` | yes | `bool` | `true` | no | no | `src/configstream/config.py:107` |
| `HF_TOKEN` | no | `direct-only` | `<redacted>` | no | yes | `scripts/upload_hf.py:216` |
| `INCLUDE_INSECURE_PROXIES` | yes | `bool` | `false` | no | no | `src/configstream/config.py:130` |
| `INGEST_MICRO_CHUNK_LINES` | yes | `int` | `500` | no | no | `src/configstream/config.py:53` |
| `INTRANET_ORIGIN` | yes | `str` | `"IR"` | no | no | `src/configstream/config.py:61` |
| `IPNS_KEY` | no | `direct-only` |  | no | no | `scripts/publish_ipfs.py:185` |
| `LAB_LIVE_TEST_ENABLED` | yes | `bool` | `false` | no | no | `src/configstream/config.py:168` |
| `LAB_MAX_CONFIG_BYTES` | yes | `int` | `65536` | no | no | `src/configstream/config.py:170` |
| `LAB_TEST_TIMEOUT_SECONDS` | yes | `float` | `15.0` | no | no | `src/configstream/config.py:169` |
| `LAT_CONNECT_TIMEOUT_MS` | yes | `int` | `3500` | no | no | `src/configstream/config.py:41` |
| `LAT_HTTP_TIMEOUT_MS` | yes | `int` | `3500` | no | no | `src/configstream/config.py:42` |
| `LAT_PER_PROXY_BUDGET_MS` | yes | `int` | `6000` | no | no | `src/configstream/config.py:43` |
| `LAT_SOFT_CAP_MS` | yes | `int` | `1800` | no | no | `src/configstream/config.py:44` |
| `LOG_LEVEL` | yes | `str` | `"INFO"` | no | no | `src/configstream/config.py:94` |
| `MASK_SENSITIVE_DATA` | yes | `bool` | `true` | no | no | `src/configstream/config.py:93` |
| `MAXMIND_LICENSE_KEY` | yes | `Optional[str]` | `<redacted>` | no | yes | `src/configstream/config.py:139` |
| `MAX_B64_INPUT_SIZE` | yes | `int` | `"<computed>"` | no | no | `src/configstream/config.py:71` |
| `MAX_B64_OUTPUT_SIZE` | yes | `int` | `"<computed>"` | no | no | `src/configstream/config.py:72` |
| `MAX_CONFIG_LINE_LENGTH` | yes | `int` | `"<computed>"` | no | no | `src/configstream/config.py:73` |
| `MAX_LATENCY` | yes | `int` | `10000` | no | no | `src/configstream/config.py:40` |
| `MAX_LINES_PER_SOURCE` | yes | `int` | `250000` | no | no | `src/configstream/config.py:74` |
| `MAX_OPENVPN_CONFIG_SIZE` | yes | `int` | `"<computed>"` | no | no | `src/configstream/config.py:75` |
| `MAX_RESPONSE_SIZE` | yes | `int` | `"<computed>"` | no | no | `src/configstream/config.py:174` |
| `MAX_SEEN_KEYS` | yes | `int` | `2000000` | no | no | `src/configstream/config.py:68` |
| `MAX_SELECTOR_MEMBERS` | no | `direct-only` |  | no | no | `scripts/finalize_release_outputs.py:52` |
| `MAX_WORKERS` | yes | `int` | `128` | no | no | `src/configstream/config.py:70` |
| `MIN_LATENCY` | yes | `int` | `10` | no | no | `src/configstream/config.py:39` |
| `MIN_SOURCE_COVERAGE` | no | `direct-only` |  | no | no | `scripts/finalize_release_outputs.py:647` |
| `NOTIFY_UPDATE_URL` | yes | `Optional[str]` |  | no | no | `src/configstream/config.py:172` |
| `OPTIMAL_RELAY_ORIGIN` | yes | `str` | `"IR"` | no | no | `src/configstream/config.py:62` |
| `OUTPUT_DIR` | no | `direct-only` |  | no | no | `src/configstream/server/utils.py:55` |
| `PARENT_RELEASE_DIGEST` | no | `direct-only` |  | no | no | `scripts/finalize_release.py:292` |
| `PATH` | no | `direct-only` |  | no | no | `scripts/native_client_checks.py:92`<br>`src/configstream/testers/go_tester/manager.py:324`<br>`src/configstream/testers/go_tester/manager.py:91` |
| `PER_HOST_MAX_CONCURRENCY` | yes | `int` | `16` | no | no | `src/configstream/config.py:111` |
| `PINATA_JWT` | no | `direct-only` |  | no | no | `scripts/publish_ipfs.py:180` |
| `PLAYWRIGHT_BROWSER_CHANNEL` | no | `direct-only` |  | no | no | `scripts/run_test_profile.py:82` |
| `PORT` | no | `direct-only` |  | no | no | `src/configstream/container_healthcheck.py:28`<br>`src/configstream/server/__main__.py:13` |
| `PRODUCER_MAX_CONCURRENCY` | yes | `int` | `100` | no | no | `src/configstream/config.py:49` |
| `PSIPHON_COUNTRY` | yes | `str` | `"US"` | no | no | `src/configstream/config.py:149` |
| `PSIPHON_ENABLED` | yes | `bool` | `false` | no | no | `src/configstream/config.py:148` |
| `PY_TESTER_BATCH_SIZE` | yes | `int` | `100` | no | no | `src/configstream/config.py:58` |
| `QUALITY_DB_PATH` | yes | `str` | `"data/source_quality.db"` | no | no | `src/configstream/config.py:178` |
| `QUEUE_MAX_TRIES` | yes | `int` | `5` | no | no | `src/configstream/config.py:117` |
| `QUEUE_OVERLOAD_KEEP_RATIO` | yes | `float` | `0.6` | no | no | `src/configstream/config.py:52` |
| `QUEUE_OVERLOAD_THRESHOLD` | yes | `float` | `0.8` | no | no | `src/configstream/config.py:51` |
| `QUEUE_PUT_TIMEOUT_SECONDS` | yes | `float` | `0.75` | no | no | `src/configstream/config.py:50` |
| `RATE_LIMIT_REQUESTS` | yes | `int` | `100` | no | no | `src/configstream/config.py:46` |
| `RATE_LIMIT_WINDOW` | yes | `int` | `60` | no | no | `src/configstream/config.py:47` |
| `RENAME_TEMPLATE` | yes | `Optional[str]` |  | no | no | `src/configstream/config.py:125` |
| `RETEST_TIMEOUT` | yes | `int` | `6` | no | no | `src/configstream/config.py:30` |
| `SCORE_SIGMOID_CENTER_RATIO` | yes | `float` | `0.6` | no | no | `src/configstream/config.py:182` |
| `SCORE_SIGMOID_SLOPE_RATIO` | yes | `float` | `0.2` | no | no | `src/configstream/config.py:183` |
| `SCORE_WEIGHTS` | yes | `dict[str, float]` | `{"current_status": 10.0, "historical_success": 40.0, "latency": 30.0, "security": 20.0}` | no | no | `src/configstream/config.py:77` |
| `SECURITY` | yes | `dict` | `{"content_injection_threshold": 5, "header_strip_threshold": 2, "malicious_asn_list": [], "redirect_follow_limit": 3, "suspicious_port_range": [[0, 1024], [5000, 5999], [8000, 8999]]}` | no | no | `src/configstream/config.py:85` |
| `SECURITY_CHECK_TIMEOUT` | yes | `int` | `8` | no | no | `src/configstream/config.py:29` |
| `SEEN_BLOOM_ENABLED` | yes | `bool` | `true` | no | no | `src/configstream/config.py:155` |
| `SEEN_BLOOM_EXPECTED_ITEMS` | yes | `int` | `2000000` | no | no | `src/configstream/config.py:156` |
| `SEEN_BLOOM_FALSE_POSITIVE_RATE` | yes | `float` | `0.001` | no | no | `src/configstream/config.py:157` |
| `SHUTDOWN_GRACE_SECONDS` | yes | `float` | `5.0` | no | no | `src/configstream/config.py:34` |
| `SOURCE_DEAD_FAILURES` | yes | `int` | `10` | no | no | `src/configstream/config.py:180` |
| `SOURCE_PROBATION_FAILURES` | yes | `int` | `3` | no | no | `src/configstream/config.py:179` |
| `SS_LIB_SHA256` | yes | `Optional[str]` |  | no | no | `src/configstream/config.py:142` |
| `STEGO_KEY` | yes | `Optional[str]` | `<redacted>` | no | yes | `scripts/audit_pipeline_outputs.py:323`<br>`src/configstream/config.py:137` |
| `STRICT_SECURITY` | yes | `bool` | `true` | no | no | `src/configstream/config.py:123` |
| `TELEGRAM_ALLOWED_USERS` | yes | `str` | `""` | no | no | `src/configstream/config.py:134` |
| `TELEGRAM_BOT_TOKEN` | yes | `Optional[str]` | `<redacted>` | no | yes | `scripts/upload_telegram.py:29`<br>`src/configstream/config.py:133` |
| `TELEGRAM_CHAT_ID` | no | `direct-only` |  | no | no | `scripts/upload_telegram.py:30` |
| `TEST_TIMEOUT` | yes | `int` | `15` | no | no | `src/configstream/config.py:27` |
| `TEST_URLS` | yes | `dict[str, str]` | `"<structured default>"` | no | no | `src/configstream/config.py:16` |
| `TLS_TESTS_ENABLED` | yes | `bool` | `true` | no | no | `src/configstream/config.py:118` |
| `TMPDIR` | no | `direct-only` |  | no | no | `src/configstream/testers/go_tester/binary_security.py:152`<br>`src/configstream/testers/go_tester/manager.py:323` |
| `UPDATE_INTERVAL_HOURS` | yes | `int` | `4` | no | no | `src/configstream/config.py:126` |
| `USE_VWARP_TUNNEL` | yes | `bool` | `true` | no | no | `src/configstream/config.py:144`<br>`src/configstream/intelligence/washer/core.py:515`<br>`src/configstream/pipeline/core.py:135`<br>`src/configstream/pipeline/core.py:140`<br>`src/configstream/pipeline/core.py:145`<br>`src/configstream/testers/go_tester/manager.py:331`<br>`src/configstream/testers/go_tester/secure_manager.py:71` |
| `UTLS_CLIENT_SHA256` | no | `direct-only` |  | no | no | `src/configstream/security/utls_wrapper.py:47` |
| `VERSION_TAG` | no | `direct-only` |  | no | no | `scripts/upload_telegram.py:46` |
| `VT_API_KEY` | yes | `Optional[str]` | `<redacted>` | no | yes | `src/configstream/config.py:135` |
| `VWARP_BIND_ADDRESS` | yes | `str` | `"127.0.0.1"` | no | no | `src/configstream/config.py:146` |
| `VWARP_FORCE_MASQUE` | no | `direct-only` |  | no | no | `src/configstream/tools/vwarp/config.py:88` |
| `VWARP_MASQUE_ENABLED` | yes | `bool` | `true` | no | no | `src/configstream/config.py:147` |
| `VWARP_SHA256` | no | `direct-only` |  | no | no | `src/configstream/tools/vwarp/binary.py:66` |
| `VWARP_SOCKS5_PORT` | yes | `int` | `10808` | no | no | `src/configstream/config.py:145` |
| `VWARP_TUNNEL_ARGS` | no | `direct-only` |  | no | no | `src/configstream/tools/vwarp/tunnel.py:172` |
| `VWARP_URL` | no | `direct-only` |  | no | no | `src/configstream/tools/vwarp/binary.py:65` |
| `VWARP_VERSION` | no | `direct-only` |  | no | no | `src/configstream/tools/vwarp/binary.py:64`<br>`src/configstream/tools/vwarp/config.py:143` |
| `WARP_KEY_POOL` | yes | `str` | `"[]"` | no | no | `src/configstream/config.py:60` |
| `WARP_PEER_KEY` | yes | `Optional[str]` |  | no | no | `src/configstream/config.py:63` |
| `WS_IDLE_TIMEOUT_SECONDS` | yes | `float` | `60.0` | no | no | `src/configstream/config.py:166` |
| `WS_MAX_CONNECTIONS` | yes | `int` | `100` | no | no | `src/configstream/config.py:165` |
| `WS_SEND_TIMEOUT_SECONDS` | yes | `float` | `5.0` | no | no | `src/configstream/config.py:167` |

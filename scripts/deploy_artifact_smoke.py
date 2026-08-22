# SPDX-License-Identifier: AGPL-3.0-or-later
"""Assemble and smoke-test a temporary GitHub Pages artifact.

The deploy workflow mutates the pipeline output directory by copying raw static
frontend files, generating runtime config, adding API aliases, and refreshing
the public artifact contract. This script mirrors that shape in a temporary
directory so release verification can prove browser tests run against the same
kind of artifact Pages uploads, without committing generated output.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess  # nosec B404
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_frontend_placeholders import (
    inject_frontend_keys,
    validate_frontend_placeholders,
)
from scripts.validate_pages_artifact import (
    REQUIRED_EXISTS,
    validate_pages_artifact,
    write_pages_contract,
)


def _write_text(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _write_zip(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("proxies.txt", "ok")


def _singbox_payload() -> dict[str, object]:
    return {
        "outbounds": [
            {"type": "selector", "tag": "Proxy", "outbounds": ["Auto", "direct"]},
            {"type": "urltest", "tag": "Auto", "outbounds": ["direct"]},
            {"type": "direct", "tag": "direct"},
        ]
    }


def _clash_payload() -> str:
    return "\n".join(
        [
            "port: 7890",
            "proxies: []",
            "proxy-groups:",
            "  - name: PROXY",
            "    type: select",
            "    proxies:",
            "      - DIRECT",
            "rules:",
            "  - MATCH,PROXY",
            "",
        ]
    )


def _xray_payload() -> dict[str, object]:
    return {
        "outbounds": [
            {"tag": "direct", "protocol": "freedom", "settings": {}},
            {"tag": "block", "protocol": "blackhole", "settings": {}},
        ],
        "routing": {"rules": []},
    }


def _proxy_fixture() -> str:
    return (
        "vless://00000000-0000-4000-8000-000000000000@"
        "example.com:443?security=tls&type=tcp#deploy-smoke"
    )


def _base64_fixture() -> str:
    return base64.b64encode(_proxy_fixture().encode("utf-8")).decode("ascii")


def _metadata_payload() -> dict[str, object]:
    now = datetime.now(timezone.utc).isoformat()
    audit = {
        "trace_id": "-",
        "tested": 0,
        "working": 0,
        "total_revived": 0,
        "revived_warp": 0,
        "revived_vwarp": 0,
        "revival_attempts": 0,
        "revival_win_rate": 0.0,
        "fetched_sources": 0,
        "total_sources": 0,
        "source_toxicity_rate": 0.0,
        "backpressure_drop": 0,
        "time_limited": False,
    }
    return {
        "schema_version": "3.0.2",
        "version": "3.0.2",
        "generated_at": now,
        "last_updated_utc": now,
        "trace_id": "-",
        "proxies_snapshot_hash": hashlib.sha256(b"[]").hexdigest(),
        "previous_proxies_snapshot_hash": None,
        "total_lines_sourced": 0,
        "total_unique_candidates": 0,
        "total_valid_proxies": 0,
        "total_proxies": 0,
        "total_tested": 0,
        "total_working": 0,
        "success_rate": 0.0,
        "latency_distribution": {
            "fast": 0,
            "medium": 0,
            "slow": 0,
            "very_slow": 0,
        },
        "protocols": {},
        "country_stats": {},
        "drop_reasons": {},
        "rejection_reasons": {},
        "asns": {},
        "total_revived": 0,
        "total_clean": 0,
        "total_smart_chains": 0,
        "smart_chain_count": 0,
        "chain_outbounds_count": 0,
        "backpressure_drop": 0,
        "revived_warp": 0,
        "revived_vwarp": 0,
        "warp_attempts": 0,
        "vwarp_attempts": 0,
        "vwarp_success": 0,
        "vwarp_win_rate": 0.0,
        "washing_enabled": False,
        "shielded_count": 0,
        "shielded_candidate_count": 0,
        "shielded_verified_count": 0,
        "evasion_utls_enabled": 0,
        "evasion_alpn_enabled": 0,
        "evasion_fragmentation_enabled": 0,
        "evasion_multiplexing_enabled": 0,
        "evasion_dns_safe_count": 0,
        "evasion_dns_hardened_count": 0,
        "duration_seconds": 0.0,
        "geo_resolved": 0,
        "cache_misses": 0,
        "final_count": 0,
        "time_limited": False,
        "time_limit_seconds": 0,
        "total_configured_sources": 0,
        "fetched_sources": 0,
        "sources_count": 0,
        "total_sources": 0,
        "update_interval_hours": 4,
        "latency_by_country": {},
        "latency_by_protocol": {},
        "chosen_subset_size": 0,
        "pipeline_execution_audit": audit,
    }


def _copy_frontend(root: Path) -> None:
    shutil.copytree(REPO_ROOT / "frontend", root, dirs_exist_ok=True)
    tools_root = root / "tools"
    tools_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / "tools" / "lab-scanner.py", tools_root / "lab-scanner.py")
    shutil.copy2(REPO_ROOT / "tools" / "lab-runner.sh", tools_root / "lab-runner.sh")


def _write_output_fixture(root: Path) -> None:
    metadata = _metadata_payload()
    for rel_path in REQUIRED_EXISTS:
        if rel_path in {
            "artifact_manifest.json",
            "health.json",
            "index.html",
            "assets/js/runtime-config.js",
        }:
            continue
        target = root / rel_path
        if rel_path.endswith(".zip"):
            _write_zip(target)
        elif rel_path == "metadata.json" or rel_path == "api/stats":
            _write_text(target, json.dumps(metadata, ensure_ascii=False))
        elif rel_path == "pipeline_events.jsonl":
            _write_text(
                target,
                json.dumps(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "event_type": "stream_close",
                        "message": "Event stream closing.",
                    },
                    separators=(",", ":"),
                )
                + "\n",
            )
        elif rel_path == "proxies.json" or rel_path == "api/proxies":
            _write_text(target, "[]")
        elif (
            rel_path.startswith(("singbox", "chains"))
            or rel_path == "chosen/singbox.json"
        ) and rel_path.endswith(".json"):
            _write_text(target, json.dumps(_singbox_payload(), ensure_ascii=False))
        elif (
            rel_path.startswith("clash") or rel_path == "chosen/clash.yaml"
        ) and rel_path.endswith(".yaml"):
            _write_text(target, _clash_payload())
        elif rel_path == "xray.json":
            _write_text(target, json.dumps(_xray_payload(), ensure_ascii=False))
        elif Path(rel_path).name.startswith("base64") and rel_path.endswith(".txt"):
            _write_text(target, _base64_fixture())
        elif rel_path in {
            "proxies.txt",
            "proxies-dns-safe.txt",
            "proxies-dns-hardened.txt",
        }:
            _write_text(target, _proxy_fixture())
        elif rel_path.endswith(".json"):
            _write_text(target, "{}")
        else:
            _write_text(target)
    (root / ".nojekyll").touch()


def _runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    env["CS_PUBLIC_KEY"] = (
        "d75a980182b10ab7d54bfed3c964073a" "0ee172f3daa62325af021a68f707511a"
    )
    env.setdefault("STEGO_KEY", "deploy-smoke-stego-key")
    env.setdefault("CS_IPNS_KEY", "deploy-smoke-ipns-key")
    return env


def _run(command: list[str]) -> int:
    print("+ " + " ".join(command), flush=True)
    return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode  # nosec B603


def run_smoke(*, keep_artifact: bool = False) -> int:
    temp_dir = Path(tempfile.mkdtemp(prefix="configstream-pages-smoke-"))
    try:
        _copy_frontend(temp_dir)
        _write_output_fixture(temp_dir)
        inject_frontend_keys(temp_dir, _runtime_env())
        placeholder_errors = validate_frontend_placeholders(temp_dir, strict=True)
        if placeholder_errors:
            print("ERROR: frontend runtime config validation failed", file=sys.stderr)
            for error in placeholder_errors:
                print(f"  - {error}", file=sys.stderr)
            return 1

        write_pages_contract(temp_dir)
        artifact_errors = validate_pages_artifact(temp_dir)
        if artifact_errors:
            print("ERROR: Pages artifact validation failed", file=sys.stderr)
            for error in artifact_errors:
                print(f"  - {error}", file=sys.stderr)
            return 1

        code = _run(
            [
                "node",
                "scripts/frontend_same_origin_smoke.cjs",
                "--root",
                str(temp_dir),
                "--require-runtime-config",
            ]
        )
        if code == 0:
            print(f"OK: deploy artifact smoke passed for {temp_dir}")
        return code
    finally:
        if keep_artifact:
            print(f"Kept temporary Pages artifact: {temp_dir}")
        else:
            shutil.rmtree(temp_dir, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep-artifact",
        action="store_true",
        help="Leave the temporary artifact on disk for manual inspection.",
    )
    args = parser.parse_args(argv)
    return run_smoke(keep_artifact=bool(args.keep_artifact))


if __name__ == "__main__":
    raise SystemExit(main())

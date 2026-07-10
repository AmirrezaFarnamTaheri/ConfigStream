# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate a consolidated evidence bundle for a pipeline and deploy run."""
import logging

import argparse
import base64
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def get_run_metadata() -> Dict[str, Any]:
    """Return CI run identity fields from environment variables."""
    return {
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "event": os.environ.get("GITHUB_EVENT_NAME", "manual"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repository": os.environ.get("GITHUB_REPOSITORY", "ConfigStream"),
    }


def get_file_stats(output_dir: str) -> Dict[str, Any]:
    """Collect high-level statistics about the pipeline output directory."""
    stats: Dict[str, Any] = {}
    output_path = Path(output_dir)
    if not output_path.exists():
        return stats

    # Count public files
    files = list(output_path.glob("**/*"))
    stats["total_files"] = len([f for f in files if f.is_file()])
    stats["total_size_bytes"] = sum(f.stat().st_size for f in files if f.is_file())

    # Count working proxies from metadata
    metadata_file = output_path / "metadata.json"
    if metadata_file.exists():
        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            stats["working_proxies"] = metadata.get(
                "total_working", metadata.get("working", 0)
            )
            stats["total_proxies"] = metadata.get("total_proxies", 0)
            stats["shielded_count"] = metadata.get("shielded_count", 0)
            stats["shielded_verified_count"] = metadata.get(
                "shielded_verified_count", 0
            )
        except Exception:  # nosec B110
            logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)
            pass

    # Count decoded subscription lines from base64.txt
    base64_file = output_path / "base64.txt"
    if base64_file.exists():
        try:
            content = base64_file.read_text(encoding="utf-8").strip()
            if content:
                decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
                stats["base64_proxy_count"] = len(
                    [line for line in decoded.splitlines() if line.strip()]
                )
        except Exception:  # nosec B110
            logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)
            pass

    return stats


def generate_evidence_bundle(
    output_dir: str,
    evidence_dir: str,
    smoke_report: Optional[str] = None,
    native_report: Optional[str] = None,
) -> None:
    """
    Assemble a durable evidence bundle from a completed pipeline run.

    Copies core control artifacts (health.json, metadata.json,
    artifact_manifest.json) into *evidence_dir*, writes a machine-readable
    summary.json, and generates a human-readable README.md.  An optional
    smoke-test JSON report is embedded when provided.
    """
    output_path = Path(output_dir)
    evidence_path = Path(evidence_dir)
    evidence_path.mkdir(parents=True, exist_ok=True)

    # 1. Copy core control artifacts
    for filename in ["health.json", "metadata.json", "artifact_manifest.json"]:
        src = output_path / filename
        if src.exists():
            shutil.copy2(src, evidence_path / filename)

    # 2. Collect run metadata and file statistics
    bundle_meta: Dict[str, Any] = get_run_metadata()
    bundle_meta["file_stats"] = get_file_stats(output_dir)

    if smoke_report and Path(smoke_report).exists():
        try:
            bundle_meta["smoke_test"] = json.loads(
                Path(smoke_report).read_text(encoding="utf-8")
            )
        except Exception:
            logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)
            bundle_meta["smoke_test"] = {"error": "Failed to read smoke report"}

    native_report_path = Path(native_report) if native_report else None
    default_native_report = evidence_path / "native_client_check_report.json"
    if native_report_path and native_report_path.exists():
        try:
            bundle_meta["native_client_check"] = json.loads(
                native_report_path.read_text(encoding="utf-8")
            )
            if native_report_path.resolve() != default_native_report.resolve():
                shutil.copy2(native_report_path, default_native_report)
        except Exception:
            logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)
            bundle_meta["native_client_check"] = {
                "error": "Failed to read native client check report"
            }
    elif default_native_report.exists():
        try:
            bundle_meta["native_client_check"] = json.loads(
                default_native_report.read_text(encoding="utf-8")
            )
        except Exception:
            logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)
            bundle_meta["native_client_check"] = {
                "error": "Failed to read native client check report"
            }

    # 3. Write machine-readable summary.json
    (evidence_path / "summary.json").write_text(
        json.dumps(bundle_meta, indent=2), encoding="utf-8"
    )

    # 4. Generate human-readable README.md
    file_stats = bundle_meta["file_stats"]
    readme_lines = [
        "# ConfigStream Evidence Bundle",
        "",
        f"- **Timestamp**: {bundle_meta['timestamp']}",
        (
            f"- **Run ID**: [{bundle_meta['run_id']}]"
            f"(https://github.com/{bundle_meta['repository']}"
            f"/actions/runs/{bundle_meta['run_id']})"
        ),
        f"- **Commit**: `{bundle_meta['commit']}`",
        f"- **Event**: {bundle_meta['event']}",
        "",
        "## Pipeline Stats",
        f"- **Total Proxies**: {file_stats.get('total_proxies', 0)}",
        f"- **Working Proxies**: {file_stats.get('working_proxies', 0)}",
        f"- **Shielded Candidates**: {file_stats.get('shielded_count', 0)}",
        f"- **Shielded Verified**: {file_stats.get('shielded_verified_count', 0)}",
        f"- **Base64 Subscriptions**: {file_stats.get('base64_proxy_count', 0)} proxies",
        "",
        "## Artifact Stats",
        f"- **Total Files**: {file_stats.get('total_files', 0)}",
        f"- **Total Size**: {file_stats.get('total_size_bytes', 0) / 1024 / 1024:.2f} MB",
        "",
        "## Verification Status",
    ]

    smoke = bundle_meta.get("smoke_test")
    if smoke:
        status = smoke.get("status", "unknown")
        passed = status == "passed"
        readme_lines.append(
            f"- **Deployed Smoke Test**: {'PASSED' if passed else 'FAILED'}"
        )
        for error in smoke.get("errors") or []:
            readme_lines.append(f"  - {error}")
    else:
        readme_lines.append("- **Deployed Smoke Test**: NOT RUN")

    native = bundle_meta.get("native_client_check")
    if isinstance(native, dict):
        summary = native.get("summary", {})
        if isinstance(summary, dict):
            readme_lines.append(
                "- **Native Client Checks**: "
                f"{summary.get('passed', 0)} passed, "
                f"{summary.get('failed', 0)} failed, "
                f"{summary.get('skipped', 0)} skipped"
            )
        else:
            readme_lines.append("- **Native Client Checks**: report captured")
    else:
        readme_lines.append("- **Native Client Checks**: NOT RUN")

    (evidence_path / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")
    print(f"Evidence bundle generated in {evidence_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory containing pipeline outputs",
    )
    parser.add_argument(
        "--evidence-dir",
        default="evidence",
        help="Directory to save evidence bundle",
    )
    parser.add_argument(
        "--smoke-report",
        help="Path to smoke test JSON report",
    )
    parser.add_argument(
        "--native-report",
        help="Path to native client check JSON report",
    )
    args = parser.parse_args()

    generate_evidence_bundle(
        args.output_dir, args.evidence_dir, args.smoke_report, args.native_report
    )

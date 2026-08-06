# SPDX-License-Identifier: AGPL-3.0-or-later
"""Container-local health probe used by Docker HEALTHCHECK."""

from __future__ import annotations

import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path


def check_local_runtime() -> list[str]:
    reasons: list[str] = []
    if shutil.which("configstream-tester") is None:
        reasons.append("native_tester_missing")
    try:
        import configstream  # noqa: F401
    except ImportError:
        reasons.append("package_import_failed")
    if not Path("/app/src/configstream").is_dir():
        reasons.append("application_source_missing")
    return reasons


def check_http_liveness() -> list[str]:
    raw_port = os.getenv("PORT", "8000")
    try:
        port = int(raw_port)
    except ValueError:
        return ["http_port_invalid"]
    if not 1 <= port <= 65535:
        return ["http_port_invalid"]
    url = f"http://127.0.0.1:{port}/live"
    try:
        with urllib.request.urlopen(url, timeout=3) as response:  # nosec B310
            if response.status < 200 or response.status >= 400:
                return [f"http_status:{response.status}"]
    except (OSError, urllib.error.URLError, ValueError) as exc:
        return [f"http_unreachable:{type(exc).__name__}"]
    return []


def main() -> int:
    reasons = check_local_runtime()
    if os.getenv("CONFIGSTREAM_HEALTHCHECK_HTTP") == "1":
        reasons.extend(check_http_liveness())
    if reasons:
        print("unhealthy:" + ",".join(reasons), file=sys.stderr)
        return 1
    print("healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

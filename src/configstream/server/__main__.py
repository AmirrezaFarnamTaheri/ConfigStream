# SPDX-License-Identifier: AGPL-3.0-or-later
"""Executable ASGI server entry point for container and Render deployments."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    try:
        port = int(os.getenv("PORT", "8000"))
    except ValueError as exc:
        raise SystemExit("PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise SystemExit("PORT must be between 1 and 65535")

    host = os.getenv("CONFIGSTREAM_HOST", "127.0.0.1").strip()
    if not host:
        raise SystemExit("CONFIGSTREAM_HOST must not be empty")

    uvicorn.run(
        "configstream.server:app",
        host=host,
        port=port,
        proxy_headers=True,
        forwarded_allow_ips=os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1"),
    )


if __name__ == "__main__":
    main()

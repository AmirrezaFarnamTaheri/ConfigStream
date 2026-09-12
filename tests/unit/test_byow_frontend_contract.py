# SPDX-License-Identifier: AGPL-3.0-or-later
"""Contract for the manually deployed Worker configuration."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WRANGLER = ROOT / "tools" / "wrangler.toml"
WORKER = ROOT / "tools" / "worker.js"


def test_worker_deployment_docs_match_required_bindings() -> None:
    wrangler = WRANGLER.read_text(encoding="utf-8")
    worker = WORKER.read_text(encoding="utf-8")

    for name in ("TUNNEL_TOKEN", "PROXY_HOST", "PROXY_PORT"):
        assert name in worker
        assert name in wrangler
    assert "USER_ID" not in wrangler
    assert "DEFAULT_PROXY_IP" not in wrangler
    assert "DEFAULT_PROXY_PORT" not in wrangler
    assert "generic rewrite target" in wrangler

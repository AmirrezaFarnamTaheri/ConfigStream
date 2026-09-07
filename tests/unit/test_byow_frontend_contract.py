# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cross-layer contract for the BYOW frontend and Worker deployment config."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BYOW = ROOT / "frontend" / "assets" / "js" / "byow.js"
WRANGLER = ROOT / "tools" / "wrangler.toml"
WORKER = ROOT / "tools" / "worker.js"


def test_frontend_does_not_rewrite_arbitrary_proxy_transports() -> None:
    text = BYOW.read_text(encoding="utf-8")

    assert "Automatic Private Bridge generation is currently disabled" in text
    assert "modifiedConfig.outbounds" not in text
    assert "outbound.server =" not in text
    assert "104.16.20.10" not in text
    assert "Manual Bridge Setup Required" in text


def test_byow_does_not_run_global_feather_replacement() -> None:
    text = BYOW.read_text(encoding="utf-8")

    assert "feather.replace" not in text
    assert "window.feather.replace" not in text


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

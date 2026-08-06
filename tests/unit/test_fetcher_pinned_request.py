# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path


def test_fetcher_applies_request_level_host_and_sni_pinning_to_injected_clients():
    source = (
        Path(__file__).resolve().parents[2]
        / "src/configstream/pipeline/fetcher.py"
    ).read_text(encoding="utf-8")
    assert "rewrite_request_to_pinned_ip(" in source
    assert "extensions=dict(pinned_request.extensions)" in source
    assert "headers=dict(pinned_request.headers)" in source
    assert "str(pinned_request.url)" in source

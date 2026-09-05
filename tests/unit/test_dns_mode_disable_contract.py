# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from configstream.models import Proxy
from configstream.output_logic import generate_categorized_outputs


def test_disabled_dns_variants_ignore_nonempty_caches_and_chain_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DNS_SAFE_OUTPUTS", "false")
    monkeypatch.setenv("DNS_HARDENED_OUTPUTS", "false")

    proxy = Proxy(
        config="socks5://1.1.1.1:1080#node",
        protocol="socks5",
        address="1.1.1.1",
        port=1080,
        is_working=True,
    )
    washed_outbounds: list[dict[str, Any]] = [
        {"type": "direct", "tag": "washed-leak-marker"}
    ]
    smart_chains: dict[str, list[list[dict[str, Any]]]] = {
        "test": [[{"type": "direct", "tag": "smart-leak-marker"}]]
    }
    stale_cache = ([proxy], {"example.com": "1.1.1.1"})

    files = generate_categorized_outputs(
        [proxy],
        tmp_path,
        washed_outbounds=washed_outbounds,
        washed_ids=set(),
        smart_chains=smart_chains,
        dns_safe_cache=stale_cache,
        dns_hardened_cache=stale_cache,
    )

    assert files["base64_dns_safe"].read_text(encoding="utf-8") == ""
    assert files["base64_dns_hardened"].read_text(encoding="utf-8") == ""

    for key in (
        "singbox_dns_safe",
        "singbox_dns_hardened",
        "singbox_chains_dns_safe",
        "chains_dns_safe",
        "singbox_chains_dns_hardened",
        "chains_dns_hardened",
    ):
        content = files[key].read_text(encoding="utf-8")
        assert "washed-leak-marker" not in content
        assert "smart-leak-marker" not in content

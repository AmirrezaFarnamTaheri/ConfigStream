# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression coverage: public subscriptions may only include verified nodes."""

from __future__ import annotations

import json

from configstream.models import Proxy
from configstream.output.public_lists import generate_categorized_lists
from configstream.output.subscriptions import get_export_pool, select_chosen_proxies


def _proxy(name: str, *, working: bool) -> Proxy:
    return Proxy(
        config=f"vless://00000000-0000-0000-0000-000000000001@{name}.example:443#{name}",
        protocol="vless",
        address=f"{name}.example",
        port=443,
        uuid="00000000-0000-0000-0000-000000000001",
        remarks=name,
        country_code="US",
        is_working=working,
        details={"tls": True},
    )


def test_export_pool_excludes_failed_even_when_no_working_nodes() -> None:
    failed = _proxy("failed", working=False)
    assert get_export_pool([failed]) == []
    assert select_chosen_proxies([failed], 5, 10) == []


def test_export_pool_keeps_working_nodes_without_uri_and_not_failed_fallback() -> None:
    verified_no_uri = Proxy(
        config="not-a-uri",
        protocol="wireguard",
        address="wg.example",
        port=2408,
        is_working=True,
    )
    failed = _proxy("failed", working=False)
    assert get_export_pool([verified_no_uri, failed]) == [verified_no_uri]


def test_categorized_import_profiles_exclude_failed_but_preserve_diagnostic_rows(tmp_path) -> None:
    verified = _proxy("verified", working=True)
    failed = _proxy("failed", working=False)
    generate_categorized_lists([failed, verified], tmp_path)
    for path in (tmp_path / "countries" / "US.json", tmp_path / "protocols" / "vless.json"):
        outbounds = json.loads(path.read_text(encoding="utf-8"))["outbounds"]
        tags = {item.get("tag") for item in outbounds}
        assert "verified" in tags
        assert "failed" not in tags
    uri_text = (tmp_path / "protocols" / "vless.txt").read_text(encoding="utf-8")
    assert "verified.example" in uri_text
    assert "failed.example" not in uri_text
    diagnostic_rows = json.loads((tmp_path / "protocols" / "vless.list.json").read_text(encoding="utf-8"))
    assert len(diagnostic_rows) == 2
    assert {item["is_working"] for item in diagnostic_rows} == {True, False}

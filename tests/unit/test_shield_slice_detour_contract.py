# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for shielded revived chains in sliced sing-box outputs.

Production failure (runs 32596291691 / 32609647125): ``countries/XX.json`` and
``protocols/revived.json`` carried ``detour: SHIELD-XX-*`` references whose
target tags no longer existed in the file, so ``validate_pages_artifact.py``
failed the release gate and nothing was published for two weeks.
"""

from __future__ import annotations

import json
from pathlib import Path

from configstream.converters.singbox import to_singbox_outbound
from configstream.generators.singbox import generate_singbox_config
from configstream.models import Proxy
from configstream.output.public_lists import generate_categorized_lists
from configstream.output.singbox_contract import validate_singbox_config
from scripts.finalize_release_outputs import modernize_singbox

_WG_PRIVATE = "6M6tfYfQ6B0fLF8A3XJ2Z2z8jz4Yb9k+f0z8xN2aM0E="
_WG_PUBLIC = "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="


def _shield_chain(shield_tag: str, payload_tag: str) -> list[dict[str, object]]:
    """Chain shape emitted by ProxyWasher.shield_batch + create_revived_proxy."""
    return [
        {
            "type": "wireguard",
            "tag": shield_tag,
            "server": "162.159.192.1",
            "server_port": 2408,
            "private_key": _WG_PRIVATE,
            "peer_public_key": _WG_PUBLIC,
            "local_address": ["10.87.214.169/32"],
            "reserved": [84, 146, 56],
            "mtu": 1280,
        },
        {
            "type": "wireguard",
            "tag": payload_tag,
            "server": "188.114.96.1",
            "server_port": 2408,
            "private_key": _WG_PRIVATE,
            "peer_public_key": _WG_PUBLIC,
            "local_address": ["172.16.0.2/32"],
            "detour": shield_tag,
            "mtu": 1280,
        },
    ]


def _shielded_revived_proxy(index: int, shield_tag: str) -> Proxy:
    payload_tag = f"🇽🇽 | REVIVED-VLESS+TCP+WARP | SHIELDED | {index:08x}"
    chain = _shield_chain(shield_tag, payload_tag)
    return Proxy(
        config="chain://",
        protocol="revived",
        address="188.114.96.1",
        port=2408,
        remarks=f"🇽🇽 | REVIVED+TCP+WARP | SHIELDED | {index:08x}",
        country_code="XX",
        process="shielded",
        details={
            "is_revived": True,
            "is_shielded": True,
            "chain": chain,
            # Production records also carry the raw outbound form consumed by
            # the converter fallback path.
            "chain_outbounds": [dict(hop) for hop in chain],
        },
        is_working=False,
    )


def _assert_contract_holds(config_path: Path) -> dict[str, object]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    modernized = modernize_singbox(payload)
    errors = validate_singbox_config(modernized, config_path.name)
    assert errors == [], f"{config_path.name}: {errors[:5]}"
    return modernized


def test_revived_slice_keeps_shield_detour_resolvable(tmp_path: Path) -> None:
    proxies = [_shielded_revived_proxy(1, "SHIELD-XX-0")]
    generated = generate_categorized_lists(proxies, tmp_path)

    country = _assert_contract_holds(generated["country_XX"])
    tags = {
        str(item.get("tag"))
        for item in [*country.get("outbounds", []), *country.get("endpoints", [])]
    }
    assert "SHIELD-XX-0" in tags, "inner SHIELD hop lost its tag"
    proto = _assert_contract_holds(generated["proto_revived"])
    proto_tags = {
        str(item.get("tag"))
        for item in [*proto.get("outbounds", []), *proto.get("endpoints", [])]
    }
    assert "SHIELD-XX-0" in proto_tags


def test_revived_conversion_selects_entry_hop_and_preserves_inner_tags() -> None:
    proxy = _shielded_revived_proxy(2, "SHIELD-XX-7")
    outbound = to_singbox_outbound(proxy)
    assert outbound is not None

    # The user-facing remarks tag lands on the selectable entry hop...
    assert outbound["tag"] == proxy.remarks
    # ...whose detour still points at the inner hop...
    assert outbound["detour"] == "SHIELD-XX-7"
    # ...and the inner hop keeps its original tag.
    extras = outbound.get("_extra_outbounds")
    assert isinstance(extras, list) and len(extras) == 1
    assert extras[0]["tag"] == "SHIELD-XX-7"
    assert "detour" not in extras[0]


def test_duplicate_shield_tags_uniquify_without_dangling_detours(
    tmp_path: Path,
) -> None:
    # Multiple washer batches reuse the same SHIELD indices, so slices can
    # contain several chains referencing the "same" shield tag.
    proxies = [
        _shielded_revived_proxy(1, "SHIELD-XX-0"),
        _shielded_revived_proxy(2, "SHIELD-XX-0"),
        _shielded_revived_proxy(3, "SHIELD-XX-1"),
    ]
    generated = generate_categorized_lists(proxies, tmp_path)
    country = _assert_contract_holds(generated["country_XX"])

    shield_tags = [
        str(item.get("tag"))
        for item in [*country.get("outbounds", []), *country.get("endpoints", [])]
        if str(item.get("tag", "")).startswith("SHIELD-")
    ]
    assert sorted(shield_tags) == ["SHIELD-XX-0", "SHIELD-XX-0-0", "SHIELD-XX-1"]

    rendered = json.loads(
        generate_singbox_config(proxies),
    )
    errors = validate_singbox_config(rendered, "singbox.json")
    assert errors == [], errors[:5]

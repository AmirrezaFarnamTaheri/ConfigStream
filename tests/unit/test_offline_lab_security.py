# SPDX-License-Identifier: AGPL-3.0-or-later
"""Security contract for the standalone offline laboratory."""

from __future__ import annotations

from pathlib import Path

LAB = Path(__file__).resolve().parents[2] / "frontend" / "lab-offline.html"


def test_offline_lab_does_not_embed_a_wireguard_private_key() -> None:
    text = LAB.read_text(encoding="utf-8")
    assert "YNS+CEQE6JIQiVWcOUJd0K8FLFeCQBONJnXCdFnMRlQ=" not in text
    assert "ob.private_key=d.private_key.trim()" in text
    assert "WireGuard private key is required" in text


def test_offline_lab_singbox_export_uses_wireguard_endpoints() -> None:
    text = LAB.read_text(encoding="utf-8")
    assert "const endpoints=[];" in text
    assert "if(o.type!=='wireguard'){sbOutbounds.push(o);return;}" in text
    assert "if(endpoints.length)lastConfig.endpoints=endpoints;" in text
    assert "outbounds:[...sbOutbounds,{type:'direct',tag:'direct'}]" in text

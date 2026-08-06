# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate complete Surge/Loon/Quantumult profiles with explicit omissions."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

ProfileGenerator = Callable[[list[dict[str, Any]]], tuple[str, dict[str, int]]]


def load_records(root: Path) -> list[dict[str, Any]]:
    payload = json.loads((root / "proxies.json").read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("proxies.json must be a list")
    return [item for item in payload if isinstance(item, dict)]


def values(
    record: dict[str, Any],
) -> tuple[str, str, int, dict[str, Any], str, str]:
    protocol = str(record.get("protocol") or "").lower()
    name = (
        str(record.get("remarks") or record.get("id") or "Proxy")
        .replace(",", "_")
        .replace("=", "_")
        .replace("\n", " ")
    )
    raw_details = record.get("details")
    details: dict[str, Any] = raw_details if isinstance(raw_details, dict) else {}
    user = str(
        record.get("uuid") or details.get("username") or details.get("user") or ""
    )
    password = str(details.get("password") or "")
    return protocol, name, int(record.get("port") or 0), details, user, password


def surge(records: list[dict[str, Any]]) -> tuple[str, dict[str, int]]:
    lines = [
        "#!MANAGED-CONFIG ConfigStream",
        "[General]",
        "loglevel = notify",
        "",
        "[Proxy]",
    ]
    names: list[str] = []
    unsupported: Counter[str] = Counter()
    for record in records:
        if not record.get("is_working") or record.get("protocol") == "chain":
            continue
        protocol, name, port, details, user, password = values(record)
        host = record.get("address")
        line = None
        if protocol == "http":
            line = f"{name} = http, {host}, {port}"
            if user:
                line += f", username={user}, password={password}"
            if details.get("tls"):
                line += ", tls=true"
        elif protocol in {"socks", "socks5"}:
            line = f"{name} = socks5, {host}, {port}, udp-relay=true"
            if user:
                line += f", username={user}, password={password}"
        elif protocol in {"ss", "shadowsocks"}:
            method = (
                details.get("method")
                or details.get("cipher")
                or "chacha20-ietf-poly1305"
            )
            line = (
                f"{name} = ss, {host}, {port}, "
                f"encrypt-method={method}, password={password}"
            )
        elif protocol in {"vmess", "vless"}:
            line = f"{name} = {protocol}, {host}, {port}, username={record.get('uuid')}"
        elif protocol == "trojan":
            line = (
                f"{name} = trojan, {host}, {port}, "
                f"password={record.get('uuid') or password}"
            )
        elif protocol in {"hysteria2", "hy2"}:
            line = (
                f"{name} = hysteria2, {host}, {port}, "
                f"password={record.get('uuid') or password}"
            )
        elif protocol == "tuic":
            token = details.get("password") or record.get("uuid")
            line = f"{name} = tuic, {host}, {port}, token={token}, version=5"
        if line:
            lines.append(line)
            names.append(name)
        else:
            unsupported[protocol or "unknown"] += 1
    lines.extend(
        [
            "",
            "[Proxy Group]",
            f"PROXY = select, {', '.join(names) if names else 'DIRECT'}",
            "",
            "[Rule]",
            "FINAL,PROXY",
        ]
    )
    return "\n".join(lines) + "\n", dict(unsupported)


def loon(records: list[dict[str, Any]]) -> tuple[str, dict[str, int]]:
    lines = ["# ConfigStream Loon Configuration", "[Proxy]"]
    names: list[str] = []
    unsupported: Counter[str] = Counter()
    for record in records:
        if not record.get("is_working") or record.get("protocol") == "chain":
            continue
        protocol, name, port, details, user, password = values(record)
        host = record.get("address")
        line = None
        if protocol == "http":
            line = f"{name} = http, {host}, {port}"
        elif protocol in {"socks", "socks5"}:
            line = f"{name} = socks5, {host}, {port}"
        elif protocol in {"ss", "shadowsocks"}:
            method = (
                details.get("method")
                or details.get("cipher")
                or "chacha20-ietf-poly1305"
            )
            line = f'{name} = shadowsocks, {host}, {port}, {method}, "{password}"'
        elif protocol == "vmess":
            line = (
                f"{name} = vmess, {host}, {port}, "
                f'chacha20-poly1305, "{record.get("uuid")}"'
            )
        elif protocol == "trojan":
            line = (
                f"{name} = trojan, {host}, {port}, "
                f'"{record.get("uuid") or password}"'
            )
        elif protocol == "vless":
            line = f'{name} = vless, {host}, {port}, "{record.get("uuid")}"'
        if line:
            if user and protocol in {"http", "socks", "socks5"}:
                line += f', username="{user}", password="{password}"'
            lines.append(line)
            names.append(name)
        else:
            unsupported[protocol or "unknown"] += 1
    lines.extend(
        [
            "",
            "[Proxy Group]",
            f"PROXY = select,{','.join(names) if names else 'DIRECT'}",
        ]
    )
    return "\n".join(lines) + "\n", dict(unsupported)


def quantumult(records: list[dict[str, Any]]) -> tuple[str, dict[str, int]]:
    lines = ["# ConfigStream Quantumult X server fragment"]
    unsupported: Counter[str] = Counter()
    for record in records:
        if not record.get("is_working") or record.get("protocol") == "chain":
            continue
        protocol, name, port, details, user, password = values(record)
        host = record.get("address")
        line = None
        if protocol == "http":
            line = f"http={name}: {host}, {port}"
        elif protocol in {"socks", "socks5"}:
            line = f"socks5={name}: {host}, {port}"
        elif protocol in {"ss", "shadowsocks"}:
            method = (
                details.get("method")
                or details.get("cipher")
                or "chacha20-ietf-poly1305"
            )
            line = (
                f"shadowsocks={name}: {host}, {port}, "
                f"method={method}, password={password}"
            )
        elif protocol == "vmess":
            line = (
                f"vmess={name}: {host}, {port}, method=chacha20-poly1305, "
                f"password={record.get('uuid')}"
            )
        elif protocol == "trojan":
            line = (
                f"trojan={name}: {host}, {port}, "
                f"password={record.get('uuid') or password}, over-tls=true"
            )
        elif protocol == "vless":
            line = (
                f"vless={name}: {host}, {port}, method=none, "
                f"uuid={record.get('uuid')}"
            )
        if line:
            if user and protocol in {"http", "socks", "socks5"}:
                line += f", username={user}, password={password}"
            lines.append(line)
        else:
            unsupported[protocol or "unknown"] += 1
    return "\n".join(lines) + "\n", dict(unsupported)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    args = parser.parse_args()
    records = load_records(args.artifact_dir)
    generators: dict[str, ProfileGenerator] = {
        "surge": surge,
        "loon": loon,
        "quantumult": quantumult,
    }
    report: dict[str, Any] = {"schema_version": 1, "profiles": {}}
    profiles = report["profiles"]
    if not isinstance(profiles, dict):
        raise TypeError("profiles report must be a dictionary")
    for family, generator in generators.items():
        content, unsupported = generator(records)
        pattern = "quantumult*.conf" if family == "quantumult" else f"{family}*.conf"
        targets = list(args.artifact_dir.glob(pattern))
        if not targets:
            targets = [
                args.artifact_dir
                / ("quantumult.conf" if family == "quantumult" else f"{family}.conf")
            ]
        for target in targets:
            target.write_text(content, encoding="utf-8")
        profiles[family] = {
            "files": [path.name for path in targets],
            "unsupported": unsupported,
        }
    (args.artifact_dir / "legacy_profile_coverage.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate protocol support claims against schema and parser exports."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ENCODING = "utf-8"
ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "docs" / "protocol_matrix.json"
SCHEMA_PATH = ROOT / "schema" / "proxy.schema.json"
PARSERS_INIT = ROOT / "src" / "configstream" / "parsers" / "__init__.py"
README_PATH = ROOT / "README.md"

VALID_KINDS = {"canonical", "alias", "schema-only", "internal"}
README_PROTOCOL_NAMES = {
    "VLESS": "vless",
    "VMess": "vmess",
    "Trojan": "trojan",
    "Shadowsocks": "shadowsocks",
    "SSR": "ssr",
    "Hysteria": "hysteria",
    "Hysteria2": "hysteria2",
    "TUIC": "tuic",
    "WireGuard": "wireguard",
    "OpenVPN": "openvpn",
    "HTTP": "http",
    "SOCKS": "socks5",
    "SSH": "ssh",
    "Xray": "xray",
    "Snell": "snell",
    "Brook": "brook",
    "Juicity": "juicity",
}


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding=ENCODING) as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be an object")
    return data


def _schema_protocols() -> set[str]:
    schema = _read_json(SCHEMA_PATH)
    values = schema["properties"]["protocol"]["enum"]
    return set(values)


def _parser_exports() -> set[str]:
    text = PARSERS_INIT.read_text(encoding=ENCODING)
    return set(re.findall(r'"(parse_[a-zA-Z0-9_]+)"', text))


def validate_protocol_matrix(path: Path = MATRIX_PATH) -> list[str]:
    errors: list[str] = []
    try:
        matrix = _read_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"protocol matrix cannot be read: {exc}"]

    protocols = matrix.get("protocols")
    if not isinstance(protocols, list) or not protocols:
        return ["protocol matrix must contain a non-empty protocols list"]

    schema_protocols = _schema_protocols()
    parser_exports = _parser_exports()
    ids: set[str] = set()
    entries: dict[str, dict[str, Any]] = {}

    for index, entry in enumerate(protocols):
        prefix = f"protocols[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        protocol_id = entry.get("id")
        if not isinstance(protocol_id, str) or not protocol_id:
            errors.append(f"{prefix}.id must be a non-empty string")
            continue
        if protocol_id in ids:
            errors.append(f"duplicate protocol id: {protocol_id}")
        ids.add(protocol_id)
        entries[protocol_id] = entry

        if entry.get("kind") not in VALID_KINDS:
            errors.append(f"{protocol_id} has invalid kind: {entry.get('kind')}")
        if not isinstance(entry.get("public"), bool):
            errors.append(f"{protocol_id}.public must be a boolean")
        if entry.get("schema") is not True:
            errors.append(f"{protocol_id}.schema must be true")
        if not isinstance(entry.get("frontend"), bool):
            errors.append(f"{protocol_id}.frontend must be a boolean")
        if not isinstance(entry.get("singbox_export"), bool):
            errors.append(f"{protocol_id}.singbox_export must be a boolean")
        if not isinstance(entry.get("clash_export"), bool):
            errors.append(f"{protocol_id}.clash_export must be a boolean")
        if not isinstance(entry.get("notes"), str) or not entry["notes"].strip():
            errors.append(f"{protocol_id}.notes must be non-empty")

        parser = entry.get("parser")
        if parser is not None and parser not in parser_exports:
            errors.append(f"{protocol_id} references unknown parser export: {parser}")

        normalized_to = entry.get("normalized_to")
        if normalized_to is not None and normalized_to not in schema_protocols:
            errors.append(
                f"{protocol_id} normalizes to unknown protocol: {normalized_to}"
            )

        if entry.get("public") and entry.get("kind") == "canonical" and not parser:
            errors.append(f"{protocol_id} public canonical protocol must list parser")

    missing = sorted(schema_protocols - ids)
    extra = sorted(ids - schema_protocols)
    if missing:
        errors.append(f"protocol matrix missing schema protocols: {', '.join(missing)}")
    if extra:
        errors.append(f"protocol matrix has non-schema protocols: {', '.join(extra)}")

    readme = README_PATH.read_text(encoding=ENCODING)
    for display, protocol_id in README_PROTOCOL_NAMES.items():
        if display not in readme:
            errors.append(f"README missing protocol claim: {display}")
        entry = entries.get(protocol_id)
        if not entry or not entry.get("public"):
            errors.append(f"README protocol claim is not public in matrix: {display}")

    return errors


def main() -> None:
    errors = validate_protocol_matrix()
    if errors:
        print("ERROR: protocol matrix validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK: protocol matrix validated.")


if __name__ == "__main__":
    main()

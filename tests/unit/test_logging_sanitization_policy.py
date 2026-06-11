# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression checks for sensitive converter logging."""

from __future__ import annotations

import ast
import logging
import time
from pathlib import Path
from typing import Any, cast

import pytest

from configstream.converters.singbox import to_singbox_outbound
from configstream.dns_batch_resolver import BatchDNSResolver
from configstream.models import Proxy
from configstream.parsers.extraction import extract_config_lines
from configstream.parsers.openvpn import parse_openvpn
from configstream.parsers.shadowsocks import parse_ss
from configstream.security import honeypot
from configstream.security import rules as security_rules
from configstream.security.rules import validate_address
from configstream.test_cache import TestResultCache
from configstream.tools.vwarp import _sanitize_process_output

REPO_ROOT = Path(__file__).resolve().parents[2]
HIGH_RISK_LOGGING_PATHS = [
    REPO_ROOT / "src/configstream/dns_batch_resolver.py",
    REPO_ROOT / "src/configstream/security/honeypot.py",
    REPO_ROOT / "src/configstream/security/rules.py",
    REPO_ROOT / "src/configstream/test_cache.py",
    *sorted((REPO_ROOT / "src/configstream/tools/vwarp").glob("*.py")),
    *sorted((REPO_ROOT / "src/configstream/converters").glob("*.py")),
    *sorted((REPO_ROOT / "src/configstream/parsers").glob("*.py")),
]
LOG_METHODS = {"debug", "info", "warning", "error", "critical", "exception", "log"}
SENSITIVE_LOG_NAMES = {
    "address",
    "candidate",
    "config",
    "decoded",
    "details",
    "dropped_samples",
    "e",
    "err",
    "error",
    "exc",
    "host",
    "host_info",
    "hostname",
    "key",
    "line",
    "pass",
    "password",
    "payload",
    "proxy",
    "pwd",
    "raw",
    "response",
    "sample",
    "samples",
    "secret",
    "source",
    "source_url",
    "stderr",
    "stdout",
    "token",
    "uri",
    "url",
    "user_info",
    "uuid",
}
SAFE_LOG_CALLS = {
    "SecurityValidator.sanitize_log_message",
    "_safe_log_text",
    "_safe_proxy_ref",
    "_safe_source_ref",
    "_sanitize_process_output",
    "len",
    "str",
    "int",
}


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _referenced_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            names.add(child.attr)
    return names


def _is_safe_log_arg(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.Call):
        return _call_name(node.func) in SAFE_LOG_CALLS
    return False


def _iter_logger_calls(tree: ast.AST):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in LOG_METHODS:
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id not in {"logger", "log"}:
            continue
        if node.args:
            yield node


def test_singbox_missing_uuid_log_masks_endpoint(caplog) -> None:
    proxy = Proxy(
        config="vless://missing",
        protocol="vless",
        address="8.8.8.8",
        port=443,
        details={"_source": "https://example.com/sub?token=super-secret"},
    )

    with caplog.at_level(logging.WARNING, logger="configstream.converters.singbox"):
        assert to_singbox_outbound(proxy) is None

    text = caplog.text
    assert "8.8.8.8" not in text
    assert "super-secret" not in text
    assert "vless://[endpoint]" in text
    assert "token=[MASKED]" in text


def test_high_risk_logging_surfaces_use_static_sanitization_policy() -> None:
    violations: list[str] = []

    for path in HIGH_RISK_LOGGING_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative_path = path.relative_to(REPO_ROOT)
        for call in _iter_logger_calls(tree):
            message = call.args[0]
            if isinstance(message, ast.JoinedStr):
                names = sorted(_referenced_names(message) & SENSITIVE_LOG_NAMES)
                if names:
                    violations.append(
                        f"{relative_path}:{call.lineno}: f-string log references {names}"
                    )
            elif isinstance(message, ast.BinOp) and isinstance(message.op, ast.Mod):
                violations.append(
                    f"{relative_path}:{call.lineno}: %-formatted logger message"
                )
            elif (
                isinstance(message, ast.Call)
                and isinstance(message.func, ast.Attribute)
                and message.func.attr == "format"
            ):
                violations.append(
                    f"{relative_path}:{call.lineno}: .format() logger message"
                )

            for arg in call.args[1:]:
                names = sorted(_referenced_names(arg) & SENSITIVE_LOG_NAMES)
                if names and not _is_safe_log_arg(arg):
                    violations.append(
                        f"{relative_path}:{call.lineno}: raw logger argument references {names}"
                    )

    assert violations == []


@pytest.mark.asyncio
async def test_dns_failure_log_masks_hostname_and_exception(caplog) -> None:
    class FailingResolver:
        async def query(self, hostname: str, record_type: str) -> list[object]:
            raise RuntimeError(
                f"lookup failed for {hostname} with token=super-secret at 8.8.8.8"
            )

    resolver = object.__new__(BatchDNSResolver)
    resolver.timeout = 0.1
    resolver.resolver = cast(Any, FailingResolver())

    with caplog.at_level(logging.DEBUG, logger="configstream.dns_batch_resolver"):
        result = await resolver._resolve_one("8.8.8.8.example?token=super-secret")

    assert result is None
    text = caplog.text
    assert "super-secret" not in text
    assert "8.8.8.8" not in text
    assert "token=[MASKED]" in text
    assert "[IP]" in text


def test_vwarp_process_output_sanitizer_masks_and_bounds_output() -> None:
    raw = b"token=super-secret endpoint=8.8.8.8 " + b" ".join([b"process-line"] * 300)

    text = _sanitize_process_output(raw, limit=100)

    assert "super-secret" not in text
    assert "8.8.8.8" not in text
    assert "token=[MASKED]" in text
    assert "[IP]" in text
    assert text.endswith("...[truncated]")
    assert len(text) <= 114


def test_security_rules_address_logs_are_sanitized(monkeypatch, caplog) -> None:
    monkeypatch.setattr(security_rules._APP_SETTINGS_CACHE, "ALLOW_PRIVATE_IPS", False)

    with caplog.at_level(logging.WARNING, logger="configstream.security.rules"):
        validate_address("10.0.0.1", frozenset())

    text = caplog.text
    assert "10.0.0.1" not in text
    assert "[IP]" in text


@pytest.mark.asyncio
async def test_honeypot_logs_sanitize_host_and_exception(monkeypatch, caplog) -> None:
    async def failing_reputation(host: str) -> dict[str, object]:
        raise RuntimeError(f"reputation failed for {host} token=super-secret")

    monkeypatch.setattr(honeypot, "check_ip_reputation", failing_reputation)

    with caplog.at_level(logging.ERROR, logger="configstream.security.honeypot"):
        assert await honeypot.is_honeypot("8.8.8.8?token=super-secret") is False

    text = caplog.text
    assert "8.8.8.8" not in text
    assert "super-secret" not in text
    assert "[IP]" in text
    assert "token=[MASKED]" in text


def test_test_cache_endpoint_logs_are_sanitized(caplog) -> None:
    proxy = Proxy(
        config="vless://example",
        protocol="vless",
        address="8.8.8.8",
        port=443,
    )
    cache = object.__new__(TestResultCache)
    cast(Any, cache).db_path = None
    cache.ttl_seconds = 3600
    cache._cache = {
        cache._compute_hash(proxy.config): {
            "tested_at": time.time(),
            "is_working": True,
        }
    }

    with caplog.at_level(logging.DEBUG, logger="configstream.test_cache"):
        assert cache.get(proxy) is proxy

    text = caplog.text
    assert "8.8.8.8" not in text
    assert "[IP]" in text


def test_shadowsocks_parser_drop_log_does_not_leak_config(caplog) -> None:
    config = "ss://ss:super-secret@8.8.8.8:443#token=super-secret"

    with caplog.at_level(logging.DEBUG, logger="configstream.parsers.shadowsocks"):
        assert parse_ss(config) is None

    text = caplog.text
    assert "super-secret" not in text
    assert "8.8.8.8" not in text


def test_openvpn_parser_invalid_host_log_is_sanitized(caplog) -> None:
    config = "client\ndev tun\nremote 8.8.8.8?token=super-secret 1194\n"

    with caplog.at_level(logging.WARNING, logger="configstream.parsers.openvpn"):
        assert parse_openvpn(config) is None

    text = caplog.text
    assert "super-secret" not in text
    assert "8.8.8.8" not in text
    assert "token=[MASKED]" in text
    assert "[IP]" in text


def test_extraction_drop_samples_are_sanitized(caplog) -> None:
    payload = "8.8.8.8:99999:super-secret\n"

    with caplog.at_level(logging.WARNING, logger="configstream.parsers.extraction"):
        configs, drop_stats = extract_config_lines(payload)

    assert configs == []
    assert drop_stats
    text = caplog.text
    assert "super-secret" not in text
    assert "8.8.8.8" not in text
    assert "[dropped_line]" in text

# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[3] / "tools" / "dns_scanner.py"
SPEC = importlib.util.spec_from_file_location("dns_scanner", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
dns_scanner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dns_scanner)


def test_dns_scanner_import() -> None:
    assert hasattr(dns_scanner, "test_dns")
    assert hasattr(dns_scanner, "scan_cidrs")


@pytest.mark.asyncio
async def test_test_dns_requires_successful_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeDNSError(Exception):
        pass

    class Resolver:
        async def query(self, _domain: str, _record_type: str) -> list[object]:
            raise FakeDNSError(4, "not found")

    monkeypatch.setattr(dns_scanner.aiodns.error, "DNSError", FakeDNSError)
    monkeypatch.setattr(
        dns_scanner.aiodns,
        "DNSResolver",
        lambda **_kwargs: Resolver(),
    )

    ip, success, latency = await dns_scanner.test_dns("192.0.2.53", "example.com")

    assert ip == "192.0.2.53"
    assert success is False
    assert latency == 0.0


@pytest.mark.asyncio
async def test_test_dns_accepts_nonempty_a_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Resolver:
        async def query(self, _domain: str, _record_type: str) -> list[object]:
            return [object()]

    monkeypatch.setattr(
        dns_scanner.aiodns,
        "DNSResolver",
        lambda **_kwargs: Resolver(),
    )

    _ip, success, latency = await dns_scanner.test_dns("192.0.2.53", "example.com")

    assert success is True
    assert latency >= 0.0


@pytest.mark.asyncio
@pytest.mark.parametrize("concurrency", [0, -1, dns_scanner.CHUNK_SIZE + 1])
async def test_scan_rejects_invalid_concurrency(
    tmp_path: Path,
    concurrency: int,
) -> None:
    with pytest.raises(ValueError, match="concurrency"):
        await dns_scanner.scan_cidrs(
            [], concurrency=concurrency, output_file=str(tmp_path / "out.txt")
        )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, 100), ("1", 1), (str(dns_scanner.CHUNK_SIZE), dns_scanner.CHUNK_SIZE)],
)
def test_parse_concurrency_accepts_bounded_values(
    raw: str | None, expected: int
) -> None:
    assert dns_scanner._parse_concurrency(raw) == expected


@pytest.mark.parametrize("raw", ["0", "-1", "abc", str(dns_scanner.CHUNK_SIZE + 1)])
def test_parse_concurrency_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(SystemExit, match="concurrency"):
        dns_scanner._parse_concurrency(raw)

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for the repository audit/hardening pass.

Each test pins a specific defect that was fixed:
  * Go tester latency coercion on untrusted subprocess output.
  * sing-box urltest group referencing the final (uniquified) tag.
  * v2ray JSON parser robustness against non-string ciphers / nested input.
  * lab config outbound-count and nesting-depth DoS bounds.
"""

import pytest

from configstream.models import Proxy
from configstream.testers.go_tester.manager import _coerce_latency
from configstream.parsers.generic import parse_v2ray_json


class TestCoerceLatency:
    def test_valid_numeric(self) -> None:
        assert _coerce_latency(12) == 12.0
        assert _coerce_latency(3.5) == 3.5
        assert _coerce_latency("42") == 42.0

    def test_none_returns_none(self) -> None:
        assert _coerce_latency(None) is None

    def test_non_numeric_string_returns_none(self) -> None:
        # Previously float("n/a") raised ValueError and aborted the whole batch.
        assert _coerce_latency("n/a") is None

    def test_bool_is_not_latency(self) -> None:
        assert _coerce_latency(True) is None
        assert _coerce_latency(False) is None

    def test_nan_and_inf_rejected(self) -> None:
        assert _coerce_latency(float("nan")) is None
        assert _coerce_latency(float("inf")) is None
        assert _coerce_latency("inf") is None

    def test_container_returns_none(self) -> None:
        assert _coerce_latency([1, 2]) is None
        assert _coerce_latency({"a": 1}) is None


def _vless_proxy(address: str, uuid: str, remarks: str) -> Proxy:
    return Proxy(
        config=f"vless://{address}:443#{remarks}",
        protocol="vless",
        address=address,
        port=443,
        uuid=uuid,
        remarks=remarks,
        country_code="US",
        is_working=True,
        details={"tls": "tls", "sni": address},
    )


class TestSingboxUrltestTagUniqueness:
    def test_duplicate_remarks_get_unique_urltest_members(self) -> None:
        from configstream.generators.singbox import SingBoxGenerator

        # Two proxies with an identical remark force tag uniquification.
        proxies = [
            _vless_proxy("1.1.1.1", "123e4567-e89b-42d3-a456-426614174001", "DUP"),
            _vless_proxy("2.2.2.2", "123e4567-e89b-42d3-a456-426614174002", "DUP"),
        ]

        doc = SingBoxGenerator().generate(proxies)
        outbounds = doc["outbounds"] if isinstance(doc, dict) else doc

        urltest = next(o for o in outbounds if o.get("type") == "urltest")
        members = urltest["outbounds"]
        # Two proxies -> two distinct urltest members, all pointing at real tags.
        assert len(members) == len(set(members)), members
        real_tags = {
            o.get("tag")
            for o in outbounds
            if o.get("type") not in ("urltest", "selector")
        }
        for tag in members:
            assert tag in real_tags, f"urltest references missing tag {tag!r}"
        assert len(members) == 2, members


class TestV2rayJsonRobustness:
    def test_non_string_cipher_does_not_raise(self) -> None:
        # A non-string method/cipher previously raised AttributeError at
        # method.lower() and escaped the dispatcher's narrow except clause.
        config = (
            '{"outbounds":[{"protocol":"ss","settings":{"servers":'
            '[{"address":"1.2.3.4","port":8388,"password":"x","method":123}]}}]}'
        )
        # Must not raise; returns None or a Proxy, never an unhandled exception.
        result = parse_v2ray_json(config)
        assert result is None or isinstance(result, Proxy)

    def test_non_object_top_level_returns_none(self) -> None:
        assert parse_v2ray_json("[1, 2, 3]") is None

    def test_garbage_returns_none(self) -> None:
        assert parse_v2ray_json("{not json") is None


class TestAtomicWriteDurability:
    def test_write_text_fsyncs_parent_dir(self, tmp_path, monkeypatch) -> None:
        # The rename must be made durable by fsyncing the parent directory,
        # not just the file contents.
        import configstream.utils as utils

        fsynced_dirs = []
        real_fsync = utils.os.fsync
        real_open = utils.os.open

        opened_dir_fds = {}

        def tracking_open(path, flags, *args, **kwargs) -> int:
            fd = real_open(path, flags, *args, **kwargs)
            opened_dir_fds[fd] = path
            return fd

        def tracking_fsync(fd):
            if fd in opened_dir_fds:
                fsynced_dirs.append(opened_dir_fds[fd])
            return real_fsync(fd)

        monkeypatch.setattr(utils.os, "open", tracking_open)
        monkeypatch.setattr(utils.os, "fsync", tracking_fsync)

        target = tmp_path / "sub" / "out.json"
        utils.AtomicFileWriter.write_text(target, '{"ok": true}')

        assert target.read_text() == '{"ok": true}'
        # The parent directory must have been fsynced at least once.
        assert str(target.parent) in fsynced_dirs

    def test_write_text_content_roundtrip(self, tmp_path) -> None:
        import configstream.utils as utils

        target = tmp_path / "data.txt"
        utils.AtomicFileWriter.write_text(target, "héllo\nworld")
        assert target.read_text(encoding="utf-8") == "héllo\nworld"


class TestLabConfigBounds:
    @pytest.mark.asyncio
    async def test_too_many_outbounds_rejected(self) -> None:
        from fastapi import HTTPException
        from configstream.server.routes.lab import (
            _validate_and_build_lab_config,
            LAB_MAX_OUTBOUND_NODES,
        )

        config = {
            "outbounds": [
                {"type": "http", "server": "1.1.1.1", "server_port": 80}
                for _ in range(LAB_MAX_OUTBOUND_NODES + 1)
            ]
        }
        with pytest.raises(HTTPException) as exc:
            await _validate_and_build_lab_config(config)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_excessive_nesting_rejected(self) -> None:
        from fastapi import HTTPException
        from configstream.server.routes.lab import (
            _validate_and_build_lab_config,
            LAB_MAX_NESTING_DEPTH,
        )

        # Build a chain nested deeper than the allowed limit.
        inner: dict = {"type": "direct"}
        node = inner
        for _ in range(LAB_MAX_NESTING_DEPTH + 3):
            node = {"type": "direct", "detour": node}
        config = {"outbounds": [node]}

        with pytest.raises(HTTPException) as exc:
            await _validate_and_build_lab_config(config)
        assert exc.value.status_code == 400


class TestOversizedLineDrain:
    """`_drain_oversized_line` must always make forward progress.

    A `readline()` that overruns the stream limit is recovered by discarding
    bytes up to the next newline. Retrying `readuntil` blindly would hit the
    identical stuck buffer forever; `LimitOverrunError.consumed` reports how
    many leading bytes are confirmed separator-free, so discarding exactly
    those bytes guarantees the loop advances.
    """

    @pytest.mark.asyncio
    async def test_drain_consumes_bytes_and_stops_spinning(self) -> None:
        import asyncio
        from configstream.testers.go_tester.manager import GoBatchTester

        calls: dict[str, int] = {"readuntil": 0, "readexactly": 0}

        class FakeStream:
            """Overruns twice (reporting consumable bytes), then succeeds."""

            async def readuntil(self, sep: bytes) -> bytes:
                calls["readuntil"] += 1
                if calls["readuntil"] <= 2:
                    raise asyncio.LimitOverrunError("too long", 64)
                return b"tail\n"

            async def readexactly(self, n: int) -> bytes:
                calls["readexactly"] += 1
                assert n == 64, "must discard exactly the consumed-byte count"
                return b"x" * n

        tester = GoBatchTester.__new__(GoBatchTester)
        tester._proc = type("P", (), {"stdout": FakeStream()})()

        assert await tester._drain_oversized_line() is True
        # Both overruns discarded bytes rather than spinning on the same buffer.
        assert calls["readexactly"] == 2
        assert calls["readuntil"] == 3

    @pytest.mark.asyncio
    async def test_drain_reports_eof(self) -> None:
        import asyncio
        from configstream.testers.go_tester.manager import GoBatchTester

        class EofStream:
            async def readuntil(self, sep: bytes) -> bytes:
                raise asyncio.IncompleteReadError(b"", None)

        tester = GoBatchTester.__new__(GoBatchTester)
        tester._proc = type("P", (), {"stdout": EofStream()})()

        assert await tester._drain_oversized_line() is False

    @pytest.mark.asyncio
    async def test_drain_bails_out_when_nothing_consumable(self) -> None:
        """A zero `consumed` count must not loop forever."""
        import asyncio
        from configstream.testers.go_tester.manager import GoBatchTester

        class StuckStream:
            async def readuntil(self, sep: bytes) -> bytes:
                raise asyncio.LimitOverrunError("stuck", 0)

        tester = GoBatchTester.__new__(GoBatchTester)
        tester._proc = type("P", (), {"stdout": StuckStream()})()

        assert await tester._drain_oversized_line() is False

import hashlib
import asyncio
from pathlib import Path

import pytest

from configstream.tools.vwarp import (
    VwarpTool,
    PSIPHON_COUNTRY_CODES,
    MASQUE_NOIZE_PRESETS,
    ATOMICNOIZE_PRESETS,
    DEFAULT_WARP_ENDPOINT,
)
from configstream.tools.vwarp.tunnel import VwarpTunnel
from configstream.tools.vwarp import binary as vwarp_binary
from configstream.tools.vwarp.binary import _validate_download_digest


def test_key_validation():
    tool = VwarpTool()
    valid_key = "a" * 45
    assert tool.validate_warp_key(valid_key) is True
    invalid_key = "short"
    assert tool.validate_warp_key(invalid_key) is False


def test_build_vwarp_config_defaults():
    config = VwarpTool.build_vwarp_config()
    assert config["bind"] == "127.0.0.1:8086"
    assert config["endpoint"] == DEFAULT_WARP_ENDPOINT
    assert config["dns"] == "1.1.1.1"
    assert config["masque"]["enabled"] is False
    assert config["wireguard"]["enabled"] is True
    assert config["psiphon"]["enabled"] is False
    assert "key" not in config
    assert "proxy" not in config


def test_tunnel_probe_host_maps_unspecified_binds_to_loopback():
    assert VwarpTunnel._probe_host_for_bind("") == "127.0.0.1"
    assert VwarpTunnel._probe_host_for_bind("0.0.0.0") == "127.0.0.1"
    assert VwarpTunnel._probe_host_for_bind("::") == "127.0.0.1"
    assert VwarpTunnel._probe_host_for_bind("localhost") == "localhost"
    assert VwarpTunnel._probe_host_for_bind("192.0.2.10") == "192.0.2.10"


def test_build_vwarp_config_masque_preset():
    for preset_name in MASQUE_NOIZE_PRESETS:
        config = VwarpTool.build_vwarp_config(masque_preset=preset_name)
        assert config["masque"]["enabled"] is True
        assert config["masque"]["preferred"] is True
        assert "Jc" in config["masque"]["config"]
        assert (
            config["masque"]["config"]["Jc"] == MASQUE_NOIZE_PRESETS[preset_name]["Jc"]
        )


def test_build_vwarp_config_atomicnoize_preset():
    for preset_name in ATOMICNOIZE_PRESETS:
        config = VwarpTool.build_vwarp_config(atomicnoize_preset=preset_name)
        an = config["wireguard"]["atomicnoize"]
        assert "Jc" in an
        assert an["Jc"] == ATOMICNOIZE_PRESETS[preset_name]["Jc"]


def test_build_vwarp_config_psiphon():
    config = VwarpTool.build_vwarp_config(psiphon_country="US")
    assert config["psiphon"]["enabled"] is True
    assert config["psiphon"]["country"] == "US"


def test_build_vwarp_config_psiphon_case_insensitive():
    config = VwarpTool.build_vwarp_config(psiphon_country="de")
    assert config["psiphon"]["country"] == "DE"


def test_build_vwarp_config_proxy():
    config = VwarpTool.build_vwarp_config(proxy="socks5://127.0.0.1:1080")
    assert config["proxy"] == "socks5://127.0.0.1:1080"


def test_build_vwarp_config_full():
    config = VwarpTool.build_vwarp_config(
        bind="0.0.0.0:9090",
        endpoint="162.159.195.1:500",
        key="test-warp-key",
        dns="8.8.8.8",
        masque_preset="heavy",
        atomicnoize_preset="medium",
        psiphon_country="JP",
        proxy="socks5://10.0.0.1:1080",
    )
    assert config["bind"] == "0.0.0.0:9090"
    assert config["endpoint"] == "162.159.195.1:500"
    assert config["key"] == "test-warp-key"
    assert config["dns"] == "8.8.8.8"
    assert config["masque"]["enabled"] is True
    assert config["masque"]["config"]["SNIFragmentation"] is True

    # Robust check for I1
    an = config["wireguard"]["atomicnoize"]
    assert (
        "I1" in an
    ), f"I1 missing from atomicnoize preset 'medium'. Available keys: {list(an.keys())}"
    assert an["I1"] == "<b 0c0d0e0f>"

    assert config["psiphon"]["country"] == "JP"
    assert config["proxy"] == "socks5://10.0.0.1:1080"


def test_psiphon_country_codes_completeness():
    assert "US" in PSIPHON_COUNTRY_CODES
    assert "DE" in PSIPHON_COUNTRY_CODES
    assert "JP" in PSIPHON_COUNTRY_CODES
    assert "IR" not in PSIPHON_COUNTRY_CODES
    assert len(PSIPHON_COUNTRY_CODES) >= 29


def test_download_digest_requires_exact_sha256_pin():
    content = b"verified vwarp archive"
    digest = hashlib.sha256(content).hexdigest()

    assert _validate_download_digest(content, digest) is True
    assert _validate_download_digest(content + b"tampered", digest) is False
    assert _validate_download_digest(content, None) is False
    assert _validate_download_digest(content, "not-a-digest") is False


def test_unknown_architecture_does_not_fall_back_to_amd64(monkeypatch):
    monkeypatch.setattr(vwarp_binary.platform, "machine", lambda: "riscv64")
    monkeypatch.delenv("VWARP_URL", raising=False)
    monkeypatch.delenv("VWARP_SHA256", raising=False)

    with pytest.raises(ValueError, match="unsupported Vwarp architecture"):
        vwarp_binary._get_download_spec()


def test_download_override_requires_https(monkeypatch):
    monkeypatch.setenv("VWARP_URL", "http://example.test/vwarp.zip")
    monkeypatch.setenv("VWARP_SHA256", "a" * 64)

    with pytest.raises(ValueError, match="absolute HTTPS"):
        vwarp_binary._get_download_spec()


class _StreamResponse:
    def __init__(self, chunks: list[bytes], content_length: str | None = None):
        self._chunks = chunks
        self.headers = {}
        if content_length is not None:
            self.headers["content-length"] = content_length

    def raise_for_status(self) -> None:
        return None

    async def aiter_bytes(self):
        for chunk in self._chunks:
            yield chunk


class _StreamContext:
    def __init__(self, response: _StreamResponse):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _StreamClient:
    def __init__(self, response: _StreamResponse):
        self.response = response

    def stream(self, method: str, url: str):
        assert method == "GET"
        assert url == "https://example.test/vwarp.zip"
        return _StreamContext(self.response)


@pytest.mark.asyncio
async def test_vwarp_download_enforces_streaming_size_limit(monkeypatch):
    monkeypatch.setattr(vwarp_binary, "MAX_VWARP_ARCHIVE_BYTES", 4)
    client = _StreamClient(_StreamResponse([b"123", b"45"]))

    with pytest.raises(ValueError, match="safety limit"):
        await vwarp_binary._download_archive(client, "https://example.test/vwarp.zip")


@pytest.mark.asyncio
async def test_vwarp_verification_kills_timed_out_process(monkeypatch):
    class _Process:
        returncode = None
        killed = False
        waited = False

        async def communicate(self):
            await asyncio.sleep(1)
            return b"", b""

        def kill(self):
            self.killed = True

        async def wait(self):
            self.waited = True

    process = _Process()

    async def _create(*args, **kwargs):
        return process

    monkeypatch.setattr(vwarp_binary.asyncio, "create_subprocess_exec", _create)
    monkeypatch.setattr(vwarp_binary, "VERIFY_TIMEOUT_SECONDS", 0.001)

    assert await vwarp_binary.verify_binary("/tmp/vwarp") is False
    assert process.killed is True
    assert process.waited is True


def test_install_directory_falls_back_when_user_bin_creation_fails(
    monkeypatch, tmp_path
):
    home = tmp_path / "home"
    preferred = home / ".local" / "bin"
    original_mkdir = Path.mkdir

    monkeypatch.setattr(vwarp_binary.Path, "home", classmethod(lambda cls: home))

    def guarded_mkdir(self, *args, **kwargs):
        if self == preferred:
            raise PermissionError("read-only home")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(vwarp_binary.Path, "mkdir", guarded_mkdir)
    fallback = vwarp_binary._prepare_install_dir()

    assert fallback.is_dir()
    assert fallback != preferred
    assert fallback.name.startswith("configstream-bin-")

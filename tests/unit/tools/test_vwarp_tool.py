from configstream.tools.vwarp import (
    VwarpTool,
    PSIPHON_COUNTRY_CODES,
    MASQUE_NOIZE_PRESETS,
    ATOMICNOIZE_PRESETS,
    DEFAULT_WARP_ENDPOINT,
)
from configstream.tools.vwarp.tunnel import VwarpTunnel


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
    assert "I1" in an, (
        f"I1 missing from atomicnoize preset 'medium'. Available keys: {list(an.keys())}"
    )
    assert an["I1"] == "<b 0c0d0e0f>"

    assert config["psiphon"]["country"] == "JP"
    assert config["proxy"] == "socks5://10.0.0.1:1080"


def test_psiphon_country_codes_completeness():
    assert "US" in PSIPHON_COUNTRY_CODES
    assert "DE" in PSIPHON_COUNTRY_CODES
    assert "JP" in PSIPHON_COUNTRY_CODES
    assert "IR" not in PSIPHON_COUNTRY_CODES
    assert len(PSIPHON_COUNTRY_CODES) >= 29

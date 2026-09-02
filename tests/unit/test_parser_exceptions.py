# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for explicit exception handling across parsers.
Verifies that:
1. Malformed URLs, corrupted base64, invalid JSON, and invalid parameters
   gracefully return None by catching specific expected exceptions.
2. Unexpected exceptions (RuntimeError, KeyboardInterrupt, SystemExit) are NOT swallowed.
"""

import binascii
import json
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from configstream.parsers.vless import parse_vless
from configstream.parsers.vmess import parse_vmess
from configstream.parsers.trojan import parse_trojan
from configstream.parsers.shadowsocks import parse_ss, parse_ss2022
from configstream.parsers.clash_json import parse_clash_json
from configstream.parsers.openvpn import parse_openvpn
from configstream.parsers.others import (
    parse_hysteria,
    parse_hysteria2,
    parse_tuic as parse_tuic_other,
    parse_wireguard,
    parse_xray,
    parse_snell,
    parse_brook,
    parse_juicity,
    parse_ssh,
)
from configstream.parsers.generic import (
    parse_generic_url_scheme,
    parse_naive,
    parse_v2ray_json,
)
from configstream.parsers.decoders import safe_b64_decode, validate_b64_input


class TestExpectedExceptionsReturnNone:
    """Test that malformed/corrupted inputs are caught gracefully and return None."""

    def test_vless_malformed_inputs(self):
        # Missing @
        assert parse_vless("vless://invalid-uuid-without-at-sign") is None
        # Non-numeric port
        assert parse_vless("vless://uuid@host:notaport?type=tcp") is None
        # Invalid IPv6 bracket format
        assert parse_vless("vless://uuid@[unclosed-ipv6:443") is None
        # Missing host
        assert parse_vless("vless://@:443") is None
        # Empty uuid
        assert parse_vless("vless://@host:443") is None

    def test_vmess_malformed_inputs(self):
        # Corrupted base64
        assert parse_vmess("vmess://!!!not-valid-base64@@@") is None
        # Valid base64 but invalid JSON
        bad_json_b64 = "bm90IGEgSlNPTiBvYmplY3Q="  # "not a JSON object"
        assert parse_vmess(f"vmess://{bad_json_b64}") is None
        # Valid base64 JSON but missing required fields
        incomplete_json = "eyJmb28iOiAiYmFyIn0="  # {"foo": "bar"}
        assert parse_vmess(f"vmess://{incomplete_json}") is None
        # Port not an int
        bad_port_json = "eyJhZGQiOiAidGVzdC5jb20iLCAicG9ydCI6ICJub3RhcG9ydCIsICJpZCI6ICJ1dWlkIn0="
        assert parse_vmess(f"vmess://{bad_port_json}") is None

    def test_trojan_malformed_inputs(self):
        # Empty credentials
        assert parse_trojan("trojan://@example.com:443") is None
        # Out of range port
        assert parse_trojan("trojan://password@example.com:999999") is None
        # Missing hostname
        assert parse_trojan("trojan://password@:443") is None

    def test_shadowsocks_malformed_inputs(self):
        # Missing password/credentials
        assert parse_ss("ss://@example.com:8388") is None
        # Invalid method (c3M6cGFzc3dvcmQ= is ss:password)
        assert parse_ss("ss://c3M6cGFzc3dvcmQ=@example.com:8388") is None
        # Out of range port
        assert parse_ss("ss://YWVzLTEyOC1nY206cGFzc3dvcmQ=@example.com:999999") is None
        # Non-numeric port
        assert parse_ss("ss://YWVzLTEyOC1nY206cGFzc3dvcmQ=@example.com:notaport") is None
        # SS2022 invalid
        assert parse_ss2022("ss2022://invalid-ss2022-url") is None

    def test_clash_json_malformed_inputs(self):
        # Non-JSON string
        assert parse_clash_json("not json") is None
        # JSON array instead of dict
        assert parse_clash_json("[1, 2, 3]") is None
        # Missing mandatory fields
        assert parse_clash_json(json.dumps({"name": "test"})) is None
        # Invalid port
        assert parse_clash_json(json.dumps({"name": "test", "type": "vmess", "server": "1.1.1.1", "port": 999999})) is None

    def test_openvpn_malformed_inputs(self):
        # No client directive
        assert parse_openvpn("remote 1.1.1.1 1194\nproto udp") is None
        # Invalid port
        assert parse_openvpn("client\nremote 1.1.1.1 notaport\nproto udp") is None
        # Invalid hostname format
        assert parse_openvpn("client\nremote invalid!hostname!* 1194\nproto udp") is None

    def test_generic_and_others_malformed_inputs(self):
        assert parse_generic_url_scheme("http://") is None
        assert parse_naive("naive+https://") is None
        assert parse_v2ray_json("{invalid json") is None
        assert parse_hysteria("hysteria://") is None
        assert parse_hysteria2("hysteria2://") is None
        assert parse_wireguard("wireguard://") is None


class TestUnexpectedExceptionsNotSwallowed:
    """Test that unexpected exceptions (RuntimeError, SystemExit, KeyboardInterrupt) are NOT swallowed."""

    @pytest.mark.parametrize(
        "module_path,parser_func,valid_config",
        [
            (
                "configstream.parsers.vless",
                parse_vless,
                "vless://a3a2a1a0-1234-5678-9abc-def012345678@example.com:443?type=tcp&security=none#test",
            ),
            (
                "configstream.parsers.vmess",
                parse_vmess,
                "vmess://eyJhZGQiOiAiMS4xLjEuMSIsICJwb3J0IjogNDQzLCAiaWQiOiAiYTNhMmExYTAtMTIzNC01Njc4LTlhYmMtZGVmMDEyMzQ1Njc4IiwgInBzIjogInRlc3QifQ==",
            ),
            (
                "configstream.parsers.trojan",
                parse_trojan,
                "trojan://password123@example.com:443#test",
            ),
            (
                "configstream.parsers.shadowsocks",
                parse_ss,
                "ss://YWVzLTEyOC1nY206cGFzc3dvcmRAMS4xLjEuMTo4Mzg4#test",
            ),
            (
                "configstream.parsers.shadowsocks",
                parse_ss2022,
                "ss2022://YWVzLTEyOC1nY206cGFzc3dvcmRAMS4xLjEuMTo4Mzg4#test",
            ),
            (
                "configstream.parsers.clash_json",
                parse_clash_json,
                json.dumps(
                    {
                        "name": "test",
                        "type": "vmess",
                        "server": "1.1.1.1",
                        "port": 443,
                        "uuid": "a3a2a1a0-1234-5678-9abc-def012345678",
                    }
                ),
            ),
            (
                "configstream.parsers.openvpn",
                parse_openvpn,
                "client\ndev tun\nremote 1.1.1.1 1194\nproto udp",
            ),
        ],
    )
    def test_runtime_error_propagates(self, module_path, parser_func, valid_config):
        target = f"{module_path}.normalize_proxy_details" if hasattr(__import__(module_path, fromlist=["normalize_proxy_details"]), "normalize_proxy_details") else f"{module_path}.Proxy"
        with patch(target, side_effect=RuntimeError("unexpected crash")):
            with pytest.raises(RuntimeError, match="unexpected crash"):
                parser_func(valid_config)

    @pytest.mark.parametrize(
        "module_path,parser_func,valid_config",
        [
            (
                "configstream.parsers.vless",
                parse_vless,
                "vless://a3a2a1a0-1234-5678-9abc-def012345678@example.com:443?type=tcp#test",
            ),
            (
                "configstream.parsers.vmess",
                parse_vmess,
                "vmess://eyJhZGQiOiAiMS4xLjEuMSIsICJwb3J0IjogNDQzLCAiaWQiOiAiYTNhMmExYTAtMTIzNC01Njc4LTlhYmMtZGVmMDEyMzQ1Njc4IiwgInBzIjogInRlc3QifQ==",
            ),
            (
                "configstream.parsers.trojan",
                parse_trojan,
                "trojan://password123@example.com:443#test",
            ),
            (
                "configstream.parsers.shadowsocks",
                parse_ss,
                "ss://YWVzLTEyOC1nY206cGFzc3dvcmRAMS4xLjEuMTo4Mzg4#test",
            ),
        ],
    )
    def test_keyboard_interrupt_propagates(self, module_path, parser_func, valid_config):
        target = f"{module_path}.normalize_proxy_details"
        with patch(target, side_effect=KeyboardInterrupt()):
            with pytest.raises(KeyboardInterrupt):
                parser_func(valid_config)


class TestExplicitValidationErrorHandling:
    """Test that pydantic.ValidationError during model instantiation is caught gracefully."""

    def test_vless_validation_error_caught(self):
        with patch("configstream.parsers.vless.Proxy", side_effect=ValidationError.from_exception_data(
            title="Proxy", line_errors=[]
        )):
            assert parse_vless("vless://a3a2a1a0-1234-5678-9abc-def012345678@example.com:443?type=tcp#test") is None

    def test_vmess_validation_error_caught(self):
        with patch("configstream.parsers.vmess.Proxy", side_effect=ValidationError.from_exception_data(
            title="Proxy", line_errors=[]
        )):
            assert parse_vmess("vmess://eyJhZGQiOiAiMS4xLjEuMSIsICJwb3J0IjogNDQzLCAiaWQiOiAiYTNhMmExYTAtMTIzNC01Njc4LTlhYmMtZGVmMDEyMzQ1Njc4In0=") is None

    def test_trojan_validation_error_caught(self):
        with patch("configstream.parsers.trojan.Proxy", side_effect=ValidationError.from_exception_data(
            title="Proxy", line_errors=[]
        )):
            assert parse_trojan("trojan://password123@example.com:443#test") is None

    def test_shadowsocks_validation_error_caught(self):
        with patch("configstream.parsers.shadowsocks.Proxy", side_effect=ValidationError.from_exception_data(
            title="Proxy", line_errors=[]
        )):
            assert parse_ss("ss://YWVzLTEyOC1nY206cGFzc3dvcmRAMS4xLjEuMTo4Mzg4#test") is None

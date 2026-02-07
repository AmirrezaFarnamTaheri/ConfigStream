import pytest
import json
from configstream.parsers.clash_json import parse_clash_json

def test_parse_clash_json_valid_vmess():
    config = json.dumps({
        "name": "Test VMess",
        "type": "vmess",
        "server": "example.com",
        "port": 443,
        "uuid": "1234-5678",
        "alterId": 0,
        "cipher": "auto",
        "tls": True
    })
    proxy = parse_clash_json(config)
    assert proxy is not None
    assert proxy.protocol == "vmess"
    assert proxy.address == "example.com"
    assert proxy.port == 443
    assert proxy.uuid == "1234-5678"
    assert proxy.remarks == "Test VMess"

def test_parse_clash_json_invalid_json():
    assert parse_clash_json("{invalid_json}") is None

def test_parse_clash_json_missing_fields():
    assert parse_clash_json(json.dumps({"name": "No Type"})) is None
    assert parse_clash_json(json.dumps({"type": "vmess", "server": "example.com"})) is None # Missing name

def test_parse_clash_json_shadowsocks():
    config = json.dumps({
        "name": "Test SS",
        "type": "ss",
        "server": "ss.example.com",
        "port": 8388,
        "cipher": "aes-256-gcm",
        "password": "password123"
    })
    proxy = parse_clash_json(config)
    assert proxy is not None
    assert proxy.protocol == "shadowsocks"
    assert proxy.details["password"] == "password123"
    assert proxy.details["method"] == "aes-256-gcm"

def test_parse_clash_json_shadowsocks_no_password():
    config = json.dumps({
        "name": "Test SS No Pass",
        "type": "ss",
        "server": "ss.example.com",
        "port": 8388,
        "cipher": "aes-256-gcm"
    })
    assert parse_clash_json(config) is None

def test_parse_clash_json_wireguard():
    config = json.dumps({
        "name": "Test WG",
        "type": "wireguard",
        "server": "wg.example.com",
        "port": 51820,
        "private-key": "someprivatekey",
        "ip": "10.0.0.2"
    })
    proxy = parse_clash_json(config)
    assert proxy is not None
    assert proxy.protocol == "wireguard"
    assert proxy.details["private_key"] == "someprivatekey"

def test_parse_clash_json_wireguard_camelCase():
    config = json.dumps({
        "name": "Test WG Camel",
        "type": "wireguard",
        "server": "wg.example.com",
        "port": 51820,
        "privateKey": "someprivatekey2",
        "ip": "10.0.0.2"
    })
    proxy = parse_clash_json(config)
    assert proxy is not None
    assert proxy.details["private_key"] == "someprivatekey2"

def test_parse_clash_json_wireguard_missing_key():
    config = json.dumps({
        "name": "Test WG Missing",
        "type": "wireguard",
        "server": "wg.example.com",
        "port": 51820
    })
    assert parse_clash_json(config) is None

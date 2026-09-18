# SPDX-License-Identifier: AGPL-3.0-or-later
"""Execute browser exporters and validate their payloads with backend contracts."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest
from configstream.output.client_formats import validate_xray_config

ROOT = Path(__file__).resolve().parents[2]


def test_lab_exports_match_current_core_contracts() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node unavailable")
    script = """
import {singboxOutboundToXray, singboxOutboundToClash} from './frontend/assets/js/lab/exporters.js';
const base = {tag:'test',server:'example.com',server_port:443,uuid:'123e4567-e89b-12d3-a456-426614174000',password:'test-password',method:'aes-128-gcm',tls:{enabled:true,insecure:true,server_name:'example.com'}};
const outbounds = ['vless','vmess','trojan','shadowsocks','socks','http'].map(type => singboxOutboundToXray({...base,type,tag:type}));
const xhttp = singboxOutboundToXray({...base,type:'vless',tag:'xhttp',transport:{type:'http',path:'/xhttp',host:['edge.example','backup.example']}});
const httpupgrade = singboxOutboundToXray({...base,type:'vless',tag:'httpupgrade',transport:{type:'httpupgrade',path:'/upgrade',host:['upgrade.example','ignored.example']}});
const plain = singboxOutboundToClash({...base,type:'vless',tls:undefined});
let rejected = false;
try { singboxOutboundToXray({...base,type:'tuic'}); } catch { rejected = true; }
console.log(JSON.stringify({outbounds,xhttp,httpupgrade,plain,rejected}));
"""
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    data = json.loads(result.stdout)
    assert validate_xray_config({"outbounds": data["outbounds"]}) == []
    assert data["xhttp"]["streamSettings"]["xhttpSettings"] == {
        "path": "/xhttp",
        "host": "edge.example",
    }
    assert data["httpupgrade"]["streamSettings"]["httpupgradeSettings"] == {
        "path": "/upgrade",
        "host": "upgrade.example",
    }
    assert data["plain"]["tls"] is False
    assert data["rejected"] is True
    assert all(
        "allowInsecure" not in row["streamSettings"].get("tlsSettings", {})
        for row in data["outbounds"]
    )


def test_cache_keeps_explicit_delta_snapshot_version() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node unavailable")
    script = """
import fs from 'node:fs';
import vm from 'node:vm';
const context = {console, navigator:{}, document:{readyState:'loading',addEventListener(){}}, URL, Date, setTimeout, clearTimeout};
context.window=context;
vm.createContext(context);
vm.runInContext(fs.readFileSync('frontend/assets/js/cache-manager.js','utf8'),context);
const manager=context.cacheManager;
manager._cacheAvailable=true;
let stored;
manager.idb={set:async(key,value)=>{stored=value;}};
await manager.cacheData('https://example.com/api/proxies',[], 'exact-snapshot');
if(stored.version !== 'exact-snapshot') throw new Error('Snapshot identity lost');
"""
    subprocess.run(
        [node, "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )


def test_lab_private_destination_rules_match_backend() -> None:
    from configstream.output.xray_security import (
        requires_transport_security,
        XRAY_PRIVATE_NETWORKS,
        XRAY_PRIVATE_DOMAINS,
    )

    node = shutil.which("node")
    if not node:
        pytest.skip("Node unavailable")
    addresses = [
        "8.8.8.8",
        "public.example.com",
        "::ffff:8.8.8.8",
        "::ffff:10.0.0.1",
        "2001:4860:4860::8888",
    ]
    addresses += [str(network.network_address) for network in XRAY_PRIVATE_NETWORKS]
    addresses += ["host." + domain for domain in XRAY_PRIVATE_DOMAINS]
    script = (
        "import {requiresXrayTransportSecurity as check} from './frontend/assets/js/lab/xray-security.js';console.log(JSON.stringify("
        + json.dumps(addresses)
        + ".map(check)));"
    )
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert json.loads(result.stdout) == [
        requires_transport_security(address) for address in addresses
    ]

def test_lab_singbox_exports_use_113_endpoint_schema() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node unavailable")
    script = r"""
import {
  buildSingboxConfig,
  buildNekoboxLink,
  buildPythonScript,
  buildBashScript
} from './frontend/assets/js/lab/exporters.js';

const raw = {
  log: {level: 'info'},
  outbounds: [
    {
      type: 'vless', tag: 'proxy-chain', server: 'example.com', server_port: 443,
      uuid: '123e4567-e89b-12d3-a456-426614174000', detour: 'warp-out'
    },
    {
      type: 'wireguard', tag: 'warp-out', server: '162.159.192.1', server_port: 2408,
      local_address: ['172.16.0.2/32', 'fd01:db8:85a3::2/128'],
      private_key: 'private', peer_public_key: 'public', reserved: [1, 2, 3], mtu: 1280
    },
    {type: 'block', tag: 'block'}
  ],
  route: {final: 'proxy-chain'}
};

const decode = value => JSON.parse(Buffer.from(value, 'base64').toString('utf8'));
const modern = buildSingboxConfig(raw);
const nekoEncoded = decodeURIComponent(
  buildNekoboxLink(raw).split('nekobox://import-singbox?config=')[1]
);
const pythonScript = buildPythonScript(raw);
const bashScript = buildBashScript(raw);
const pythonMatch = pythonScript.match(/base64\.b64decode\("([^"]+)"\)/);
const bashMatch = bashScript.match(/printf '%s' '([^']+)' \| base64 -d/);
if (!pythonMatch || !bashMatch) throw new Error('Generated runner payload missing');
console.log(JSON.stringify({
  modern,
  nekobox: decode(nekoEncoded),
  python: decode(pythonMatch[1]),
  bash: decode(bashMatch[1])
}));
"""
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    payloads = json.loads(result.stdout)
    for config in payloads.values():
        assert [item["type"] for item in config["outbounds"]] == ["vless"]
        assert config["outbounds"][0]["detour"] == "warp-out"
        assert config["route"]["final"] == "proxy-chain"
        assert len(config["endpoints"]) == 1
        endpoint = config["endpoints"][0]
        assert endpoint["type"] == "wireguard"
        assert endpoint["tag"] == "warp-out"
        assert endpoint["address"] == [
            "172.16.0.2/32",
            "fd01:db8:85a3::2/128",
        ]
        assert "server" not in endpoint
        assert endpoint["peers"] == [
            {
                "address": "162.159.192.1",
                "port": 2408,
                "public_key": "public",
                "allowed_ips": ["0.0.0.0/0", "::/0"],
                "reserved": [1, 2, 3],
            }
        ]


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

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Frontend lab clean-IP consumers must preserve IPv6 and honest evidence status."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_lab_clean_ip_parsing_and_fallback_evidence() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node unavailable")
    code = r"""
import {parseManualCleanIpLine,parsePublishedCleanIp,formatCleanIpEndpoint,handleStep2Next} from './frontend/assets/js/lab/clean-ips.js';
import {state} from './frontend/assets/js/lab/state.js';
const input = {
  valid: parsePublishedCleanIp({ip: '2606:4700:4700::1111', port: 2408}),
  formatted: formatCleanIpEndpoint({ip: '2606:4700:4700::1111', port: 2408}),
  invalidV6: parseManualCleanIpLine('[2001:db8:::1]:443'),
  invalidV4: parseManualCleanIpLine('999.999.999.999:443'),
  invalidPort: parsePublishedCleanIp({ip: '1.1.1.1', port: 65536}),
};
globalThis.document = {
  querySelector: sel => sel === '#cleanIpMethod' ? {value:'auto'} : null,
  getElementById: () => null,
};
globalThis.window = {ROOT_PATH: ''};
globalThis.setTimeout = () => 0;
globalThis.fetch = async () => ({ok:true,json:async () => [
  {ip:'2001:db8:::1',port:443},
  {ip:'2606:4700:4700::1111',port:2408},
  {ip:'1.1.1.1',port:443}
]});
await handleStep2Next();
input.auto = structuredClone(state.cleanIps);
globalThis.fetch = async () => {throw new Error('offline')};
await handleStep2Next();
input.fallback = structuredClone(state.cleanIps);
console.log(JSON.stringify(input));
"""
    completed = subprocess.run(
        [node, "--input-type=module", "-e", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    data = json.loads(completed.stdout)
    assert data["valid"]["ip"] == "2606:4700:4700::1111"
    assert data["valid"]["status"] == "untested"
    assert data["formatted"] == "[2606:4700:4700::1111]:2408"
    assert data["invalidV6"] is None
    assert data["invalidV4"] is None
    assert data["invalidPort"] is None
    assert [row["ip"] for row in data["auto"]] == ["2606:4700:4700::1111", "1.1.1.1"]
    assert all(row["status"] == "untested" for row in data["auto"])
    assert data["fallback"]
    assert all(row["status"] == "untested" for row in data["fallback"])

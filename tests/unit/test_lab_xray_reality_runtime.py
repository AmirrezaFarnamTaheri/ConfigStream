# SPDX-License-Identifier: AGPL-3.0-or-later
"""Browser exporter must reject native-incompatible REALITY transports."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_lab_xray_reality_transport_guard() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node unavailable")
    script = r"""
import {singboxOutboundToXray} from './frontend/assets/js/lab/exporters.js';
const base = {tag:'reality',type:'vless',server:'93.184.216.34',server_port:443,
  uuid:'00000000-0000-0000-0000-00000000f006',
  tls:{enabled:true,server_name:'example.com',reality:{enabled:true,public_key:'fixture-key'}}};
const modes=['raw','tcp','grpc','xhttp','ws','websocket','httpupgrade','kcp','mkcp'];
const outcomes=Object.fromEntries(modes.map(type=>{
  try{return [type,singboxOutboundToXray({...base,transport:{type}}).streamSettings.method]}
  catch(error){return [type,error.message]}
}));
console.log(JSON.stringify(outcomes));
"""
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    outcomes = json.loads(result.stdout)
    assert {k: outcomes[k] for k in ("raw", "tcp", "grpc", "xhttp")} == {
        "raw": "raw",
        "tcp": "raw",
        "grpc": "grpc",
        "xhttp": "xhttp",
    }
    for mode in ("ws", "websocket", "httpupgrade", "kcp", "mkcp"):
        assert "REALITY" in outcomes[mode]

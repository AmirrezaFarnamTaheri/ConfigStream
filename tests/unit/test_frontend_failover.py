# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import cast

import pytest

ROOT = Path(__file__).resolve().parents[2]
FAILOVER_JS = ROOT / "frontend" / "assets" / "js" / "failover.js"


def _run_failover_case(tmp_path: Path, case: str) -> dict[str, object]:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for frontend failover tests")

    script = tmp_path / "failover-test.cjs"
    script.write_text(
        f"""
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync({json.dumps(str(FAILOVER_JS))}, 'utf8');
const calls = [];
const warnings = [];
const session = new Map();
let href = '';

const context = {{
  self: null,
  window: {{
    ROOT_PATH: '/ConfigStream/',
    CS_CONSTANTS: {{
      IPNS_KEY: 'k51qzi5uqu5d-real-key',
      IPFS_GATEWAYS: [
        'https://ipfs.io/ipfs/',
        'https://dweb.link/ipns/'
      ],
    }},
    location: {{
      pathname: '/ConfigStream/proxies.html',
      search: '?token=must-not-leak',
      hash: '#private-state',
      protocol: 'https:',
      host: 'example.test',
      get href() {{ return href; }},
      set href(value) {{ href = value; }},
    }},
    addEventListener: () => {{}},
  }},
  sessionStorage: {{
    getItem: (key) => session.get(key) || null,
    setItem: (key, value) => session.set(key, value),
  }},
  console: {{ warn: (message) => warnings.push(String(message)) }},
  URL,
  AbortController: class {{
    constructor() {{ this.signal = {{}}; }}
    abort() {{}}
  }},
  setTimeout: () => 1,
  clearTimeout: () => {{}},
  fetch: (url, options = {{}}) => {{
    calls.push({{ url, method: options.method || 'GET', mode: options.mode || null }});
    return Promise.resolve({{ ok: url === '/ConfigStream/assets/svg/favicon.svg' || options.method === 'HEAD' }});
  }},
}};
context.window.window = context.window;
context.self = context.window;
vm.createContext(context);
vm.runInContext(source, context);

(async () => {{
  if ({json.dumps(case)} === 'probe') {{
    const ok = await context.window.Failover.checkConnectivity();
    console.log(JSON.stringify({{ ok, calls, href, warnings }}));
    return;
  }}

  if ({json.dumps(case)} === 'placeholder') {{
    context.window.CS_CONSTANTS.IPNS_KEY = 'k51qzi5uqu5d...';
    context.window.Failover.triggerFailover();
    await Promise.resolve();
    console.log(JSON.stringify({{ calls, href, warnings, attempted: session.get('configstream_failover_attempted') }}));
    return;
  }}

  await context.window.Failover.triggerFailover();
  const firstHref = href;
  context.window.Failover.triggerFailover();
  await Promise.resolve();
  console.log(JSON.stringify({{
    calls,
    href,
    firstHref,
    warnings,
    attempted: session.get('configstream_failover_attempted'),
  }}));
}})().catch((error) => {{
  console.error(error);
  process.exit(1);
}});
""",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [node, str(script)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return cast("dict[str, object]", json.loads(completed.stdout))


def test_failover_probe_uses_static_same_origin_asset(tmp_path: Path) -> None:
    result = _run_failover_case(tmp_path, "probe")

    assert result["ok"] is True
    assert result["calls"] == [
        {
            "url": "/ConfigStream/assets/svg/favicon.svg",
            "method": "GET",
            "mode": None,
        }
    ]


def test_failover_preserves_leaf_page_and_prevents_session_loop(
    tmp_path: Path,
) -> None:
    result = _run_failover_case(tmp_path, "trigger")

    assert result["attempted"] == "1"
    assert result["firstHref"] == (
        "https://ipfs.io/ipns/k51qzi5uqu5d-real-key/proxies.html"
    )
    assert result["href"] == result["firstHref"]
    assert "token=" not in str(result["href"])
    assert "private-state" not in str(result["href"])
    assert result["calls"] == [
        {
            "url": (
                "https://ipfs.io/ipns/k51qzi5uqu5d-real-key/"
                "proxies.html"
            ),
            "method": "HEAD",
            "mode": "no-cors",
        }
    ]


def test_failover_skips_placeholder_ipns_key(tmp_path: Path) -> None:
    result = _run_failover_case(tmp_path, "placeholder")

    assert result["attempted"] == "1"
    assert result["href"] == ""
    assert result["calls"] == []
    warnings = cast(list[str], result["warnings"])
    assert any("IPNS_KEY not configured" in item for item in warnings)


def test_failover_gateways_are_allowed_by_page_csp() -> None:
    html = (ROOT / "frontend" / "proxies.html").read_text(encoding="utf-8")
    for origin in ("https://ipfs.io", "https://cloudflare-ipfs.com", "https://dweb.link"):
        assert origin in html

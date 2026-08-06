# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path


def test_evidence_explorer_is_fail_closed_and_does_not_render_raw_configs() -> None:
    html = Path('frontend/evidence.html').read_text(encoding='utf-8')
    script = Path('frontend/assets/js/evidence-explorer.js').read_text(encoding='utf-8')
    assert 'artifact-state.js' in html
    assert 'await artifact.ready' in script
    assert 'if (!artifact.canDistribute())' in script
    assert "artifact.fetchVerifiedJson('proxies.json')" in script
    assert 'fetch(`${root}proxies.json' not in script
    assert 'config_sha256' in script
    assert 'record.config' not in script.replace('record.config)', 'REDACTED')
    assert 'innerHTML' not in script
    assert 'textContent' in script
    assert 'unknown' in script


def test_evidence_page_is_in_build_and_same_origin_smoke() -> None:
    assert 'evidence: resolve(frontendRoot, "evidence.html")' in Path('vite.config.mjs').read_text(encoding='utf-8')
    assert '"evidence.html"' in Path('scripts/frontend_same_origin_smoke.cjs').read_text(encoding='utf-8')

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Automated unit and contract tests for procedural 3D hero node.

Tests cover:
- HTML integration in frontend/index.html (hero section container & deferred script tag)
- Script ordering after trust bootstrap sequence
- DPR clamping (max 1.5)
- Reduced motion preference detection & static rendering gating
- IntersectionObserver offscreen visibility lifecycle controls
- WebGL context loss and restoration handling
- Global disposal hook (window._disposeHeroNode) for deterministic teardown
- Cold Luxury color token compliance
- Node VM runtime execution & lifecycle verification
"""

from __future__ import annotations

import json
import re
import subprocess
import textwrap
from pathlib import Path
import pytest
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"
INDEX_HTML = FRONTEND_DIR / "index.html"
HERO_SCENE_JS = FRONTEND_DIR / "assets" / "js" / "hero-scene.js"


def test_hero_scene_file_exists() -> None:
    """frontend/assets/js/hero-scene.js must exist and be non-empty."""
    assert HERO_SCENE_JS.is_file(), f"File does not exist: {HERO_SCENE_JS}"
    content = HERO_SCENE_JS.read_text(encoding="utf-8")
    assert len(content.strip()) > 100, "hero-scene.js is unexpectedly short or empty"


def test_hero_node_html_integration() -> None:
    """frontend/index.html must include hero canvas/container and defer script."""
    assert INDEX_HTML.is_file(), f"File does not exist: {INDEX_HTML}"
    html = INDEX_HTML.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # Check container or canvas in hero section
    hero_section = soup.find("section", class_=re.compile(r"\bhero\b"))
    assert hero_section is not None, "Hero section not found in index.html"

    container = hero_section.find(id="hero-canvas-container")
    canvas = hero_section.find(id="hero-canvas")
    assert container is not None or canvas is not None, (
        "Expected #hero-canvas-container or #hero-canvas inside hero section in index.html"
    )

    # Check script tag
    scripts = soup.find_all("script", src=True)
    hero_script = [s for s in scripts if "hero-scene.js" in s["src"]]
    assert len(hero_script) == 1, "Expected exactly one script tag referencing hero-scene.js"
    assert hero_script[0].has_attr("defer"), "hero-scene.js script tag must have 'defer' attribute"


def test_hero_scene_script_load_order_after_trust_bootstrap() -> None:
    """hero-scene.js must be loaded after trust bootstrap scripts in index.html."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    scripts = re.findall(r'<script\b[^>]*\bsrc=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)

    def find_idx(name: str) -> int:
        for idx, src in enumerate(scripts):
            clean = src.split("?")[0].strip()
            if clean == name or clean.endswith("/" + name):
                return idx
        return -1

    verifier_idx = find_idx("verifier.js")
    artifact_idx = find_idx("artifact-state.js")
    hero_idx = find_idx("hero-scene.js")

    assert hero_idx != -1, "hero-scene.js script tag not found in index.html"
    assert verifier_idx != -1, "verifier.js script tag not found in index.html"
    assert hero_idx > verifier_idx, (
        f"hero-scene.js (index {hero_idx}) must be loaded after verifier.js (index {verifier_idx})"
    )

    if artifact_idx != -1:
        assert hero_idx > artifact_idx, (
            f"hero-scene.js (index {hero_idx}) must be loaded after artifact-state.js (index {artifact_idx})"
        )


def test_hero_scene_dpr_clamping_to_maximum_1_5() -> None:
    """hero-scene.js must clamp devicePixelRatio to at most 1.5."""
    content = HERO_SCENE_JS.read_text(encoding="utf-8")
    assert "1.5" in content, "DPR clamp to 1.5 not found in hero-scene.js"
    assert "devicePixelRatio" in content, "window.devicePixelRatio check not found in hero-scene.js"
    # Matches Math.min(window.devicePixelRatio || 1, 1.5) or equivalent clamp pattern
    dpr_pattern = re.search(
        r"Math\.min\(\s*(?:window\.)?devicePixelRatio(?:\s*\|\|\s*1)?\s*,\s*1\.5\s*\)",
        content,
    )
    assert dpr_pattern is not None, "Explicit DPR clamp formula 'Math.min(window.devicePixelRatio || 1, 1.5)' required"


def test_hero_scene_reduced_motion_gating() -> None:
    """hero-scene.js must query prefers-reduced-motion and support static/paused rendering."""
    content = HERO_SCENE_JS.read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in content, (
        "prefers-reduced-motion media query check not found in hero-scene.js"
    )
    assert "matchMedia" in content, "window.matchMedia check not found in hero-scene.js"


def test_hero_scene_intersection_observer_lifecycle() -> None:
    """hero-scene.js must attach IntersectionObserver to control RAF loop."""
    content = HERO_SCENE_JS.read_text(encoding="utf-8")
    assert "IntersectionObserver" in content, "IntersectionObserver not found in hero-scene.js"
    assert "isIntersecting" in content, "isIntersecting visibility handling not found in hero-scene.js"


def test_hero_scene_webgl_context_loss_and_restore_handlers() -> None:
    """hero-scene.js must handle webglcontextlost and webglcontextrestored."""
    content = HERO_SCENE_JS.read_text(encoding="utf-8")
    assert "webglcontextlost" in content, "webglcontextlost listener not found in hero-scene.js"
    assert "webglcontextrestored" in content, "webglcontextrestored listener not found in hero-scene.js"
    assert "preventDefault" in content, "preventDefault() on webglcontextlost not found in hero-scene.js"


def test_hero_scene_dispose_hero_node_export_and_teardown() -> None:
    """hero-scene.js must export window._disposeHeroNode for clean teardown."""
    content = HERO_SCENE_JS.read_text(encoding="utf-8")
    assert "_disposeHeroNode" in content, "window._disposeHeroNode teardown hook not found in hero-scene.js"
    assert "cancelAnimationFrame" in content, "cancelAnimationFrame not found in hero-scene.js"


def test_hero_scene_cold_luxury_palette_tokens() -> None:
    """hero-scene.js must implement Cold Luxury electric cobalt and cyan color styling."""
    content = HERO_SCENE_JS.read_text(encoding="utf-8").lower()
    # Check for presence of cobalt/cyan hex codes, CSS vars, or RGB tokens
    has_cobalt = any(c in content for c in ["3b82f6", "2979ff", "59, 130, 246", "0x3b82f6", "--accent-cobalt"])
    has_cyan = any(c in content for c in ["06b6d4", "00e5ff", "6, 182, 212", "0x06b6d4", "--accent-cyan"])
    assert has_cobalt, "Cold luxury cobalt styling token not found in hero-scene.js"
    assert has_cyan, "Cold luxury cyan styling token not found in hero-scene.js"


def test_hero_scene_node_vm_lifecycle_and_disposal() -> None:
    """Execute hero-scene.js in simulated Node VM environment with full lifecycle testing."""
    test_harness_js = textwrap.dedent(f"""
        const fs = require('fs');
        const vm = require('vm');
        const code = fs.readFileSync({str(HERO_SCENE_JS)!r}, 'utf8');

        let animationFrameCount = 0;
        let canceledFrames = 0;
        let observerDisconnected = false;
        let observerObserved = false;
        let observerCallback = null;

        const eventListeners = {{}};
        const canvasListeners = {{}};

        const mockCanvas = {{
            id: 'hero-canvas',
            width: 300,
            height: 300,
            style: {{ width: '300px', height: '300px' }},
            getBoundingClientRect: () => ({{ width: 300, height: 300, top: 0, left: 0, bottom: 300, right: 300 }}),
            getContext: (type) => {{
                if (type === 'webgl' || type === 'experimental-webgl') {{
                    return {{
                        viewport: () => {{}},
                        clearColor: () => {{}},
                        clear: () => {{}},
                        enable: () => {{}},
                        blendFunc: () => {{}},
                        createShader: () => ({{}}),
                        shaderSource: () => {{}},
                        compileShader: () => {{}},
                        getShaderParameter: () => true,
                        createProgram: () => ({{}}),
                        attachShader: () => {{}},
                        linkProgram: () => {{}},
                        getProgramParameter: () => true,
                        useProgram: () => {{}},
                        createBuffer: () => ({{}}),
                        bindBuffer: () => {{}},
                        bufferData: () => {{}},
                        getAttribLocation: () => 0,
                        getUniformLocation: () => ({{}}),
                        enableVertexAttribArray: () => {{}},
                        vertexAttribPointer: () => {{}},
                        uniformMatrix4fv: () => {{}},
                        uniform4f: () => {{}},
                        uniform3f: () => {{}},
                        uniform1f: () => {{}},
                        drawArrays: () => {{}},
                        drawElements: () => {{}},
                        deleteProgram: () => {{}},
                        deleteShader: () => {{}},
                        deleteBuffer: () => {{}},
                        COLOR_BUFFER_BIT: 16384,
                        DEPTH_BUFFER_BIT: 256,
                        DEPTH_TEST: 2929,
                        BLEND: 3042,
                        SRC_ALPHA: 770,
                        ONE: 1,
                        ONE_MINUS_SRC_ALPHA: 771,
                        TRIANGLES: 4,
                        LINES: 1,
                        STATIC_DRAW: 35044,
                        ARRAY_BUFFER: 34962,
                        ELEMENT_ARRAY_BUFFER: 34963,
                        UNSIGNED_SHORT: 5123,
                        FLOAT: 5126
                    }};
                }}
                if (type === '2d') {{
                    return {{
                        clearRect: () => {{}},
                        beginPath: () => {{}},
                        moveTo: () => {{}},
                        lineTo: () => {{}},
                        stroke: () => {{}},
                        fill: () => {{}},
                        arc: () => {{}},
                        save: () => {{}},
                        restore: () => {{}},
                        translate: () => {{}},
                        scale: () => {{}},
                        createLinearGradient: () => ({{ addColorStop: () => {{}} }}),
                        createRadialGradient: () => ({{ addColorStop: () => {{}} }}),
                        set strokeStyle(v) {{}},
                        set fillStyle(v) {{}},
                        set lineWidth(v) {{}}
                    }};
                }}
                return null;
            }},
            addEventListener: (evt, cb) => {{
                canvasListeners[evt] = canvasListeners[evt] || [];
                canvasListeners[evt].push(cb);
            }},
            removeEventListener: (evt, cb) => {{
                if (canvasListeners[evt]) {{
                    canvasListeners[evt] = canvasListeners[evt].filter(f => f !== cb);
                }}
            }}
        }};

        const mockContainer = {{
            id: 'hero-canvas-container',
            clientWidth: 300,
            clientHeight: 300,
            appendChild: () => {{}},
            querySelector: (sel) => sel === '#hero-canvas' || sel === 'canvas' ? mockCanvas : null
        }};

        let prefersReducedMotion = false;
        const mediaQueryListeners = [];

        const context = {{
            console,
            Math,
            Float32Array,
            Uint16Array,
            Date,
            window: {{
                devicePixelRatio: 2.0,
                innerWidth: 1024,
                innerHeight: 768,
                requestAnimationFrame: (cb) => {{
                    animationFrameCount++;
                    return animationFrameCount;
                }},
                cancelAnimationFrame: (id) => {{
                    canceledFrames++;
                }},
                matchMedia: (query) => ({{
                    matches: query.includes('prefers-reduced-motion') ? prefersReducedMotion : false,
                    media: query,
                    addEventListener: (evt, cb) => mediaQueryListeners.push(cb),
                    removeEventListener: (evt, cb) => {{
                        const idx = mediaQueryListeners.indexOf(cb);
                        if (idx !== -1) mediaQueryListeners.splice(idx, 1);
                    }},
                    addListener: (cb) => mediaQueryListeners.push(cb),
                    removeListener: (cb) => {{
                        const idx = mediaQueryListeners.indexOf(cb);
                        if (idx !== -1) mediaQueryListeners.splice(idx, 1);
                    }}
                }}),
                addEventListener: (evt, cb) => {{
                    eventListeners[evt] = eventListeners[evt] || [];
                    eventListeners[evt].push(cb);
                }},
                removeEventListener: (evt, cb) => {{
                    if (eventListeners[evt]) {{
                        eventListeners[evt] = eventListeners[evt].filter(f => f !== cb);
                    }}
                }},
                document: {{
                    getElementById: (id) => {{
                        if (id === 'hero-canvas') return mockCanvas;
                        if (id === 'hero-canvas-container') return mockContainer;
                        return null;
                    }},
                    querySelector: (sel) => {{
                        if (sel === '#hero-canvas') return mockCanvas;
                        if (sel === '#hero-canvas-container') return mockContainer;
                        return null;
                    }},
                    addEventListener: (evt, cb) => {{
                        eventListeners[evt] = eventListeners[evt] || [];
                        eventListeners[evt].push(cb);
                    }},
                    removeEventListener: (evt, cb) => {{
                        if (eventListeners[evt]) {{
                            eventListeners[evt] = eventListeners[evt].filter(f => f !== cb);
                        }}
                    }},
                    readyState: 'complete'
                }},
                IntersectionObserver: class {{
                    constructor(cb) {{
                        observerCallback = cb;
                    }}
                    observe(el) {{
                        observerObserved = true;
                    }}
                    unobserve(el) {{}}
                    disconnect() {{
                        observerDisconnected = true;
                    }}
                }}
            }}
        }};

        context.window.window = context.window;
        context.window.self = context.window;
        context.document = context.window.document;
        context.IntersectionObserver = context.window.IntersectionObserver;
        context.requestAnimationFrame = context.window.requestAnimationFrame;
        context.cancelAnimationFrame = context.window.cancelAnimationFrame;
        context.matchMedia = context.window.matchMedia;
        context.addEventListener = context.window.addEventListener;
        context.removeEventListener = context.window.removeEventListener;

        vm.createContext(context);
        vm.runInContext(code, context);

        if (typeof context.window._disposeHeroNode !== 'function') {{
            throw new Error('window._disposeHeroNode is not a function');
        }}

        if (!observerObserved) {{
            throw new Error('IntersectionObserver.observe was not called');
        }}

        if (observerCallback) {{
            observerCallback([{{ isIntersecting: false, target: mockCanvas }}]);
        }}

        if (observerCallback) {{
            observerCallback([{{ isIntersecting: true, target: mockCanvas }}]);
        }}

        let preventedLoss = false;
        if (canvasListeners['webglcontextlost'] && canvasListeners['webglcontextlost'].length > 0) {{
            canvasListeners['webglcontextlost'][0]({{
                preventDefault: () => {{ preventedLoss = true; }}
            }});
        }}
        if (!preventedLoss) {{
            throw new Error('webglcontextlost handler did not call preventDefault()');
        }}

        context.window._disposeHeroNode();
        if (!observerDisconnected) {{
            throw new Error('IntersectionObserver was not disconnected on _disposeHeroNode()');
        }}

        console.log(JSON.stringify({{
            ok: true,
            hasDispose: typeof context.window._disposeHeroNode === 'function',
            observerObserved,
            observerDisconnected,
            preventedLoss
        }}));
    """)

    result = subprocess.run(
        ["node", "-e", test_harness_js],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Node VM lifecycle test failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    data = json.loads(result.stdout.strip().splitlines()[-1])
    assert data.get("ok") is True
    assert data.get("hasDispose") is True
    assert data.get("observerObserved") is True
    assert data.get("observerDisconnected") is True
    assert data.get("preventedLoss") is True

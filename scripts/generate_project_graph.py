#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
ConfigStream Project Tree & Topology Graph Generator

Generates a standalone, interactive HTML graph (docs/project_tree_graph.html)
combining repository directory tree hierarchy, module dependencies, data flows,
and MCP code-review-graph topology.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# Root path resolution
REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = REPO_ROOT / "docs" / "project_tree_graph.html"

# Define Subsystems and Palette
SUBSYSTEM_COLORS = {
    "root": "#f43f5e",  # Rose
    "directory": "#38bdf8",  # Sky Blue
    "pipeline": "#a855f7",  # Purple
    "parsers": "#ec4899",  # Pink
    "generators": "#f59e0b",  # Amber
    "output": "#10b981",  # Emerald
    "intelligence": "#3b82f6",  # Indigo Blue
    "testers": "#6366f1",  # Violet
    "security": "#ef4444",  # Red
    "server": "#06b6d4",  # Cyan
    "frontend": "#8b5cf6",  # Violet Blue
    "scripts": "#f97316",  # Orange
    "tests": "#84cc16",  # Lime
    "docs": "#14b8a6",  # Teal
}


def build_graph_data() -> Dict[str, Any]:
    nodes = []
    edges = []
    seen_nodes = set()

    def add_node(
        node_id: str,
        label: str,
        group: str,
        node_type: str,
        path: str = "",
        desc: str = "",
        lines: int = 0,
    ):
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        color = SUBSYSTEM_COLORS.get(group, "#94a3b8")
        size = (
            36
            if node_type == "root"
            else (
                28
                if node_type == "directory"
                else (20 if node_type == "module" else 14)
            )
        )
        shape = (
            "diamond"
            if node_type == "root"
            else (
                "folder"
                if node_type == "directory"
                else ("box" if node_type == "module" else "dot")
            )
        )

        nodes.append(
            {
                "id": node_id,
                "label": label,
                "group": group,
                "type": node_type,
                "path": path,
                "description": desc,
                "lines": lines,
                "color": color,
                "size": size,
                "shape": shape,
            }
        )

    def add_edge(src: str, dst: str, label: str = "", edge_type: str = "hierarchy"):
        color = (
            "#475569"
            if edge_type == "hierarchy"
            else ("#ec4899" if edge_type == "dataflow" else "#a855f7")
        )
        dashes = True if edge_type == "dataflow" else False
        width = 2 if edge_type == "dataflow" else 1
        edges.append(
            {
                "from": src,
                "to": dst,
                "label": label,
                "type": edge_type,
                "color": {"color": color, "highlight": "#f43f5e"},
                "dashes": dashes,
                "width": width,
            }
        )

    # Root Node
    add_node(
        "root",
        "ConfigStream",
        "root",
        "root",
        "D:/GitHub/ConfigStream",
        "Sovereignty-grade anti-censorship platform",
    )

    # High Level Directories
    dirs = [
        (
            "src",
            "src/",
            "directory",
            "root",
            "Source packages (Python backend & Go sidecar)",
        ),
        (
            "src/configstream",
            "configstream/",
            "directory",
            "src",
            "Core Python package root",
        ),
        (
            "src/configstream/pipeline",
            "pipeline/",
            "pipeline",
            "src/configstream",
            "StandardPipeline streaming engine & consumers",
        ),
        (
            "src/configstream/parsers",
            "parsers/",
            "parsers",
            "src/configstream",
            "20+ protocol URI parsers",
        ),
        (
            "src/configstream/generators",
            "generators/",
            "generators",
            "src/configstream",
            "Split, Plaintext, and Sing-box config generators",
        ),
        (
            "src/configstream/output",
            "output/",
            "output",
            "src/configstream",
            "Artifact exports & subscription builders",
        ),
        (
            "src/configstream/intelligence",
            "intelligence/",
            "intelligence",
            "src/configstream",
            "WARP Washer & chaining engine",
        ),
        (
            "src/configstream/testers",
            "testers/",
            "testers",
            "src/configstream",
            "GoBatchTester sidecar IPC & Python fallbacks",
        ),
        (
            "src/configstream/security",
            "security/",
            "security",
            "src/configstream",
            "SecurityValidator & IP/domain blocklists",
        ),
        (
            "src/configstream/server",
            "server/",
            "server",
            "src/configstream",
            "FastAPI server routes (Lab, Proxy, Health)",
        ),
        (
            "src/configstream/converters",
            "converters/",
            "generators",
            "src/configstream",
            "Client profile adapters (Clash, Surge, Loon)",
        ),
        (
            "src/configstream/tools",
            "tools/",
            "scripts",
            "src/configstream",
            "Vwarp tool, Censorship Lab, DNS scanner TUI",
        ),
        ("src/go", "go/", "directory", "src", "Go native components"),
        (
            "src/go/tester",
            "tester/",
            "testers",
            "src/go",
            "Go batch tester daemon & WASM bridge",
        ),
        ("frontend", "frontend/", "frontend", "root", "Frontend Web UI & WebGL Globe"),
        (
            "frontend/assets/js/lab",
            "lab/",
            "frontend",
            "frontend",
            "Modular ES6 Laboratory package",
        ),
        (
            "scripts",
            "scripts/",
            "scripts",
            "root",
            "CI/CD resharding & deployment scripts",
        ),
        (
            "tests",
            "tests/",
            "tests",
            "root",
            "1,270+ Unit & E2E integration test suites",
        ),
        ("docs", "docs/", "docs", "root", "Canonical matrices & architecture reports"),
        (
            "schema",
            "schema/",
            "docs",
            "root",
            "JSON Schemas for Proxy, Metadata, Singbox",
        ),
    ]

    for node_id, label, group, parent_id, desc in dirs:
        add_node(node_id, label, group, "directory", node_id, desc)
        add_edge(parent_id, node_id, "", "hierarchy")

    # Core Module Nodes
    modules = [
        # Pipeline
        (
            "mod:pipeline:core",
            "core.py",
            "pipeline",
            "src/configstream/pipeline",
            "StandardPipeline orchestrator & lifecycle",
            "src/configstream/pipeline/core.py",
            497,
        ),
        (
            "mod:pipeline:producer",
            "producer.py",
            "pipeline",
            "src/configstream/pipeline",
            "StreamingProducer source fetcher & queue pusher",
            "src/configstream/pipeline/producer.py",
            560,
        ),
        (
            "mod:pipeline:consumer",
            "consumer.py",
            "pipeline",
            "src/configstream/pipeline",
            "WorkerConsumer queue processing & revival",
            "src/configstream/pipeline/consumer.py",
            831,
        ),
        (
            "mod:models",
            "models.py",
            "pipeline",
            "src/configstream",
            "Canonical Proxy & ProxyGroup DTO models",
            "src/configstream/models.py",
            214,
        ),
        # Parsers
        (
            "mod:parsers:vmess",
            "vmess.py",
            "parsers",
            "src/configstream/parsers",
            "VMess base64 JSON parser",
            "src/configstream/parsers/vmess.py",
            180,
        ),
        (
            "mod:parsers:vless",
            "vless.py",
            "parsers",
            "src/configstream/parsers",
            "VLESS URI & query param parser",
            "src/configstream/parsers/vless.py",
            165,
        ),
        (
            "mod:parsers:hy3",
            "hysteria3.py",
            "parsers",
            "src/configstream/parsers",
            "Hysteria3 direct proxy scheme parser",
            "src/configstream/parsers/hysteria3.py",
            140,
        ),
        (
            "mod:parsers:tuic",
            "tuic.py",
            "parsers",
            "src/configstream/parsers",
            "TUIC v5 protocol parser",
            "src/configstream/parsers/tuic.py",
            120,
        ),
        (
            "mod:parsers:ss",
            "shadowsocks.py",
            "parsers",
            "src/configstream/parsers",
            "Shadowsocks & SS2022 parser",
            "src/configstream/parsers/shadowsocks.py",
            195,
        ),
        # Intelligence & Washer
        (
            "mod:washer:core",
            "core.py",
            "intelligence",
            "src/configstream/intelligence",
            "ProxyWasher WARP key & chain manager",
            "src/configstream/intelligence/washer/core.py",
            850,
        ),
        (
            "mod:chaining",
            "chaining.py",
            "intelligence",
            "src/configstream/intelligence",
            "Haversine geo-distance & multi-hop chaining",
            "src/configstream/intelligence/chaining.py",
            320,
        ),
        # Testers
        (
            "mod:go_tester:manager",
            "manager.py",
            "testers",
            "src/configstream/testers",
            "GoBatchTester sidecar IPC & daemon lifecycle",
            "src/configstream/testers/go_tester/manager.py",
            921,
        ),
        (
            "mod:go_tester:wasm",
            "wasm_main.go",
            "testers",
            "src/go/tester",
            "Go WASM bridge & Web Crypto interop",
            "src/go/tester/wasm_main.go",
            410,
        ),
        # Output
        (
            "mod:output:logic",
            "output_logic.py",
            "output",
            "src/configstream/output",
            "Thin orchestrator for output generation",
            "src/configstream/output_logic.py",
            185,
        ),
        (
            "mod:output:metadata",
            "metadata.py",
            "output",
            "src/configstream/output",
            "Metadata, health.json & manifest exporter",
            "src/configstream/output/metadata.py",
            290,
        ),
        (
            "mod:output:native",
            "native_configs.py",
            "output",
            "src/configstream/output",
            "Sing-box & Clash profile generator",
            "src/configstream/output/native_configs.py",
            410,
        ),
        # Security & Cryptography
        (
            "mod:signer",
            "signer.py",
            "security",
            "src/configstream",
            "Ed25519 manifest signer & verification",
            "src/configstream/signer.py",
            240,
        ),
        (
            "mod:stego",
            "stego.py",
            "security",
            "src/configstream",
            "LSB PNG steganography v1/v2/v3 (HMAC)",
            "src/configstream/stego.py",
            380,
        ),
        (
            "mod:security_val",
            "security_validator.py",
            "security",
            "src/configstream",
            "Log sanitization & blocklist enforcement",
            "src/configstream/security_validator.py",
            290,
        ),
        # Server & Routes
        (
            "mod:server:lab",
            "lab.py",
            "server",
            "src/configstream/server",
            "FastAPI live lab testing route & auth",
            "src/configstream/server/routes/lab.py",
            280,
        ),
        # Frontend
        (
            "mod:fe:lab_ui",
            "ui.js",
            "frontend",
            "frontend/assets/js/lab",
            "DOM builder & XSS-safe renderer",
            "frontend/assets/js/lab/ui.js",
            340,
        ),
        (
            "mod:fe:stego",
            "stego.js",
            "frontend",
            "frontend/assets/js/lab",
            "Web Crypto Ed25519 signature validator",
            "frontend/assets/js/stego.js",
            210,
        ),
        # Tools & Scripts
        (
            "mod:tools:vwarp",
            "vwarp.py",
            "scripts",
            "src/configstream/tools",
            "Canonical VwarpTool scanner & MASQUE builder",
            "src/configstream/tools/vwarp.py",
            640,
        ),
        (
            "mod:scripts:validate",
            "validate_pages_artifact.py",
            "scripts",
            "scripts",
            "Artifact validator & schema checker",
            "scripts/validate_pages_artifact.py",
            1326,
        ),
    ]

    for node_id, label, group, parent_id, desc, path, lines in modules:
        add_node(node_id, label, group, "module", path, desc, lines)
        add_edge(parent_id, node_id, "", "hierarchy")

    # Data Flow and Inter-Module Dependency Edges
    flows = [
        ("mod:pipeline:producer", "mod:models", "creates Proxy DTO", "dataflow"),
        (
            "mod:pipeline:producer",
            "mod:pipeline:consumer",
            "asyncio.Queue work items",
            "dataflow",
        ),
        (
            "mod:pipeline:consumer",
            "mod:go_tester:manager",
            "batch test IPC",
            "dependency",
        ),
        (
            "mod:pipeline:consumer",
            "mod:washer:core",
            "revive failed proxies",
            "dependency",
        ),
        (
            "mod:washer:core",
            "mod:tools:vwarp",
            "generate WARP/Vwarp config",
            "dependency",
        ),
        (
            "mod:pipeline:core",
            "mod:output:logic",
            "trigger artifact export",
            "dataflow",
        ),
        ("mod:output:logic", "mod:output:native", "generate profiles", "dependency"),
        (
            "mod:output:logic",
            "mod:output:metadata",
            "write metadata & manifest",
            "dependency",
        ),
        ("mod:output:metadata", "mod:signer", "sign manifest (Ed25519)", "dependency"),
        ("mod:output:logic", "mod:stego", "pack stego carrier images", "dependency"),
        (
            "mod:server:lab",
            "mod:go_tester:manager",
            "live proxy chain test",
            "dependency",
        ),
        ("mod:fe:stego", "mod:signer", "Web Crypto verification", "dataflow"),
        (
            "mod:scripts:validate",
            "mod:output:metadata",
            "validate artifact bundle",
            "dependency",
        ),
    ]

    for src, dst, label, edge_type in flows:
        add_edge(src, dst, label, edge_type)

    return {"nodes": nodes, "edges": edges}


def generate_html(data: Dict[str, Any]) -> str:
    nodes_json = json.dumps(data["nodes"], indent=2)
    edges_json = json.dumps(data["edges"], indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ConfigStream — Interactive Codebase Topology & Tree Graph</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        :root {{
            --bg-dark: #0b0f19;
            --bg-panel: rgba(15, 23, 42, 0.75);
            --border-panel: rgba(255, 255, 255, 0.1);
            --accent-primary: #38bdf8;
            --accent-purple: #a855f7;
            --accent-rose: #f43f5e;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body, html {{
            width: 100%;
            height: 100%;
            overflow: hidden;
            background-color: var(--bg-dark);
            font-family: var(--font-sans);
            color: var(--text-main);
        }}

        #network {{
            width: 100%;
            height: 100%;
            position: absolute;
            top: 0;
            left: 0;
            z-index: 1;
        }}

        /* Glassmorphic UI Overlays */
        .glass-panel {{
            background: var(--bg-panel);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--border-panel);
            border-radius: 12px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }}

        /* Header Bar */
        #header-bar {{
            position: absolute;
            top: 16px;
            left: 16px;
            right: 16px;
            z-index: 10;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 20px;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .brand-badge {{
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--accent-rose), var(--accent-purple));
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 16px;
            box-shadow: 0 0 12px rgba(244, 63, 94, 0.4);
        }}

        .brand-title {{
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.02em;
            background: linear-gradient(to right, #ffffff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .brand-subtitle {{
            font-size: 12px;
            color: var(--text-muted);
            font-weight: 400;
        }}

        /* Controls & Filter Bar */
        .controls-wrapper {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .search-box {{
            position: relative;
            width: 240px;
        }}

        .search-input {{
            width: 100%;
            padding: 8px 12px 8px 34px;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-panel);
            border-radius: 8px;
            color: var(--text-main);
            font-family: var(--font-sans);
            font-size: 13px;
            outline: none;
            transition: all 0.2s ease;
        }}

        .search-input:focus {{
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.25);
        }}

        .search-icon {{
            position: absolute;
            left: 10px;
            top: 50%;
            transform: translateY(-50%);
            width: 14px;
            height: 14px;
            fill: var(--text-muted);
        }}

        .btn {{
            padding: 8px 14px;
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid var(--border-panel);
            border-radius: 8px;
            color: var(--text-main);
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .btn:hover {{
            background: rgba(51, 65, 85, 1);
            border-color: rgba(255, 255, 255, 0.2);
            transform: translateY(-1px);
        }}

        /* Subsystem Filters Chips */
        #filters-bar {{
            position: absolute;
            top: 80px;
            left: 16px;
            z-index: 10;
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            max-width: calc(100% - 380px);
        }}

        .chip {{
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid var(--border-panel);
            color: var(--text-muted);
            transition: all 0.2s ease;
        }}

        .chip.active, .chip:hover {{
            color: #ffffff;
            border-color: var(--accent-primary);
            background: rgba(56, 189, 248, 0.15);
        }}

        /* Inspector Sidebar */
        #inspector {{
            position: absolute;
            top: 130px;
            right: 16px;
            bottom: 16px;
            width: 340px;
            z-index: 10;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            overflow-y: auto;
            transform: translateX(0);
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }}

        .inspector-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border-panel);
            padding-bottom: 12px;
        }}

        .inspector-title {{
            font-size: 16px;
            font-weight: 700;
            color: var(--text-main);
        }}

        .badge-type {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .info-group {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}

        .info-label {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.05em;
        }}

        .info-value {{
            font-size: 13px;
            color: var(--text-main);
            word-break: break-all;
        }}

        .info-code {{
            font-family: var(--font-mono);
            background: rgba(0, 0, 0, 0.4);
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 12px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}

        /* Legend */
        #legend {{
            position: absolute;
            bottom: 16px;
            left: 16px;
            z-index: 10;
            padding: 14px 18px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .legend-title {{
            font-size: 12px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .legend-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 6px 16px;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: var(--text-main);
        }}

        .legend-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }}
    </style>
</head>
<body>
    <div id="network"></div>

    <!-- Header Bar -->
    <div id="header-bar" class="glass-panel">
        <div class="brand">
            <div class="brand-badge">CS</div>
            <div>
                <div class="brand-title">ConfigStream Codebase Graph</div>
                <div class="brand-subtitle">Interactive Structural Hierarchy & Module Topology</div>
            </div>
        </div>
        <div class="controls-wrapper">
            <div class="search-box">
                <svg class="search-icon" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
                <input type="text" id="searchInput" class="search-input" placeholder="Search modules, paths...">
            </div>
            <button class="btn" onclick="resetView()">Reset View</button>
            <button class="btn" onclick="togglePhysics()">Toggle Layout</button>
        </div>
    </div>

    <!-- Subsystem Filters -->
    <div id="filters-bar">
        <div class="chip active" onclick="filterSubsystem('all', this)">All Subsystems</div>
        <div class="chip" onclick="filterSubsystem('pipeline', this)">Pipeline</div>
        <div class="chip" onclick="filterSubsystem('parsers', this)">Parsers</div>
        <div class="chip" onclick="filterSubsystem('generators', this)">Generators</div>
        <div class="chip" onclick="filterSubsystem('output', this)">Output Engine</div>
        <div class="chip" onclick="filterSubsystem('intelligence', this)">WARP Intelligence</div>
        <div class="chip" onclick="filterSubsystem('testers', this)">Go Testers</div>
        <div class="chip" onclick="filterSubsystem('security', this)">Security & Cryptography</div>
        <div class="chip" onclick="filterSubsystem('server', this)">Server Routes</div>
        <div class="chip" onclick="filterSubsystem('frontend', this)">Frontend & WebGL</div>
        <div class="chip" onclick="filterSubsystem('scripts', this)">Scripts & Tools</div>
    </div>

    <!-- Inspector Sidebar -->
    <div id="inspector" class="glass-panel">
        <div class="inspector-header">
            <div id="nodeTitle" class="inspector-title">Select a Node</div>
            <div id="nodeTypeBadge" class="badge-type" style="background: rgba(255,255,255,0.1);">Overview</div>
        </div>
        <div class="info-group">
            <div class="info-label">Subsystem Group</div>
            <div id="nodeGroup" class="info-value">ConfigStream Root</div>
        </div>
        <div class="info-group">
            <div class="info-label">File Path</div>
            <div id="nodePath" class="info-code">D:/GitHub/ConfigStream</div>
        </div>
        <div class="info-group">
            <div class="info-label">Description</div>
            <div id="nodeDesc" class="info-value">Click any node in the topology graph to inspect its function, metrics, and relationships.</div>
        </div>
        <div class="info-group" id="linesGroup">
            <div class="info-label">Lines of Code</div>
            <div id="nodeLines" class="info-value">--</div>
        </div>
        <div class="info-group">
            <div class="info-label">Connected Edges</div>
            <div id="nodeEdges" class="info-value">--</div>
        </div>
    </div>

    <!-- Legend -->
    <div id="legend" class="glass-panel">
        <div class="legend-title">Subsystem Legend</div>
        <div class="legend-grid">
            <div class="legend-item"><div class="legend-dot" style="background: #a855f7;"></div>Pipeline Core</div>
            <div class="legend-item"><div class="legend-dot" style="background: #ec4899;"></div>Parsers</div>
            <div class="legend-item"><div class="legend-dot" style="background: #f59e0b;"></div>Generators</div>
            <div class="legend-item"><div class="legend-dot" style="background: #10b981;"></div>Output Engine</div>
            <div class="legend-item"><div class="legend-dot" style="background: #3b82f6;"></div>WARP Washer</div>
            <div class="legend-item"><div class="legend-dot" style="background: #6366f1;"></div>Go Sidecar</div>
            <div class="legend-item"><div class="legend-dot" style="background: #ef4444;"></div>Security & Crypto</div>
            <div class="legend-item"><div class="legend-dot" style="background: #06b6d4;"></div>FastAPI Server</div>
        </div>
    </div>

    <script>
        const rawNodes = {nodes_json};
        const rawEdges = {edges_json};

        let network = null;
        let nodesDataset = new vis.DataSet(rawNodes);
        let edgesDataset = new vis.DataSet(rawEdges);
        let physicsEnabled = true;

        const container = document.getElementById('network');
        const data = {{ nodes: nodesDataset, edges: edgesDataset }};

        const options = {{
            nodes: {{
                font: {{ color: '#f8fafc', face: 'Inter', size: 13 }},
                borderWidth: 2,
                shadow: true,
            }},
            edges: {{
                font: {{ color: '#94a3b8', face: 'Inter', size: 10, align: 'middle' }},
                smooth: {{ type: 'cubicBezier', forceDirection: 'none', roundness: 0.4 }},
            }},
            physics: {{
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {{
                    gravitationalConstant: -50,
                    centralGravity: 0.01,
                    springLength: 100,
                    springConstant: 0.08,
                }},
                maxVelocity: 50,
                timestep: 0.35,
                stabilization: {{ iterations: 150 }},
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200,
                navigationButtons: false,
                keyboard: true,
            }},
        }};

        network = new vis.Network(container, data, options);

        // Click Event for Inspector
        network.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const node = nodesDataset.get(nodeId);
                const connectedEdges = network.getConnectedEdges(nodeId);
                
                document.getElementById('nodeTitle').innerText = node.label;
                document.getElementById('nodeTypeBadge').innerText = node.type;
                document.getElementById('nodeTypeBadge').style.background = node.color + '40';
                document.getElementById('nodeTypeBadge').style.color = node.color;
                document.getElementById('nodeGroup').innerText = node.group.toUpperCase();
                document.getElementById('nodePath').innerText = node.path || '--';
                document.getElementById('nodeDesc').innerText = node.description || 'No description available.';
                document.getElementById('nodeLines').innerText = node.lines ? node.lines + ' lines' : 'N/A';
                document.getElementById('nodeEdges').innerText = connectedEdges.length + ' connections';
            }}
        }});

        // Search Filter
        document.getElementById('searchInput').addEventListener('input', function(e) {{
            const query = e.target.value.toLowerCase().strip();
            if (!query) return;
            
            const match = rawNodes.find(n => n.label.toLowerCase().includes(query) || (n.path && n.path.toLowerCase().includes(query)));
            if (match) {{
                network.focus(match.id, {{ scale: 1.2, animation: true }});
                network.selectNodes([match.id]);
            }}
        }});

        function resetView() {{
            network.fit({{ animation: true }});
        }}

        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
        }}

        function filterSubsystem(subsystem, chipEl) {{
            document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
            chipEl.classList.add('active');

            if (subsystem === 'all') {{
                nodesDataset.update(rawNodes.map(n => ({{ id: n.id, hidden: false }})));
            }} else {{
                nodesDataset.update(rawNodes.map(n => ({{
                    id: n.id,
                    hidden: n.group !== subsystem && n.type !== 'root' && n.type !== 'directory'
                }})));
            }}
        }}
    </script>
</body>
</html>
"""


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    graph_data = build_graph_data()
    html_content = generate_html(graph_data)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[SUCCESS] Successfully generated project graph HTML at: {OUTPUT_FILE}")
    print(
        f"          Nodes: {len(graph_data['nodes'])}, Edges: {len(graph_data['edges'])}"
    )


if __name__ == "__main__":
    main()

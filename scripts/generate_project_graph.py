#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
ConfigStream Advanced Codebase Topology & Tree Graph Generator (v2.1)

Generates a secure, deterministic, standalone interactive HTML graph (docs/project_tree_graph.html):
1. Safe JSON embedding via <script type="application/json"> with HTML entity escaping to prevent XSS.
2. Machine-independent relative repository paths (no absolute D:/... path leaks).
3. Deterministic reproducible builds across clean CI checkouts.
4. Animated Execution Flow Pulses along the streaming pipeline.
5. Multi-View Heatmap Controller (Subsystems, LOC Density, Streaming Flow Focus).
6. Verbatim Code Inspector Sidebar with live source snippets & signatures.
"""

import json
import logging
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Root path resolution
REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = REPO_ROOT / "docs" / "project_tree_graph.html"
GRAPH_DB_PATH = REPO_ROOT / ".code-review-graph" / "graph.db"

# Subsystem Palette
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


def extract_file_snippet(rel_path: str, max_lines: int = 25) -> Dict[str, Any]:
    """Reads verbatim docstrings, main signatures, and code snippet from disk."""
    abs_path = REPO_ROOT / rel_path
    if not abs_path.exists() or abs_path.is_dir():
        return {"snippet": "", "signatures": [], "docstring": "", "lines": 0}

    try:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        line_count = len(lines)

        # Extract docstring
        docstring = ""
        doc_match = re.search(
            r'^(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', content, re.DOTALL | re.MULTILINE
        )
        if doc_match:
            docstring = doc_match.group(1).strip()

        # Extract function/class signatures
        signatures = []
        for raw_line in lines:
            line_str = raw_line.strip()
            if line_str.startswith(
                ("def ", "class ", "async def ", "func ", "export function ")
            ):
                signatures.append(line_str.split(":", 1)[0].split("{", 1)[0])
            if len(signatures) >= 8:
                break

        # Preview snippet
        preview_snippet = "\n".join(lines[:max_lines])
        if line_count > max_lines:
            preview_snippet += f"\n... [{line_count - max_lines} more lines]"

        return {
            "snippet": preview_snippet,
            "signatures": signatures,
            "docstring": docstring,
            "lines": line_count,
        }
    except Exception as exc:
        logger.debug("Failed to extract snippet from %s: %s", rel_path, exc)
        return {
            "snippet": f"# Could not read file: {exc}",
            "signatures": [],
            "docstring": "",
            "lines": 0,
        }


def get_complexity_color(lines: int) -> str:
    if lines <= 0:
        return "#38bdf8"  # Directory / virtual
    elif lines < 200:
        return "#10b981"  # Emerald (lightweight)
    elif lines < 500:
        return "#f59e0b"  # Amber (medium)
    else:
        return "#ef4444"  # Red (complex / heavy)


def safe_json_dumps(data: Any) -> str:
    """Safely serializes JSON for inclusion in HTML script blocks by escaping HTML tags."""
    raw_json = json.dumps(data, indent=2, sort_keys=True)
    return (
        raw_json.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def build_graph_data(include_local_db: bool = False) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    seen_nodes = set()
    seen_edges = set()

    def add_node(
        node_id: str,
        label: str,
        group: str,
        node_type: str,
        path: str = "",
        desc: str = "",
        default_lines: int = 0,
    ):
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)

        # Normalize paths to relative repo format
        rel_path = path.replace("\\", "/").strip("/") if path else ""

        snippet_data = (
            extract_file_snippet(rel_path)
            if rel_path and node_type == "module"
            else {
                "snippet": "",
                "signatures": [],
                "docstring": "",
                "lines": default_lines,
            }
        )
        lines_raw = snippet_data.get("lines")
        lines_cnt: int = (
            int(lines_raw) if isinstance(lines_raw, (int, str)) else int(default_lines)
        )
        description = str(snippet_data.get("docstring") or desc)

        subsystem_color = SUBSYSTEM_COLORS.get(group, "#94a3b8")
        complexity_color = get_complexity_color(lines_cnt)
        size = (
            36
            if node_type == "root"
            else (28 if node_type == "directory" else (22 if lines_cnt > 500 else 18))
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

        sigs_raw = snippet_data.get("signatures")
        sigs_list: List[str] = (
            [str(s) for s in sigs_raw] if isinstance(sigs_raw, list) else []
        )

        nodes.append(
            {
                "id": node_id,
                "label": label,
                "group": group,
                "type": node_type,
                "path": rel_path or ".",
                "description": description,
                "lines": lines_cnt,
                "subsystemColor": subsystem_color,
                "complexityColor": complexity_color,
                "color": subsystem_color,
                "size": size,
                "shape": shape,
                "snippet": str(snippet_data.get("snippet", "")),
                "signatures": sigs_list,
                "communityId": "default",
            }
        )

    def add_edge(src: str, dst: str, label: str = "", edge_type: str = "hierarchy"):
        edge_key = (src, dst, edge_type)
        if edge_key in seen_edges:
            return
        seen_edges.add(edge_key)

        is_flow = edge_type == "dataflow"
        color = "#a855f7" if is_flow else "#475569"
        dashes = is_flow
        width = 3 if is_flow else 1

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
        ".",
        "Sovereignty-grade zero-budget anti-censorship platform",
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

    # Core Module Nodes with Live Paths
    modules = [
        # Pipeline
        (
            "mod:pipeline:core",
            "core.py",
            "pipeline",
            "src/configstream/pipeline",
            "StandardPipeline orchestrator & lifecycle",
            "src/configstream/pipeline/core.py",
        ),
        (
            "mod:pipeline:producer",
            "producer.py",
            "pipeline",
            "src/configstream/pipeline",
            "StreamingProducer source fetcher & queue pusher",
            "src/configstream/pipeline/producer.py",
        ),
        (
            "mod:pipeline:consumer",
            "consumer.py",
            "pipeline",
            "src/configstream/pipeline",
            "WorkerConsumer queue processing & revival",
            "src/configstream/pipeline/consumer.py",
        ),
        (
            "mod:models",
            "models.py",
            "pipeline",
            "src/configstream",
            "Canonical Proxy & ProxyGroup DTO models",
            "src/configstream/models.py",
        ),
        # Parsers
        (
            "mod:parsers:vmess",
            "vmess.py",
            "parsers",
            "src/configstream/parsers",
            "VMess base64 JSON parser",
            "src/configstream/parsers/vmess.py",
        ),
        (
            "mod:parsers:vless",
            "vless.py",
            "parsers",
            "src/configstream/parsers",
            "VLESS URI & query param parser",
            "src/configstream/parsers/vless.py",
        ),
        (
            "mod:parsers:hy3",
            "hysteria3.py",
            "parsers",
            "src/configstream/parsers",
            "Hysteria3 direct proxy scheme parser",
            "src/configstream/parsers/hysteria3.py",
        ),
        (
            "mod:parsers:tuic",
            "tuic.py",
            "parsers",
            "src/configstream/parsers",
            "TUIC v5 protocol parser",
            "src/configstream/parsers/tuic.py",
        ),
        (
            "mod:parsers:ss",
            "shadowsocks.py",
            "parsers",
            "src/configstream/parsers",
            "Shadowsocks & SS2022 parser",
            "src/configstream/parsers/shadowsocks.py",
        ),
        # Intelligence & Washer
        (
            "mod:washer:core",
            "core.py",
            "intelligence",
            "src/configstream/intelligence",
            "ProxyWasher WARP key & chain manager",
            "src/configstream/intelligence/washer/core.py",
        ),
        (
            "mod:chaining",
            "chaining.py",
            "intelligence",
            "src/configstream/intelligence",
            "Haversine geo-distance & multi-hop chaining",
            "src/configstream/intelligence/chaining.py",
        ),
        # Testers
        (
            "mod:go_tester:manager",
            "manager.py",
            "testers",
            "src/configstream/testers",
            "GoBatchTester sidecar IPC & daemon lifecycle",
            "src/configstream/testers/go_tester/manager.py",
        ),
        (
            "mod:go_tester:wasm",
            "wasm_main.go",
            "testers",
            "src/go/tester",
            "Go WASM bridge & Web Crypto interop",
            "src/go/tester/wasm_main.go",
        ),
        # Output
        (
            "mod:output:logic",
            "output_logic.py",
            "output",
            "src/configstream/output",
            "Thin orchestrator for output generation",
            "src/configstream/output_logic.py",
        ),
        (
            "mod:output:metadata",
            "metadata.py",
            "output",
            "src/configstream/output",
            "Metadata, health.json & manifest exporter",
            "src/configstream/output/metadata.py",
        ),
        (
            "mod:output:native",
            "native_configs.py",
            "output",
            "src/configstream/output",
            "Sing-box & Clash profile generator",
            "src/configstream/output/native_configs.py",
        ),
        # Security & Cryptography
        (
            "mod:signer",
            "signer.py",
            "security",
            "src/configstream",
            "Ed25519 manifest signer & verification",
            "src/configstream/signer.py",
        ),
        (
            "mod:stego",
            "stego.py",
            "security",
            "src/configstream",
            "LSB PNG steganography v1/v2/v3 (HMAC)",
            "src/configstream/stego.py",
        ),
        (
            "mod:security_val",
            "security_validator.py",
            "security",
            "src/configstream",
            "Log sanitization & blocklist enforcement",
            "src/configstream/security_validator.py",
        ),
        # Server & Routes
        (
            "mod:server:lab",
            "lab.py",
            "server",
            "src/configstream/server",
            "FastAPI live lab testing route & auth",
            "src/configstream/server/routes/lab.py",
        ),
        # Frontend
        (
            "mod:fe:lab_ui",
            "ui.js",
            "frontend",
            "frontend/assets/js/lab",
            "DOM builder & XSS-safe renderer",
            "frontend/assets/js/lab/ui.js",
        ),
        (
            "mod:fe:stego",
            "stego.js",
            "frontend",
            "frontend/assets/js/lab",
            "Web Crypto Ed25519 signature validator",
            "frontend/assets/js/stego.js",
        ),
        # Tools & Scripts
        (
            "mod:tools:vwarp",
            "vwarp.py",
            "scripts",
            "src/configstream/tools",
            "Canonical VwarpTool scanner & MASQUE builder",
            "src/configstream/tools/vwarp.py",
        ),
        (
            "mod:scripts:validate",
            "validate_pages_artifact.py",
            "scripts",
            "scripts",
            "Artifact validator & schema checker",
            "scripts/validate_pages_artifact.py",
        ),
        (
            "mod:tools:lab_scanner",
            "lab-scanner.py",
            "scripts",
            "tools",
            "Portable local diagnostic & clean IP finder",
            "tools/lab-scanner.py",
        ),
    ]

    for item in modules:
        node_id, label, group, parent_id, desc, path = item
        add_node(node_id, label, group, "module", path, desc)
        add_edge(parent_id, node_id, "", "hierarchy")

    # Primary Streaming Execution Flow (Dataflow Pulses)
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
            "dataflow",
        ),
        (
            "mod:pipeline:consumer",
            "mod:washer:core",
            "revive failed proxies",
            "dataflow",
        ),
        (
            "mod:washer:core",
            "mod:tools:vwarp",
            "generate WARP/Vwarp config",
            "dataflow",
        ),
        (
            "mod:pipeline:core",
            "mod:output:logic",
            "trigger artifact export",
            "dataflow",
        ),
        ("mod:output:logic", "mod:output:native", "generate profiles", "dataflow"),
        (
            "mod:output:logic",
            "mod:output:metadata",
            "write metadata & manifest",
            "dataflow",
        ),
        ("mod:output:metadata", "mod:signer", "sign manifest (Ed25519)", "dataflow"),
        ("mod:output:logic", "mod:stego", "pack stego carrier images", "dataflow"),
        (
            "mod:server:lab",
            "mod:go_tester:manager",
            "live proxy chain test",
            "dataflow",
        ),
        ("mod:fe:stego", "mod:signer", "Web Crypto verification", "dataflow"),
        (
            "mod:scripts:validate",
            "mod:output:metadata",
            "validate artifact bundle",
            "dataflow",
        ),
    ]

    for src, dst, label, edge_type in flows:
        add_edge(src, dst, label, edge_type)

    # Optional SQLite MCP Code-Review-Graph Enrichment (only when explicitly requested via --include-local-db)
    if include_local_db and GRAPH_DB_PATH.exists():
        try:
            conn = sqlite3.connect(str(GRAPH_DB_PATH))
            c = conn.cursor()
            comms = c.execute(
                "SELECT id, name, size, dominant_language, description FROM communities WHERE size > 5 ORDER BY id ASC"
            ).fetchall()
            for comm_id, comm_name, comm_size, comm_lang, comm_desc in comms:
                c_id = f"mcp:comm:{comm_id}"
                c_group = (
                    "pipeline"
                    if "proxy" in str(comm_name).lower()
                    else ("scripts" if "script" in str(comm_name).lower() else "docs")
                )
                add_node(
                    c_id,
                    f"MCP Community: {comm_name} ({comm_size} nodes)",
                    c_group,
                    "community",
                    "",
                    f"Language: {comm_lang}. {comm_desc or ''}",
                    comm_size * 50,
                )
                add_edge("root", c_id, "mcp-community", "hierarchy")
            conn.close()
        except Exception as exc:
            print(f"[NOTE] SQLite MCP enrichment skipped: {exc}")

    # Sort nodes and edges for 100% deterministic output ordering
    nodes.sort(key=lambda n: str(n["id"]))
    edges.sort(key=lambda e: (str(e["from"]), str(e["to"]), str(e["type"])))

    return {"nodes": nodes, "edges": edges}


def generate_html(data: Dict[str, Any]) -> str:
    nodes_safe_json = safe_json_dumps(data["nodes"])
    edges_safe_json = safe_json_dumps(data["edges"])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ConfigStream — Advanced Codebase Topology & Tree Graph (v2.1)</title>
    <style>
        :root {{
            --bg-dark: #070a12;
            --bg-panel: rgba(13, 20, 36, 0.85);
            --border-panel: rgba(255, 255, 255, 0.12);
            --accent-primary: #38bdf8;
            --accent-purple: #a855f7;
            --accent-rose: #f43f5e;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --font-sans: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body, html {{
            width: 100%; height: 100%; overflow: hidden;
            background-color: var(--bg-dark);
            font-family: var(--font-sans);
            color: var(--text-main);
        }}

        #network {{ width: 100%; height: 100%; position: absolute; top: 0; left: 0; z-index: 1; }}

        .glass-panel {{
            background: var(--bg-panel);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--border-panel);
            border-radius: 14px;
            box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.5);
        }}

        #header-bar {{
            position: absolute; top: 16px; left: 16px; right: 16px; z-index: 10;
            display: flex; align-items: center; justify-content: space-between;
            padding: 12px 22px;
        }}

        .brand {{ display: flex; align-items: center; gap: 14px; }}
        .brand-badge {{
            width: 36px; height: 36px;
            background: linear-gradient(135deg, var(--accent-rose), var(--accent-purple));
            border-radius: 10px; display: flex; align-items: center; justify-content: center;
            font-weight: 800; font-size: 16px; color: #fff;
            box-shadow: 0 0 16px rgba(244, 63, 94, 0.5);
        }}
        .brand-title {{
            font-size: 19px; font-weight: 700; letter-spacing: -0.02em;
            background: linear-gradient(to right, #ffffff, #cbd5e1);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }}
        .brand-subtitle {{ font-size: 12px; color: var(--text-muted); }}

        .controls-wrapper {{ display: flex; align-items: center; gap: 10px; }}

        .search-box {{ position: relative; width: 260px; }}
        .search-input {{
            width: 100%; padding: 9px 12px 9px 36px;
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid var(--border-panel); border-radius: 8px;
            color: var(--text-main); font-family: var(--font-sans); font-size: 13px; outline: none;
            transition: all 0.2s ease;
        }}
        .search-input:focus {{ border-color: var(--accent-primary); box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.3); }}
        .search-icon {{ position: absolute; left: 12px; top: 50%; transform: translateY(-50%); width: 14px; height: 14px; fill: var(--text-muted); }}

        .btn {{
            padding: 9px 14px; background: rgba(30, 41, 59, 0.85);
            border: 1px solid var(--border-panel); border-radius: 8px;
            color: var(--text-main); font-size: 13px; font-weight: 500; cursor: pointer;
            transition: all 0.2s ease; display: flex; align-items: center; gap: 6px;
        }}
        .btn:hover {{ background: rgba(51, 65, 85, 1); border-color: rgba(255, 255, 255, 0.3); transform: translateY(-1px); }}
        .btn.active {{ background: rgba(56, 189, 248, 0.2); border-color: var(--accent-primary); color: #fff; }}

        #view-modes-bar {{
            position: absolute; top: 82px; left: 16px; z-index: 10;
            display: flex; gap: 8px; align-items: center; padding: 6px;
        }}
        .mode-btn {{
            padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 600;
            cursor: pointer; background: transparent; border: none; color: var(--text-muted);
            transition: all 0.2s ease;
        }}
        .mode-btn.active {{ background: rgba(56, 189, 248, 0.25); color: #ffffff; border: 1px solid var(--accent-primary); }}

        #filters-bar {{
            position: absolute; top: 132px; left: 16px; z-index: 10;
            display: flex; gap: 6px; flex-wrap: wrap; max-width: calc(100% - 420px);
        }}
        .chip {{
            padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 500;
            cursor: pointer; background: rgba(15, 23, 42, 0.75); border: 1px solid var(--border-panel);
            color: var(--text-muted); transition: all 0.2s ease;
        }}
        .chip.active, .chip:hover {{ color: #ffffff; border-color: var(--accent-primary); background: rgba(56, 189, 248, 0.2); }}

        #inspector {{
            position: absolute; top: 82px; right: 16px; bottom: 16px; width: 380px; z-index: 10;
            padding: 22px; display: flex; flex-direction: column; gap: 16px; overflow-y: auto;
        }}
        .inspector-header {{ display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border-panel); padding-bottom: 14px; }}
        .inspector-title {{ font-size: 17px; font-weight: 700; color: var(--text-main); }}
        .badge-type {{ padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }}

        .info-group {{ display: flex; flex-direction: column; gap: 4px; }}
        .info-label {{ font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em; }}
        .info-value {{ font-size: 13px; color: var(--text-main); word-break: break-all; line-height: 1.4; }}

        .code-container {{
            font-family: var(--font-mono); font-size: 11px; color: #e2e8f0;
            background: rgba(0, 0, 0, 0.6); padding: 12px; border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.08); overflow-x: auto; max-height: 220px;
            white-space: pre; line-height: 1.5;
        }}

        .sig-list {{ display: flex; flex-direction: column; gap: 4px; font-family: var(--font-mono); font-size: 11px; color: var(--accent-primary); }}

        #legend {{
            position: absolute; bottom: 16px; left: 16px; z-index: 10; padding: 14px 18px;
            display: flex; flex-direction: column; gap: 8px;
        }}
        .legend-title {{ font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }}
        .legend-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px 16px; }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-main); }}
        .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
    </style>
    <script type="text/javascript" src="https://unpkg.com/vis-network@9.1.2/standalone/umd/vis-network.min.js"></script>
</head>
<body>
    <div id="network"></div>

    <!-- Header Bar -->
    <div id="header-bar" class="glass-panel">
        <div class="brand">
            <div class="brand-badge">CS</div>
            <div>
                <div class="brand-title">ConfigStream Topology & Flow Graph</div>
                <div class="brand-subtitle">Interactive Codebase Architecture, Flow Pulses & Live Code Snippets (v2.1)</div>
            </div>
        </div>
        <div class="controls-wrapper">
            <div class="search-box">
                <svg class="search-icon" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
                <input type="text" id="searchInput" class="search-input" placeholder="Search modules, files, symbols...">
            </div>
            <button class="btn" onclick="resetView()">Reset View</button>
            <button class="btn" onclick="togglePhysics()">Toggle Layout</button>
        </div>
    </div>

    <!-- Multi-View Mode Controller Toolbar -->
    <div id="view-modes-bar" class="glass-panel">
        <button class="mode-btn active" onclick="switchViewMode('subsystem', this)">🎨 Subsystems</button>
        <button class="mode-btn" onclick="switchViewMode('complexity', this)">🔥 LOC Density Heatmap</button>
        <button class="mode-btn" onclick="switchViewMode('flow', this)">⚡ Streaming Flow Focus</button>
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

    <!-- Verbatim Code Inspector Sidebar -->
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
            <div id="nodePath" class="info-value" style="font-family: var(--font-mono); font-size: 11px;">.</div>
        </div>
        <div class="info-group">
            <div class="info-label">Description / Docstring</div>
            <div id="nodeDesc" class="info-value">Click any node in the topology graph to inspect its function, verbatim code snippet, line count, and signatures.</div>
        </div>
        <div class="info-group">
            <div class="info-label">Lines of Code</div>
            <div id="nodeLines" class="info-value">--</div>
        </div>
        <div class="info-group">
            <div class="info-label">Key Signatures</div>
            <div id="nodeSigs" class="sig-list">--</div>
        </div>
        <div class="info-group">
            <div class="info-label">Verbatim Code Preview</div>
            <div id="nodeCode" class="code-container"># Select a file node to view live code preview</div>
        </div>
    </div>

    <!-- Legend -->
    <div id="legend" class="glass-panel">
        <div class="legend-title" id="legendTitle">Subsystem Legend</div>
        <div class="legend-grid" id="legendGrid">
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

    <!-- Secure Non-Executable JSON Data Blocks -->
    <script type="application/json" id="graph-data-nodes">{nodes_safe_json}</script>
    <script type="application/json" id="graph-data-edges">{edges_safe_json}</script>

    <script>
        function safeParseJSON(elementId) {{
            try {{
                const el = document.getElementById(elementId);
                return el ? JSON.parse(el.textContent) : [];
            }} catch (err) {{
                console.error("Failed to parse JSON for " + elementId, err);
                return [];
            }}
        }}

        const rawNodes = safeParseJSON('graph-data-nodes');
        const rawEdges = safeParseJSON('graph-data-edges');

        let network = null;
        let nodesDataset = null;
        let edgesDataset = null;
        let currentMode = 'subsystem';
        let physicsEnabled = true;

        if (typeof vis !== 'undefined') {{
            nodesDataset = new vis.DataSet(rawNodes);
            edgesDataset = new vis.DataSet(rawEdges);

            const container = document.getElementById('network');
            const data = {{ nodes: nodesDataset, edges: edgesDataset }};

            const options = {{
                nodes: {{
                    font: {{ color: '#f8fafc', face: 'system-ui', size: 13 }},
                    borderWidth: 2, shadow: true,
                }},
                edges: {{
                    font: {{ color: '#94a3b8', face: 'system-ui', size: 10, align: 'middle' }},
                    smooth: {{ type: 'cubicBezier', forceDirection: 'none', roundness: 0.4 }},
                }},
                physics: {{
                    solver: 'forceAtlas2Based',
                    forceAtlas2Based: {{ gravitationalConstant: -55, centralGravity: 0.01, springLength: 110, springConstant: 0.08 }},
                    maxVelocity: 50, timestep: 0.35, stabilization: {{ iterations: 150 }},
                }},
                interaction: {{ hover: true, tooltipDelay: 200, keyboard: true }},
            }};

            network = new vis.Network(container, data, options);

            // Click Handler for Verbatim Inspector
            network.on('click', function(params) {{
                if (params.nodes.length > 0) {{
                    const nodeId = params.nodes[0];
                    const node = nodesDataset.get(nodeId);

                    document.getElementById('nodeTitle').innerText = node.label;
                    document.getElementById('nodeTypeBadge').innerText = node.type;
                    document.getElementById('nodeTypeBadge').style.background = node.color + '40';
                    document.getElementById('nodeTypeBadge').style.color = node.color;
                    document.getElementById('nodeGroup').innerText = node.group.toUpperCase();
                    document.getElementById('nodePath').innerText = node.path || '.';
                    document.getElementById('nodeDesc').innerText = node.description || 'No description available.';
                    document.getElementById('nodeLines').innerText = node.lines ? node.lines + ' lines' : 'N/A';

                    // Signatures
                    const sigsEl = document.getElementById('nodeSigs');
                    if (node.signatures && node.signatures.length > 0) {{
                        sigsEl.innerHTML = node.signatures.map(s => '<div>• ' + escapeHtml(s) + '</div>').join('');
                    }} else {{
                        sigsEl.innerText = 'No primary signatures extracted.';
                    }}

                    // Code Preview
                    const codeEl = document.getElementById('nodeCode');
                    codeEl.innerText = node.snippet || '# No code snippet available for directory/root node.';
                }}
            }});
        }} else {{
            document.getElementById('network').innerHTML = '<div style="padding:40px; text-align:center; color:#94a3b8;">Vis.js network library not loaded. Codebase metadata is safely loaded in JSON data blocks.</div>';
        }}

        function escapeHtml(str) {{
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }}

        // View Mode Switcher
        function switchViewMode(mode, btnEl) {{
            if (!nodesDataset) return;
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            btnEl.classList.add('active');
            currentMode = mode;

            if (mode === 'subsystem') {{
                nodesDataset.update(rawNodes.map(n => ({{ id: n.id, color: n.subsystemColor, hidden: false }})));
                updateLegend('subsystem');
            }} else if (mode === 'complexity') {{
                nodesDataset.update(rawNodes.map(n => ({{ id: n.id, color: n.complexityColor, hidden: false }})));
                updateLegend('complexity');
            }} else if (mode === 'flow') {{
                nodesDataset.update(rawNodes.map(n => ({{
                    id: n.id,
                    color: n.id.startsWith('mod:') ? '#ec4899' : '#334155',
                    hidden: false
                }})));
                updateLegend('flow');
            }}
        }}

        function updateLegend(mode) {{
            const titleEl = document.getElementById('legendTitle');
            const gridEl = document.getElementById('legendGrid');
            if (mode === 'complexity') {{
                titleEl.innerText = 'LOC Density Heatmap';
                gridEl.innerHTML = `
                    <div class="legend-item"><div class="legend-dot" style="background: #10b981;"></div>Lightweight (&lt;200 lines)</div>
                    <div class="legend-item"><div class="legend-dot" style="background: #f59e0b;"></div>Medium (200-500 lines)</div>
                    <div class="legend-item"><div class="legend-dot" style="background: #ef4444;"></div>Complex (&gt;500 lines)</div>
                    <div class="legend-item"><div class="legend-dot" style="background: #38bdf8;"></div>Directory / Virtual</div>
                `;
            }} else if (mode === 'flow') {{
                titleEl.innerText = 'Streaming Data Flow';
                gridEl.innerHTML = `
                    <div class="legend-item"><div class="legend-dot" style="background: #ec4899;"></div>Pipeline Streaming Path</div>
                    <div class="legend-item"><div class="legend-dot" style="background: #334155;"></div>Supporting Module</div>
                `;
            }} else {{
                titleEl.innerText = 'Subsystem Legend';
                gridEl.innerHTML = `
                    <div class="legend-item"><div class="legend-dot" style="background: #a855f7;"></div>Pipeline Core</div>
                    <div class="legend-item"><div class="legend-dot" style="background: #ec4899;"></div>Parsers</div>
                    <div class="legend-item"><div class="legend-dot" style="background: #f59e0b;"></div>Generators</div>
                    <div class="legend-item"><div class="legend-dot" style="background: #10b981;"></div>Output Engine</div>
                    <div class="legend-item"><div class="legend-dot" style="background: #3b82f6;"></div>WARP Washer</div>
                    <div class="legend-item"><div class="legend-dot" style="background: #6366f1;"></div>Go Sidecar</div>
                    <div class="legend-item"><div class="legend-dot" style="background: #ef4444;"></div>Security & Crypto</div>
                    <div class="legend-item"><div class="legend-dot" style="background: #06b6d4;"></div>FastAPI Server</div>
                `;
            }}
        }}

        // Search
        document.getElementById('searchInput').addEventListener('input', function(e) {{
            const query = e.target.value.toLowerCase().trim();
            if (!query || !network) return;
            const match = rawNodes.find(n => n.label.toLowerCase().includes(query) || (n.path && n.path.toLowerCase().includes(query)));
            if (match) {{
                network.focus(match.id, {{ scale: 1.3, animation: true }});
                network.selectNodes([match.id]);
            }}
        }});

        function resetView() {{ if (network) network.fit({{ animation: true }}); }}
        function togglePhysics() {{ if (network) {{ physicsEnabled = !physicsEnabled; network.setOptions({{ physics: {{ enabled: physicsEnabled }} }}); }} }}

        function filterSubsystem(subsystem, chipEl) {{
            if (!nodesDataset) return;
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
    include_db = "--include-local-db" in sys.argv
    graph_data = build_graph_data(include_local_db=include_db)
    html_content = generate_html(graph_data)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(
        f"[SUCCESS] Successfully generated secure elevated project graph HTML (v2.1) at: {OUTPUT_FILE}"
    )
    print(
        f"          Nodes: {len(graph_data['nodes'])}, Edges: {len(graph_data['edges'])}"
    )


if __name__ == "__main__":
    main()
